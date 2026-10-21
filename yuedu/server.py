#!/usr/bin/env python3.11
"""月渡 · read-only backend for the ctd memory library.

Gathers the scattered stores on the Seoul box into six JSON endpoints that the
static/index.html front end understands. Every store is opened read-only; this
process never writes to the memory lab. The only file it writes is its own
cookie secret (next to this script, created on first run).

Stores (override any path with the env var in brackets):
  书童 daily output        [YUEDU_SHADOW]   …/daily-memory-shadow-20260921/output
  calendar kinds 1–6       [YUEDU_CAL]      /srv/ctd-memory-lab/calendar
  conversation ledger      [YUEDU_LEDGER]   …/conversation-ledger/croft-live-shadow.jsonl
  Ombre vault (OB)         [YUEDU_OMBRE]    /srv/ctd-memory-lab/ombre-shadow-real-20260910-a1
  C-Memory V2 canonical    [YUEDU_CANON]    …/c-memory-v2/runtime/memory_v2.sqlite3
  plans / murmurs / inbox  [YUEDU_PLANS] [YUEDU_MURMURS] [YUEDU_INBOX]
  handoff note v2          [YUEDU_HANDOFF]  …/layered-dream-20261021/live/output
"""
import datetime as dt
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

LAB = Path(os.environ.get("YUEDU_LAB", "/srv/ctd-memory-lab"))
P = lambda env, default: Path(os.environ.get(env, str(default)))
SHADOW = P("YUEDU_SHADOW", LAB / "project/daily-memory-shadow-20260921/output")
CAL = P("YUEDU_CAL", LAB / "calendar")
LEDGER = P("YUEDU_LEDGER", LAB / "runtime-shadow-20260913/conversation-ledger/croft-live-shadow.jsonl")
OMBRE = P("YUEDU_OMBRE", LAB / "ombre-shadow-real-20260910-a1")
CANON = P("YUEDU_CANON", LAB / "project/c-memory-v2/runtime/memory_v2.sqlite3")
PLANS = P("YUEDU_PLANS", LAB / "project/plans-20260926/state/plans.json")
MURMURS = P("YUEDU_MURMURS", LAB / "project/murmurs-20260926/data/murmurs.json")
INBOX = P("YUEDU_INBOX", LAB / "status/bookboy-inbox.jsonl")
INBOX_STATE = P("YUEDU_INBOX_STATE", LAB / "status/bookboy-inbox-state.json")
HANDOFF = P("YUEDU_HANDOFF", LAB / "project/layered-dream-20261021/live/output")
STATIC = Path(__file__).resolve().parent / "static"
SINCE = os.environ.get("YUEDU_SINCE", "2026-05-04")  # first day in the record; drives 相识第N天
PASSWORD_FILES = [Path(p) for p in os.environ.get("YUEDU_PASSWORD_FILES", str(LAB / "ui-shadow/.ui-key")).split(":") if p]
HOST = os.environ.get("YUEDU_HOST", "127.0.0.1")
PORT = int(os.environ.get("YUEDU_PORT", "18048"))
TZ = dt.timezone(dt.timedelta(hours=8))
DECAY_LAMBDA = 0.05  # Ombre's own setting; archive threshold is 0.3

SECRET_FILE = Path(__file__).resolve().parent / ".cookie-secret"
if not SECRET_FILE.exists():
    SECRET_FILE.write_text(secrets.token_hex(32))
    SECRET_FILE.chmod(0o600)
SECRET = SECRET_FILE.read_bytes().strip()
COOKIE_DAYS = 30


# ---------------------------------------------------------------- small helpers
def now():
    return dt.datetime.now(TZ)


def today():
    return now().date().isoformat()


def read_text(p, limit=None):
    try:
        t = Path(p).read_text(encoding="utf-8").strip()
        return t[:limit] if limit else t
    except OSError:
        return ""


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def read_jsonl(p):
    out = []
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def local_iso(ts):
    """Ledger stamps are UTC 'Z'; everything shown is Beijing time."""
    if not ts:
        return ""
    try:
        d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=TZ)
        return d.astimezone(TZ).isoformat(timespec="minutes")
    except ValueError:
        return ts


def strip_md(t):
    """Summaries carry light markdown headings; the page wants plain prose."""
    t = re.sub(r"^#+\s*", "", t, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


class Cached:
    """Rebuilds a value when its source file's mtime changes."""

    def __init__(self, path, build):
        self.path, self.build, self.mtime, self.value, self.lock = path, build, None, None, threading.Lock()

    def get(self):
        try:
            m = os.stat(self.path).st_mtime
        except OSError:
            m = -1
        with self.lock:
            if m != self.mtime:
                self.value, self.mtime = self.build(), m
            return self.value


# ---------------------------------------------------------------- ledger (原文账本)
def build_ledger():
    by_id, per_day = {}, {}
    for r in read_jsonl(LEDGER):
        if r.get("visibility") not in (None, "conversation"):
            continue
        at = local_iso(r.get("created_at"))
        mid = r.get("source_message_id")
        if mid:
            by_id[mid] = {"who": r.get("speaker") or r.get("content_author") or "", "text": r.get("text") or "", "at": at}
        day = at[:10]
        if day:
            per_day[day] = per_day.get(day, 0) + 1
    return {"by_id": by_id, "per_day": per_day, "total": len(by_id)}


ledger = Cached(LEDGER, build_ledger)


# ---------------------------------------------------------------- Ombre vault (OB)
def parse_frontmatter(text):
    """Enough YAML for Ombre's frontmatter: scalars and flat lists. Nested blocks (quotes) are skipped."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    head, body = text[3:end], text[end + 4:]
    try:
        import yaml  # use the real parser when the box has it
        meta = yaml.safe_load(head) or {}
        return (meta if isinstance(meta, dict) else {}), body
    except Exception:
        pass
    meta, key = {}, None
    for line in head.splitlines():
        if not line.strip():
            continue
        if line.startswith("- ") and key is not None and isinstance(meta.get(key), list):
            meta[key].append(line[2:].strip().strip("'\""))
            continue
        if line[0] in " \t":
            continue
        k, _, v = line.partition(":")
        key, v = k.strip(), v.strip()
        if v == "":
            meta[key] = []
        else:
            v = v.strip("'\"")
            if re.fullmatch(r"-?\d+", v):
                v = int(v)
            elif re.fullmatch(r"-?\d*\.\d+", v):
                v = float(v)
            elif v in ("true", "false"):
                v = v == "true"
            meta[key] = v
    return meta, body


# Buckets migrated from Dallas keep their import folder as a domain.
DOMAIN_NAMES = {"ctd-shadow-full-migration-notes": "旧笔记", "ctd-shadow-full-migration-core": "旧核心", "ctd-shadow-full-migration-daily": "旧日常"}


def vitality(meta):
    """Ebbinghaus-style: importance and use keep a lantern lit, time dims it."""
    try:
        last = dt.datetime.fromisoformat(str(meta.get("last_active") or meta.get("created"))[:19])
        days = max(0.0, (dt.datetime.now() - last).total_seconds() / 86400)
    except ValueError:
        days = 60
    imp = float(meta.get("importance") or 5) / 10
    use = 1 + math.log1p(float(meta.get("activation_count") or 0)) * 0.3
    if meta.get("pinned") or meta.get("type") == "permanent":
        return 1.0
    return round(max(0.04, min(1.0, imp * use * math.exp(-DECAY_LAMBDA * days) * 1.6)), 3)


def build_ombre():
    buckets, valence_by_day = [], {}
    root = OMBRE / "dynamic"
    for f in root.rglob("*.md") if root.exists() else []:
        meta, body = parse_frontmatter(read_text(f))
        if not meta:
            continue
        dom = meta.get("domain") or [f.parent.name]
        dom = dom[0] if isinstance(dom, list) and dom else str(dom)
        dom = DOMAIN_NAMES.get(dom, dom)
        created = str(meta.get("created") or "")[:10]
        try:
            val, aro = float(meta.get("valence", 0.5)), float(meta.get("arousal", 0.5))
        except (TypeError, ValueError):
            val, aro = 0.5, 0.5
        buckets.append({
            "id": str(meta.get("id") or f.stem), "title": str(meta.get("title") or meta.get("name") or f.stem),
            "domain": dom, "valence": val, "arousal": aro, "importance": int(meta.get("importance") or 5),
            "vitality": vitality(meta), "created": created, "last_active": str(meta.get("last_active") or "")[:10],
            "tags": [str(t) for t in (meta.get("tags") or []) if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(t))][:8],
            "body": body.strip()[:1200],
        })
        if created and val != 0.5:  # 0.5 is Ombre's unset default, not a mood
            valence_by_day.setdefault(created, []).append(val)
    count = lambda sub: sum(1 for _ in (OMBRE / sub).rglob("*.md")) if (OMBRE / sub).exists() else 0
    return {
        "buckets": buckets,
        "valence_by_day": {k: round(sum(v) / len(v), 3) for k, v in valence_by_day.items()},
        "archived": count("archive"), "permanent": count("permanent"),
    }


_ombre = {"at": 0, "value": None}


def ombre():
    # The vault is hundreds of small files; a five-minute cache is plenty.
    if _ombre["value"] is None or time.time() - _ombre["at"] > 300:
        _ombre["value"], _ombre["at"] = build_ombre(), time.time()
    return _ombre["value"]


# ---------------------------------------------------------------- 书童 output
def day_dir(date):
    return SHADOW / date


def events_for(date):
    d = read_json(day_dir(date) / "events.json", {}) or {}
    evs = d.get("events", d if isinstance(d, list) else [])
    return [{k: e.get(k) for k in ("event_id", "title", "category", "summary", "card_candidate", "time_start", "time_end", "source_refs", "status")} for e in evs]


def summary_for(date):
    return strip_md(read_text(day_dir(date) / "summary.md") or read_text(day_dir(date) / "summary.draft.md"))


def brief_for(date):
    return strip_md(read_text(day_dir(date) / "brief.md") or read_text(day_dir(date) / "brief.draft.md"))


def dated_dirs(root):
    try:
        return sorted(p.name for p in root.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
    except OSError:
        return []


def kinds_for(date):
    y, m = date[:4], date[5:7]
    base = CAL / y / m / date
    names = {2: "感受", 3: "我的目光", 4: "但她说", 6: "经历", 5: "经验"}
    out = {}
    for k, name in names.items():
        rows = read_jsonl(base / f"{k}-raw.jsonl")
        if rows:
            out[name] = [r.get("content", "") for r in rows if r.get("content")][:12]
    return out


# ---------------------------------------------------------------- canonical (C-Memory V2)
def canon():
    con = sqlite3.connect(f"file:{CANON}?mode=ro", uri=True, timeout=5)
    con.execute("PRAGMA query_only=1")
    con.row_factory = sqlite3.Row
    return con


def stars():
    try:
        con = canon()
    except sqlite3.Error:
        return []
    with con:
        hidden = {r[0] for r in con.execute("SELECT memory_id FROM memory_flag WHERE flag IN ('tombstone','dont_surface') AND COALESCE(value,'1') NOT IN ('0','false')")}
        flags = {}
        for r in con.execute("SELECT memory_id, flag FROM memory_flag WHERE flag IN ('pinned','permanent','star_nomination') AND COALESCE(value,'1') NOT IN ('0','false')"):
            flags.setdefault(r[0], set()).add(r[1])
        rows = con.execute("SELECT memory_id, kind, title, content, importance, COALESCE(valid_from, created_at) AS d FROM memory WHERE status IS NULL OR status NOT IN ('deleted','superseded','archived')").fetchall()
    out = []
    for r in rows:
        mid = r["memory_id"]
        if mid in hidden:
            continue
        f = flags.get(mid, set())
        kind = "permanent" if "permanent" in f else "pinned" if "pinned" in f else "star" if "star_nomination" in f else "core" if r["kind"] == "legacy_core" else None
        if not kind:
            continue
        imp = r["importance"]
        imp = int(round(imp * 10)) if isinstance(imp, float) and imp <= 1 else int(imp or 6)
        out.append({"id": mid, "kind": kind, "title": r["title"] or (r["content"] or "")[:16], "content": (r["content"] or "")[:600], "importance": max(1, min(10, imp)), "date": str(r["d"] or "")[:10] or today()})
    out.sort(key=lambda x: x["date"])
    return out


def canon_count():
    try:
        with canon() as con:
            return con.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
    except sqlite3.Error:
        return None


# ---------------------------------------------------------------- endpoints
def ep_tonight(q):
    t = today()
    days = dated_dirs(SHADOW)
    latest = days[-1] if days else t
    receipt = read_json(day_dir(latest) / "latest-receipt.json", {}) or {}
    hdays = dated_dirs(HANDOFF)
    handoff = None
    if hdays:
        d = HANDOFF / hdays[-1]
        mds = sorted(d.glob("*.md"))
        if mds:
            handoff = {"date": hdays[-1], "text": strip_md(read_text(mds[0], 1600))}
    read_ids = set((read_json(INBOX_STATE, {}) or {}).get("read", []) or [])
    inbox = [m for m in read_jsonl(INBOX) if m.get("id") not in read_ids][-3:]
    plans = (read_json(PLANS, {}) or {}).get("items", {}) or {}
    open_plans = sorted((p for p in plans.values() if p.get("status") not in ("done", "dropped", "abandoned", "resolved")), key=lambda p: p.get("created") or "", reverse=True)[:6]
    murmurs = (read_json(MURMURS, []) or [])[-6:][::-1]
    ev_total = sum(len(events_for(d)) for d in days)
    return {
        "since": SINCE, "date": t, "handoff": handoff,
        "bookboy": {"generated_at": receipt.get("generated_at"), "slices": receipt.get("fragment_count"), "events": receipt.get("event_count"), "model": receipt.get("bookboy_model"), "finalized": bool(receipt.get("finalized")), "balance": None},
        "inbox": [{"id": m.get("id"), "title": m.get("title"), "body": (m.get("body") or "")[:140], "created_at": m.get("created_at")} for m in inbox],
        "events": events_for(t) or events_for(latest),
        "plans": [{"kind": p.get("kind"), "text": p.get("text"), "said_on": p.get("said_on"), "due": p.get("due")} for p in open_plans],
        "murmurs": [{"text": m.get("text", "")[:120], "author": m.get("author"), "at": local_iso(m.get("created_at"))} for m in murmurs],
        "counts": {"messages": ledger.get()["total"], "events": ev_total, "memories": canon_count() or 0, "lanterns": len(ombre()["buckets"])},
    }


def ep_tide(q):
    t = dt.date.fromisoformat(today())
    ago = lambda n: (t - dt.timedelta(days=n)).isoformat()
    weeks = sorted((SHADOW / "weeks").glob("*.md"))[-4:][::-1] if (SHADOW / "weeks").exists() else []
    months = sorted((SHADOW / "months").glob("*.md"))[-3:][::-1] if (SHADOW / "months").exists() else []
    wk = lambda p: " — ".join(s[5:] for s in p.stem.split("_"))
    return {
        "today": {"date": ago(0), "text": summary_for(ago(0))[:600], "events": [{"t": (e.get("time_start") or "")[11:16], "title": e.get("title")} for e in events_for(ago(0))]},
        "recent": [{"date": ago(n), "text": summary_for(ago(n))} for n in (1, 2, 3) if summary_for(ago(n))],
        "brief": [{"date": ago(n), "text": brief_for(ago(n))} for n in (4, 5, 6, 7) if brief_for(ago(n))],
        "weeks": [{"range": wk(p), "text": strip_md(read_text(p))} for p in weeks],
        "months": [{"month": p.stem, "text": strip_md(read_text(p))} for p in months],
    }


def ep_moons(q):
    month = (q.get("month") or [today()[:7]])[0]
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        return {"days": []}
    per_day, val = ledger.get()["per_day"], ombre()["valence_by_day"]
    out = []
    for i in range(1, 32):
        d = f"{month}-{i:02d}"
        n = per_day.get(d, 0)
        has = day_dir(d).exists()
        if not n and not has:
            continue
        out.append({"date": d, "messages": n, "valence": val.get(d), "events": len(events_for(d)), "brief": brief_for(d)[:80]})
    return {"days": out}


def ep_day(q):
    d = (q.get("date") or [today()])[0]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return {}
    return {"date": d, "brief": brief_for(d), "summary": summary_for(d), "events": events_for(d), "kinds": kinds_for(d)}


def ep_stars(q):
    return {"stars": stars()}


def ep_lake(q):
    o = ombre()
    return {"buckets": o["buckets"], "archived": o["archived"], "permanent": o["permanent"]}


ADDR = re.compile(r"^(\d)\.(\d{1,2})\.(\d{1,2})\.(\d+)$")


def ep_trace(q):
    refs = [r for r in (q.get("refs") or [""])[0].split(",") if ADDR.match(r)][:12]
    by_id, slices_cache, out = ledger.get()["by_id"], {}, []
    for a in refs:
        y, m, d, _ = ADDR.match(a).groups()
        date = f"202{y}-{int(m):02d}-{int(d):02d}"
        if date not in slices_cache:
            sl = (read_json(day_dir(date) / "slices.json", {}) or {}).get("slices", [])
            slices_cache[date] = {s.get("human_address"): s for s in sl}
        s = slices_cache[date].get(a)
        if not s:
            continue
        lines = [by_id[m] for m in (s.get("ordered_message_ids") or []) if m in by_id][:40]
        out.append({"address": a, "time": local_iso(s.get("time_start")), "lines": lines})
    return {"slices": out}


ROUTES = {"tonight": ep_tonight, "tide": ep_tide, "moons": ep_moons, "day": ep_day, "stars": ep_stars, "lake": ep_lake, "trace": ep_trace}


# ---------------------------------------------------------------- auth
def passwords():
    out = []
    for p in PASSWORD_FILES:
        t = read_text(p)
        if t:
            out.append(t.splitlines()[0].strip())
    return out


def make_cookie():
    exp = str(int(time.time()) + COOKIE_DAYS * 86400)
    sig = hmac.new(SECRET, exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def cookie_ok(header):
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == "yuedu":
            exp, _, sig = v.partition(".")
            good = hmac.new(SECRET, exp.encode(), hashlib.sha256).hexdigest()
            if exp.isdigit() and int(exp) > time.time() and hmac.compare_digest(sig, good):
                return True
    return False


# ---------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    server_version = "yuedu/1"

    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        if path in ("/", "/index.html"):
            html = (STATIC / "index.html").read_text(encoding="utf-8").replace("<!--YUEDU_API-->", "<script>window.YUEDU_API=true</script>")
            return self.send(200, html.encode(), "text/html; charset=utf-8")
        if path == "/icon.svg":
            return self.send(200, (STATIC / "icon.svg").read_bytes(), "image/svg+xml")
        if path == "/health":
            return self.send(200, {"ok": True})
        if path.startswith("/api/"):
            name = path[5:]
            if name not in ROUTES:
                return self.send(404, {"error": "no such route"})
            if not cookie_ok(self.headers.get("Cookie")):
                return self.send(401, {"error": "login required"})
            try:
                return self.send(200, ROUTES[name](parse_qs(u.query)))
            except Exception as e:  # keep the page alive; the front end shows the message
                return self.send(500, {"error": type(e).__name__})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/login":
            return self.send(404, {"error": "not found"})
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 4096)
            pw = str(json.loads(self.rfile.read(n) or b"{}").get("password", ""))
        except ValueError:
            pw = ""
        time.sleep(0.4)  # slow down guessing
        if pw and any(hmac.compare_digest(pw, p) for p in passwords()):
            return self.send(200, {"ok": True}, headers={"Set-Cookie": f"yuedu={make_cookie()}; Max-Age={COOKIE_DAYS * 86400}; Path=/; HttpOnly; Secure; SameSite=Lax"})
        self.send(401, {"error": "wrong password"})


if __name__ == "__main__":
    print(f"月渡 listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
