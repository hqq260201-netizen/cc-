# 交接：C-Memory 重新出发（Claude → ChatGPT，2026-10-17 20:00 CST）

> 你要执行的计划是 `RESTART_PLAN_20261017.md`（同目录）。本文件告诉你**每样东西在哪、现在是什么状态、接口长什么样、每一步怎么做、怎么验收、什么不能做**。
> 琪琪的安排：你按计划从 Step 0 做到 Step 3（加上 Step 4 的样例收集），全部 PASS 后她再找 Claude 检查。期间遇到计划没覆盖的情况，**停下来问琪琪**，不要自己改方向。

---

## 0. 一句话目标

让程亭渡在普通聊天里**每一轮**都有机会自动想起旧事，规则如下：
- 旧召回（`memory_trigger_new.py`）先找；找不到时，V2（`passive_live_single.py`）补；
- 找到的内容通过 Roof mod 接在原生 `total_tokens_reminder` 后面，**只出现在这一次模型请求里**，下一轮自动消失（阅后即焚）；
- 不改写任何历史，不拖慢对话。

---

## 1. 你之前的判断里需要放下的东西

下面这些不是指责，是为了不再重复：

1. **"只追加会让缓存倒退"是错的。** 10/14 缓存爆炸的根因是改写历史（`prune-stale-context-v2.py`、`_clear_previous`、`pilulier-clean.py` 一类）。追加和请求级注入都不会动前缀。
2. **"每 session 一张"、JS 里写死的 Gate 白名单**：废弃。
3. **两份"真实宿主回执"不能算数**（见 §3 E2）。正式进程 2.1.296 **不监视 `mods/` 目录**：JS 改了也要等进程重启才生效。不要再用"刚改的 JS 已经热载入"做任何推断。
4. **隔离测试不能写生产路径。** 今天已经发生过两次（14:50、17:15）。
5. **不要找 Gemini 或其他模型重新定方向。** 计划写到的照计划做，计划没写到的问琪琪。
6. **PLAN.md 不再加新节。** 进展只写进 `STATUS.md`（≤1 页）和计划末尾的执行记录表。

---

## 2. 机器和路径地图（首尔 VPS，root，CST +08）

| 东西 | 路径或位置 | 备注 |
|---|---|---|
| 正式 Claude Code | tmux `cc`，当前 PID 2314153，2.1.296 | 启动参数：`claude --model claude-opus-4-6 --plugin-dir /root/cc-selfhost/mods/ctd-roof-names --effort max --channels plugin:telegram@… --append-system-prompt-file /tmp/cc_system_prompt.txt`。每天约 01:00 自然切窗（新进程）。**不要手动重启。** |
| 正式进程 PATH | `/root/.bun/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/bin` | 裸 `python3` = `/usr/bin/python3` **3.6.8**；3.11 在 `/usr/bin/python3.11` |
| 用户级 hooks | `/root/.claude/settings.json` | **被正式进程监视，改了立即生效**。`UserPromptSubmit` → `python3 /root/cc-selfhost/experimental/ephemeral-v3/cache_safe_recall.py`（timeout 15） |
| 当前 wrapper | `/root/cc-selfhost/experimental/ephemeral-v3/cache_safe_recall.py` | 第 137 行：开关缺席就 `audit('legacy_retained_disabled')` 后 `return ''`，**不调用旧召回** |
| wrapper 审计 | 同目录 `gate-audit.jsonl` | 目前 16 行，全是 `legacy_retained_disabled` |
| 旧召回 | `/root/cc-selfhost/.claude/hooks/memory_trigger_new.py` | 从 stdin 读 `{prompt, session_id, ...}`，向 stdout 打印块。依赖 `127.0.0.1:18043`（`ctd-hot-recall.service`） |
| 旧召回的写入点 | `STATE_DIR=/tmp/ctd-recall-session`、`AMBIENT_BUDGET_DIR=/tmp/ctd-ambient-recall-budget`、`AUDIT_LOG`（环境变量 `CTD_RECALL_HOOK_AUDIT_LOG`，默认 `…/logs/recall-hook.jsonl`）、`P4_SHADOW_JOB_DIR=/run/c-memory-v2/p4-passive-shadow-jobs` | 只有 AUDIT_LOG 有环境变量覆盖；**其余三个要先加覆盖**，才能做冒烟测试 |
| 旧召回参数 | `RANDOM_L0_PCT=20`、`RANDOM_COOLDOWN_TURNS=8`、`RANDOM_COOLDOWN_SECS=1200`、`ACTIVE_TTL=4`、`ACTIVE_MAX=2`，recall 超时 1.4 s | **本计划不改这些参数** |
| 旧召回输出格式 | `[新书房·自动召回 L{0,1,2}｜…]` + 条目行 + 提示行；`[新书房·聊天摘录｜…]`；`[新书房·当前话题｜…]` 条目带 `剩余至多 N 轮` | 见 `memory_trigger_new.py` 第 379–396 行 |
| 旧召回审计 | `/srv/ctd-memory-lab/project/memory-v2-20261008/logs/recall-hook.jsonl` | 字段有 `shown_ids`、`level`、`query_gate_reason`、`recall_error` 等；**含 prompt 原文**（已有隐私面，不要外发） |
| V2 适配器 | `/srv/ctd-memory-lab/project/memory-v2-20261008/p4/passive_live_single.py`（`c-memory-v2` 是这个目录的软链） | stdin `{prompt}` → stdout JSON。ready 时字段：`state, can_deliver, context(以 [C-Memory·本轮] 开头，≤1550), turn_key(32 hex), source_checked, route, selected_ids[1], delivery_tier, topic_cursor_proof, positive_rule, elapsed_ms`；否则返回 `{state:'empty', reason}`。依赖 `127.0.0.1:18044` |
| V2 结果日志 | `…/logs/p4-passive-adapter-outcomes.jsonl` | 今日 25 次：not_general_eligible 15、gates_abstained 8、其他 2 |
| Roof mod | `/root/cc-selfhost/mods/ctd-roof-names/hooks/`：`register.js`（唯一入口，`prompt.attachment` 里调用 `decorateEngineReminder`）、`pilulier.js`（`session.start` / `prompt.submit` / `turn.start` / `turn.complete`）、`p4_ephemeral.js`（卡片槽） | **JS 只在进程启动时载入** |
| 正式进程实际运行的 JS | 10/16 21:46 版：`/root/cc-selfhost/backups/pilulier-before-topic-shadow-20261017.js`；register 同 `backups/recovery-20261017-1445/register.before-slot-census.js` | 今晚 01:00 起换成磁盘上的当前版 |
| 开关目录 | `/run/c-memory-v2/` | tmpfs，**重启后会清空**。每轮实时检查 |
| 原生假模型测试台 | `p4/offline/request-only-20261016/`（`native_probe.py`、`integrated_four_turn_probe.py`、`integrated-plugin/`）、`recovery-20261017/native_hook36_probe.py` | 用前必须先过 §6 的隔离硬闸 |
| 回查原话 | `/root/cc-selfhost/show_source.sh <6.9.x.x｜eventv1_…｜fragv1_…>` | Step 4 给琪琪看样例时用 |
| 正式 session 记录 | `/root/.claude/projects/-root-cc-selfhost/<uuid>.jsonl`（当前是 `22a06f96…`） | 只读，用来算缓存指标和查槽位 |

---

## 3. 已核实的事实（Claude 17:49–19:30 只读核对）

- **E1 旧召回为 0**：见上表 wrapper 那一行。
- **E2 假回执**：正式进程 `/proc/2314153/fdinfo` 的 inotify 只有 5 个监视对象：`~/.claude/settings.json`、`cc-selfhost/.claude/settings.json`、`settings.local.json`、`~/.claude/`、`cc-selfhost/.claude/`。`p4-loaded-build.json` 写于 17:15:40.42，比补丁落盘的 17:15:28 晚 12 秒，比隔离测试结束的 17:16:47 早；census（150）写于 14:53:41，落在 14:46–14:53 的测试窗口内。
- **E6 槽位存在**：当前 session 96 条普通用户消息里，95 条附近有 `total_tokens_reminder` 附件（文本是固定的 `<total_tokens>15000000 tokens left</total_tokens>`）；工具结果之后另有 67 次。JSONL 里记的是**未装饰**的原文。
- **服务健康**：`18043/health` 第一次请求耗时 3.04 s，第二次 0.007 s（listen backlog 只有 5，偶尔卡顿）；`18044/health` 0.09 s。**延迟要实测**，不要假设。
- **参考仓库**（只借思路，不打二进制补丁）：
  - `lllq-123/claude-code-ephemeral-reminders`：请求级提醒插在缓存断点之后，只花自身 token；
  - `lllq-123/claude-code-cache-keepalive`：缓存要看 usage 的**时间序列**，改写历史必定 miss。

---

## 4. 逐步操作说明

### Step 0：止损（今天 01:00 之前，约 15 分钟）
```bash
cd /run/c-memory-v2
for f in p4-engine-reminder-canary-on p4-dual-rank-safe-canary-on p4-semantic-tiebreak-canary-on; do
  [ -e "$f" ] && mv "$f" "${f%-on}-off-restart-20261017"; done
mkdir -p /srv/ctd-memory-lab/project/memory-v2-20261008/recovery-20261017/synthetic-receipts/suspect-1715
mv p4-loaded-build.json p4-native-slot-census.json \
   /srv/ctd-memory-lab/project/memory-v2-20261008/recovery-20261017/synthetic-receipts/suspect-1715/
ls /run/c-memory-v2
```
- 隔离硬闸：写一个 `tools/guard_test_paths.sh <dir>`，在那个目录（含拷贝的插件代码）里 grep `/run/c-memory-v2` 和 `/root/cc-selfhost`；一旦命中，以非 0 退出。以后所有测试脚本在开头调用它。
- 改正 STATUS.md：写清 E1、E2、E6。去掉"14:57 正式槽位已观测""natural-frequency-v2 已载入"这类说法，改为"疑似测试写入，已隔离"。
- **报告给琪琪**：上面 `ls` 的输出，以及 STATUS.md 的 diff。

### Step 1：recall_router.py + 影子运行
**1a. 先给旧召回补环境变量覆盖**（备份后改，只加不删）：
```python
STATE_DIR=Path(os.environ.get('CTD_RECALL_STATE_DIR','/tmp/ctd-recall-session'))
AMBIENT_BUDGET_DIR=Path(os.environ.get('CTD_RECALL_BUDGET_DIR','/tmp/ctd-ambient-recall-budget'))
P4_SHADOW_JOB_DIR=Path(os.environ.get('CTD_P4_SHADOW_JOB_DIR','/run/c-memory-v2/p4-passive-shadow-jobs'))
```
用正式 PATH 的 python3（3.6）跑一遍语法检查和一次合成调用（全部覆盖指向临时目录），确认生产路径没有新文件。

**1b. 新文件** `/srv/ctd-memory-lab/project/memory-v2-20261008/router/recall_router.py`（Python 3.11）：
- **输入**（stdin JSON）：`{prompt, session_id}`
- **流程**：
  1. 并行启动两个子进程：
     - `/usr/bin/python3 memory_trigger_new.py`，stdin 传 `{prompt, session_id}`，超时 1.6 s；
     - `/usr/bin/python3.11 passive_live_single.py`，stdin 传 `{prompt}`，超时 2.0 s。
  2. 总截止时间 2.2 s。超时的那一路当作空。
  3. 旧召回的 stdout 非空时，用 `cache_safe_recall.reduce_output` 的分块和预算逻辑（自然联想 ≤1200 字，明确回忆 ≤7000 字）。**不使用**它 retained 模式的"当前话题去重"：阅后即焚模式下上一轮的内容已经消失，话题需要每轮重新给。
  4. 选择规则：旧召回非空 → 选旧召回；否则，V2 ready 且 `V2_COMPLEMENT_ON`（文件开关 `/run/c-memory-v2/v2-complement-output-on`）存在 → 选 V2；否则为空。
  5. 同一 session 内按 id 去重：旧召回用 `shown_ids`，从它的审计或输出解析，解析不出就用条目行文本的 sha；V2 用 `selected_ids`。状态放在 `/tmp/ctd-recall-router/<sid_sha>.json`，可以用环境变量覆盖。
- **输出**（stdout JSON）：
  ```
  {state:'ready'|'empty', reason, source:'legacy'|'v2'|null,
   context:'[C-Memory·本轮]\n…',   // 旧召回块原样放在前缀后面
   ids:[...], turn_key: sha256(session_id|prompt|ids)[:32],
   route_log:{legacy:{ran,ms,chars,err}, v2:{ran,ms,reason}, picked, elapsed_ms}}
  ```
- **路由日志**：每轮一行写到 `…/logs/recall-router.jsonl`（0600），只记 `route_log`、短哈希和时间，**不写正文**。
- **不需要也不允许**：调用模型、读写 transcript、改 Gate。

**1c. wrapper 改成影子模式**：`cache_safe_recall.py` 在 `legacy-retained…` 开关缺席时（D1 = A，它会一直缺席），用 `/usr/bin/python3.11 recall_router.py` 跑一次（超时 3 s），把 `route_log` 写进 gate-audit（`event:'router_shadow'`），**返回空字符串**。gate-audit 路径加环境变量覆盖 `CTD_GATE_AUDIT_LOG`。

**1d. 冒烟测试**（必须做）：
```bash
TMP=$(mktemp -d)
env -i PATH=/root/.bun/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/bin HOME=/root \
  CTD_GATE_AUDIT_LOG=$TMP/g.jsonl CTD_RECALL_HOOK_AUDIT_LOG=$TMP/r.jsonl \
  CTD_RECALL_STATE_DIR=$TMP/s CTD_RECALL_BUDGET_DIR=$TMP/b CTD_P4_SHADOW_JOB_DIR=$TMP/j \
  CTD_ROUTER_STATE_DIR=$TMP/rs CTD_ROUTER_LOG=$TMP/rl.jsonl \
  python3 /root/cc-selfhost/experimental/ephemeral-v3/cache_safe_recall.py \
  <<< '{"prompt":"你还记得上次我们说的那件事吗","session_id":"smoke-'$RANDOM'"}'
echo "exit=$?"; cat $TMP/g.jsonl $TMP/rl.jsonl
```
要求：exit 0；stdout 为空；临时目录里有路由日志；生产日志的行数在冒烟前后不变。

**1e. 观察**：settings 不用改（wrapper 已挂着），下一条真实消息起就生效。等 ≥30 条真实消息或 6 小时后，统计 `recall-router.jsonl`：

| 指标 | PASS |
|---|---|
| 旧召回 would-pick 比例 | 每 100 条 3–7 次（10/12–14 基线：10/185、12/241、4/132） |
| router elapsed p95 | ≤ 1.5 s |
| 错误或超时 | 0 个错误；超时 ≤ 5% |
| 旧召回为空、V2 ready 的次数 | 只记录，给 Step 4 用 |

FAIL 就停下，把数字报给琪琪，不要自己调参数。

### Step 2：快递员 JS（离线做好，01:00 前部署，不打开）
**基础**：当前磁盘上的 `p4_ephemeral.js`、`pilulier.js`、`register.js`。先整套备份到 `/root/cc-selfhost/backups/courier-before-<时间>/`。

**最小改动**：
1. `pilulier.js` 的 `prompt.submit` 里，原来调用 `P4_PASSIVE_ADAPTER` 的地方（engine 那一段）改为：
   - 开关 `/run/c-memory-v2/recall-courier-on` 存在 → `$.process.run(['/usr/bin/python3.11', ROUTER], {stdin: JSON.stringify({prompt, session_id}), timeoutMs: 3000})`；
   - `session_id` 用 mod API 提供的会话 id（查 types 文件里 `session.start`、`prompt.submit` 的事件字段），取不到就用进程启动时生成的随机 id。
   - 旧的 `p4-engine-reminder-canary-on` 分支删掉或保持不可达。
2. `p4_ephemeral.js` 的 `prepareSingle`：
   - 改为校验 router 输出：`state==='ready'`、`turn_key` 为 32 位 hex、`ids` 非空、`context` 以 `[C-Memory·本轮]` 开头、长度 30–7500；
   - 删除 `positive_rule` 白名单和 `source_checked/TRACEABLE/route` 要求（来源判断已经在 router 和 V2 里做过）；
   - 不设每 session 上限；同 session 内 `ids` 去重（Set）。
3. `decorateEngineReminder` 保持原逻辑：同一轮只装饰一次（`used`），`turn.complete` 时 `finishTurn` 加 `$.ui.invalidate('prompt.attachment')`。
4. 回执：
   - `/run/c-memory-v2/courier-receipt.jsonl`（追加）：每次真正装饰写一行 `{at, pid, sid_sha, turn_key, ids_sha, chars}`；
   - `/run/c-memory-v2/courier-slot-census.json`：每 25 个槽位写一次 `{at, pid, sid_sha, slotCount, cardCount}`。
   - `pid` 取进程 pid（查 types 文件里 `$.process` 或 `$.env` 有没有提供）；取不到就在 `session.start` 时 `$.process.run(['sh','-c','echo $PPID'])` 获得。**必须能和 `pgrep -f 'claude --model'` 对上。**
5. `session.start` 写 `/run/c-memory-v2/courier-loaded.json`：`{at, pid, build:'courier-v1'}`。

**隔离测试**（先跑 `guard_test_paths.sh`）。用原生假模型测试台跑四轮：router 用一个假的替身，第 1、3 轮返回 ready，第 2、4 轮返回 empty。**全部 PASS 才能部署**：
- 第 1、3 轮的请求体里有卡，第 2、4 轮没有；
- **卡片在请求体里位于最后一个 `cache_control` 断点之后**：在假模型端解析 messages，记下卡片 marker 所在的 block 序号和最后一个带 `cache_control` 的 block 序号；
- 工具轮测试：第 1 轮让假模型回一个 `tool_use`，宿主再发第 2 个请求。第 2 个请求里**不能出现新卡**，第 1 个请求的前缀在第 2 个请求里字节一致（比较前缀 sha）；
- 隔离环境的 JSONL 里没有卡片正文；四轮 system 哈希相同；
- 生产 `/run/c-memory-v2/` 没有任何新文件。

**部署**：01:00 之前把三个 JS 复制到正式 mods 目录。**不要创建** `recall-courier-on`。

### Step 3：正式开启（琪琪在线时）
1. 10/18 切窗后先看 `courier-loaded.json`：pid 必须等于 `pgrep -f 'claude --model'`；census 的 slotCount 在增长。
2. 记下开关打开前 24 小时的缓存基线（§5 的脚本）。
3. `touch /run/c-memory-v2/recall-courier-on`，同时把 wrapper 的影子调用关掉（同一时刻只能有一个调用方运行旧召回）。
4. 24 小时后验收：

| 指标 | PASS |
|---|---|
| `courier-receipt.jsonl` 里 pid 与正式进程一致的回执 | 每天 4–15 次 |
| JSONL 里能 grep 到卡片正文 | 0 次（用回执的 `ids_sha` 对应的正文片段去 grep） |
| 缓存（§5） | 全部通过 |
| 延迟 | router elapsed p95 ≤ 1.5 s |
| 琪琪的感受 | "他又会想起事了" |

回退：`rm /run/c-memory-v2/recall-courier-on`，立即生效。

### Step 4：V2 补漏的样例收集
- 从 `recall-router.jsonl` 里取出"旧召回为空、V2 ready"的轮次，用 `show_source.sh` 把记忆原文调出来，和那一轮琪琪的话放在一起给琪琪看。每条让她选"相关 / 不相关 / 时机不对"。结果记到 `router/v2-labels.jsonl`。
- **琪琪认可后**才 `touch /run/c-memory-v2/v2-complement-output-on`。认可之前不要开。

---

## 5. 缓存指标脚本（只读）

```bash
python3 - "$JSONL" <<'EOF'
import json,sys,statistics
seen={};rows=[]
for l in open(sys.argv[1]):
    try: r=json.loads(l)
    except: continue
    if r.get('type')!='assistant': continue
    m=r.get('message') or {}; u=m.get('usage') or {}
    if not u or m.get('id') in seen: continue
    seen[m.get('id')]=1
    rows.append((r.get('timestamp'),u.get('cache_read_input_tokens',0),u.get('cache_creation_input_tokens',0)))
cr=[c for _,_,c in rows]
print('n',len(rows),'median_create',statistics.median(cr) if cr else None,
      'big>10k',sum(c>10000 for c in cr[1:]))
EOF
```

PASS：
- 中位数不超过基线的 2 倍；
- 单次 >10k 的缓存新建，除去首条和 compact 之后的首条，≤ 2 次；
- 有卡的轮次与相邻无卡的轮次相比，create 只多卡片的量级；
- 下一轮 read ≈ 上一轮 read + create。

---

## 6. 红线（违反任何一条都要立刻停下，告诉琪琪）

- 不重启、不切换正式 CC；不向主模型发测试请求。
- 不读写、不改写任何 transcript（只读统计除外）；不打开 `legacy-retained-recall-output-on`。
- 不改 Claude Code 二进制。
- 测试不写生产路径（`guard_test_paths.sh`）。
- 不动 Gate 阈值和旧召回参数。
- 不新增计划外的开关或子系统；不给 PLAN.md 加新节。
- 不把隔离测试结果说成"已恢复"。"完成"只看 Step 3 的 PASS 表。

---

## 7. 每步汇报模板（发给琪琪）

```
Step N｜开始 hh:mm｜结束 hh:mm
改了什么：<文件 + 一句话>（备份在 …）
验收：<逐项数字> → PASS / FAIL
回滚：<一条命令>
下一步：Step N+1，需要你同意吗？（或：FAIL，等你决定）
```

---

## 8. 做完之后

Step 3 PASS、Step 4 样例收集完毕后，在 STATUS.md 顶部写一句"等待 Claude 检查"，列出：
- 所有改动文件和备份路径；
- 三个日志文件的位置；
- Step 1–3 的验收数字。

琪琪会带着这些去找 Claude。
