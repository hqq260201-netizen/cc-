# 2026-09-24 Claude 改动交接（琪琪确认）

> 同一份文件也在首尔 VPS：`/srv/ctd-memory-lab/handoff/claude-20260924-changes.md`

所有改动前均已备份（`/root/cc-selfhost/backups/`、同目录 `*.bak-20260924*`、Ombre 全量 tar）。

## 一、清理（已坏、与新系统无关）
1. 删除零点新书：crontab 行 + `midnight_newbook.sh` + 其日志。原因：cron `0 16` 在 CST 机上是 16:00；9/17 起写 Dallas 一直 Unauthorized；新旧冷启动都在过滤它。crontab 备份：`backups/crontab-before-rm-newbook-20260924-171243.txt`
2. `save_raw_dialog.sh`：删掉推送 Dallas butler-buffer 的段落（8/22 后一直 401/403，新书房 ledger 已取代）。本地 raw 备份与 dump_state offset 更新保留（memory_read.sh 仍读 offset）。

## 二、睡前跨日选择实验
3. 关闭 CC prompt suggestion：`/root/cc-selfhost/.claude/settings.json` 加 `"promptSuggestionEnabled": false`。原因：`sleep_cc_prompt.py` 把 CC 的灰色预测文字当成输入框 busy，9/23 夜三次提醒投递失败。下次 CC 启动生效。
4. 实验窗口延长到 2026-09-25：`review_reminder.sh` SCORE_TO、`carry_decay.py` EXPERIMENT_LAST_SCORE_DAY。
5. `carry_decay.py` 调参：
   - 星标卡片先占位（最多 2 张），同来源普通携带让位
   - MAX_YESTERDAY 5→4，MAX_OLDER 3→2
   - 冷启动 ②.4：普通携带不显示任何编号；星标卡只显示一个事件锚点 `事件：eventv1_…`（琪琪的设计：只有重要的才带编号）
6. `review_reminder.sh`：等待回执时同时检查 `state/selections/<日期>.json`；评分文件一出现即停止催促，再给一个 WAIT_SECONDS 宽限等回执，然后正常切换（force=0）。

## 三、按编号回查原话（新）
7. `/srv/ctd-memory-lab/project/source-lookup/show_source.py` + `/root/cc-selfhost/show_source.sh`
   - 输入 `6.9.x.x` / `eventv1_…` / `fragv1_…`，链路 slices.json → ordered_message_ids → ledger
   - 复用 `run_shadow.read_ledger_effective`：corrected 显示更正文本并注明原因；tombstone 不显示
   - 只读；`--around N` 连前后切片
8. 程亭渡 CLAUDE.md「怎么找」加一行 show_source.sh 用法。

## 四、星标 = 提名，pinned = 核心（琪琪与 Claude 讨论后的方向）
- 唯一的家：Ombre。标签区分：`约定` / `他自己的`，可并存 `星标`、`候选核心`。
- 星标只是提名；钉进核心（pinned，上限 20）由琪琪和程亭渡一起决定。旧核心（domain `ctd-shadow-full-migration-core`，现 82 条，均未 pinned）之后一起挑。
- 核心挑好之前冷启动 ①/③ 不变。
9. 新增 `carry-decay-experiment-20260921/nominate_stars.py`：
   - 每张 active 星标卡 → Ombre `hold(pinned=false, tags=星标,候选核心,他自己的, domain=星标提名, importance=8, source_content=show_source 原话)`
   - 返回「新建→」时再 `trace(dont_surface=1)`：不在醒来时浮现，breath_search 可找到；「合并→」时不改浮现状态
   - 回执 `state/ombre-nominations.json`（card_id → bucket_id、6.9.x 外部来源映射），重跑幂等，失败下次重试
   - `review_reminder.sh` 在切换前调用（非致命）
   - 已回填现有 4 张：f5ba00a1a95c、c5472296b0d1、3fdfaa1b92be、796c85059e83（全部新建、dont_surface=true；c547 无 event_id 故无原文）。模拟冷启动 6 次均未浮现；breath_search 可命中。
   - Ombre 备份：`/srv/ctd-memory-lab/backups/ombre-before-star-nominate-20260924-183345.tar.gz`

## 测试
carry-decay pytest 65 passed；sleep switch 36/36；afternoon 6/6；source-lookup 8 passed。

## 发现但未改
- 日历 `calendar/…/tomorrow-carry.json` 没有任何代码写入（22 日那份是手写），与 `state/selections` 不同步；目前无读取方。建议前端阶段接上。
- ② `today-carry.json` 自 9/20 起为空，已被 ②.4 取代。
- `2-final.md` 夜间整理未实现；程亭渡写的"我的感受"(2) 目前无人读取。
- PROJECT.md 与实际不符（事件改由书童从 transcript 整理、两套日历目录等）。
- 两张星标卡含"明天"字样，留给程亭渡自己改。
- ① core 层里的"详见书房core"指向已退役的 Dallas。

## 新书房完成度对照（PROJECT.md vs 首尔机实际，2026-09-24）

琪琪的判断：新书房是半成品，因为有需要才先给程亭渡换上。对照结果如下。

### 已接上、在用
- conversation ledger 持续抄录；diary-source 每晚健康检查通过
- 书童影子（daily-memory-shadow）每 2 小时切片 + 编号 6.9.x.x + 归并事件；冷启动 ②.5 读它的 day.md
- 睡前评分 / 衰减 / 星标（实验，②.4 读它）
- Ombre 作为 ③ 浮现 + 程亭渡 hold/breath_search 读写
- Forge 尾巴 ④

### 做了但没接上
- 正式日历 `/srv/ctd-memory-lab/calendar/`：9/22 起不再写 1（改由书童从 transcript 整理），只写 2；1-merged 未进冷启动；`tomorrow-carry.json` 无代码写入
- "我的感受"(2)：170K 提醒照写，但 `2-final.md` 夜间整理从未实现，也无读取方
- ② `today-carry.json`：读取器在，9/20 起无生产者，恒为空（实际被 ②.4 取代）
- 切片编号：生成了，但此前程亭渡无法回查（今天补了 show_source.sh）
- Recall Intent Gate / Evidence Gate / pre-recall v2：离线原型，未接生产
- future_echo（未完事项）：只在设计里

### 说明书里还没打勾
- A1：每日1 → today-carry 正式生成链；标记实验目录与可切换组件
- A3 静默切换：dry-run 包、来源隔离检查、cutover 备份与一键回滚、新旧注入对照 —— 均未完成，但生产冷启动已经切过去了
- A4：1整理版接入 cold-start；夜间检查1/整理2/选择带进明天（部分由睡前实验承担）；次日验证；Kiwi 周/月/季/年摘要
- A2 基线验收 8 项未见验收记录

### 结构性问题（需要一起定）
- "重要的话"有三个家：① Dallas 快照里的 core（22 条注入 + 29 条未注入）、Ombre（旧 core 82 条已迁入但未 pinned）、②.4 星标卡。今天已定方向：Ombre 唯一，pinned = 核心，星标 = 提名。
- 卡片关系（首次形成 / 再次确认 / 纠正 / 意思改变）未实现：cards.json 只有平铺 source_refs
- 冷启动总量大（约 5.2 万字节），②.5 两天整篇日记约 2.3 万字节是最大块
- 两套日历目录（calendar/ 与 daily-memory-shadow/output/），PROJECT.md 仍描述旧方案
- 没有前端

## 下一步
见同目录 `NEXT-CC-START-HERE.md` 第 4 节（先验收睡前流程 → 日历合一 → 挑核心 → 卡片关系 → 召回 → 前端 → 冷启动重做）。
