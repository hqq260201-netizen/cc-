# 月渡

程亭渡的记忆库前端。整套意象来自名字本身：**亭**边的**渡**口，夜里有月。

- 每一天是一轮月。月相是那天真实的月亮，月边的光环表示心情和说话量。
- 记忆像潮水一样分层沉淀：今天在水面，越往深处越模糊，只留最要紧的一句。
- 核心记忆是天上的星，Ombre 的记忆桶是湖上的灯，会按遗忘曲线慢慢变暗。
- 书童是那条来回摆渡的小船。每件事都系着一根渡绳，顺着它能找回当时的原话。

配色取自青绿山水的矿物颜料：黛、石青、石绿、泥金、朱砂。默认是夜色，系统浅色模式下切换成晨渡。

```
yuedu/
  server.py          只读后端（Python 3.11 标准库，没有依赖）
  static/index.html  整个前端是一个文件；没接后端时自动显示示例数据
  static/icon.svg    图标：一弯月，三层水（日 / 周 / 月），船头一盏灯
```

## 五个视图对应哪些存储

| 视图 | 讲什么 | 数据从哪来 |
|---|---|---|
| **夜** 今夜 | 农历日期、真实月相、相识第 N 天；交接便签；书童今天整理出的事件；书童状态和来信；约定 / 待办 / 想做；碎碎念 | `layered-dream-20261021/live/output/<日期>/*.md`，`daily-memory-shadow-20260921/output/<日期>/{events.json,latest-receipt.json}`，`status/bookboy-inbox.jsonl`，`plans-20260926/state/plans.json`，`murmurs-20260926/data/murmurs.json` |
| **潮** 潮汐 | 层级摘要本身：今天逐件 → 近三日 summary → 四到七日 brief → 每周 → 每月 | 同一个 output 目录下的 `summary.md`、`brief.md`、`weeks/*.md`、`months/*.md`。层级规则和 `render_coldstart_calendar_v2.py` 一致 |
| **月** 月历 | 一个月排成一片月相；点开某一天，看当天的摘要、事件，以及他自己写的感受、我的目光、但她说、经历、经验 | 原文账本按天计数，书童日目录，`calendar/YYYY/MM/<日期>/{2..6}-raw.jsonl` |
| **星** 星野 | 被钉住、标为永久、星标提名、旧核心的记忆，按时间连成星座 | C-Memory V2 `memory` + `memory_flag`（只读打开）。`tombstone` 和 `dont_surface` 都会被过滤掉 |
| **湖** 心湖 | Ombre 记忆桶：横轴是情绪，纵轴是激动程度。灯的大小代表重要度，亮度代表遗忘曲线算出来的「还记得多少」 | `ombre-shadow-real-20260910-a1/dynamic/**/*.md` 的 frontmatter。`archive/` 和 `permanent/` 只计数 |
| **溯源** 抽屉 | 点任意编号（比如 `6.10.20.1`）就能看到那一段原话 | 当天的 `slices.json` 给出 `ordered_message_ids`，再到原文账本 `croft-live-shadow.jsonl` 里取原话 |

## 接口

所有接口都是 GET、只读，需要先登录。

- `/api/tonight`
- `/api/tide`
- `/api/moons?month=YYYY-MM`
- `/api/day?date=YYYY-MM-DD`
- `/api/stars`
- `/api/lake`
- `/api/trace?refs=6.10.20.1,6.10.20.2`

登录用 `POST /api/login {"password": …}`，口令和书房共用（默认读 `ui-shadow/.ui-key`）。登录后发一个 HMAC 签名的 HttpOnly Secure cookie，30 天有效。

所有路径都能用环境变量覆盖，见 `server.py` 开头的注释。

2026-10-22 在首尔机器上用真实数据跑过一遍：全部端点一次跑完用时 0.7 秒。原文账本按文件修改时间缓存，Ombre 缓存 5 分钟。

## 部署（尚未部署）

```ini
# /etc/systemd/system/yuedu.service
[Unit]
Description=月渡 memory library (read-only)
After=network.target

[Service]
ExecStart=/usr/bin/python3.11 /srv/ctd-memory-lab/project/yuedu/server.py
Environment=YUEDU_PORT=18048
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

然后参照书房那条独立 tunnel，在 cloudflared 里加一条 ingress，把某个子域名指到 `http://127.0.0.1:18048`。

## 已知的缺口

- **心情光环大多是中性色。** 672 个 Ombre 桶里有 635 个的 valence 还是默认值 0.5，后端把它当成「未知」处理。要让月亮真正有颜色，最省事的办法是让书童给每天的事件打一个 valence。
- **书童余额没接上。** 余额在 Croft 的 `/api/bookboy`（`bookboy-status.js`）里，页面上的余额格目前显示「—」。
- **星标提名不显示。** 那 10 条星标提名在 canonical 库里都被标成了 `dont_surface`，按规则不显示。
