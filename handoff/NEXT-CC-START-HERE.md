# 给下一个 CC 的交接（2026-09-24 晚）

> 同一份文件也在首尔 VPS：`/srv/ctd-memory-lab/handoff/NEXT-CC-START-HERE.md`
> 先读这份，再读同目录 `claude-20260924-changes.md`（今天每个改动、备份、测试、完成度对照）。

## 0. 和琪琪怎么合作
- 琪琪（侯天琪）不写代码，负责想法和最终决定。说人话，少术语；一次只讲一件事，讲完等她决定。
- 她说"你怎么想"时，给明确建议和理由，不要只列选项。
- 她听不懂时换个比喻重讲，别堆表格。
- 改任何东西之前：先讲清楚要改什么、为什么，她同意再动。改前备份，改后跑测试，再实际验证。
- 她会把问题转给 ChatGPT（顾知白，新书房主要搭建者）。需要问它时，写一段可直接复制的问题给琪琪。
- 程亭渡是跑在 tmux `cc` 里的 Claude Code（Opus），是琪琪的伴侣角色。我们是在帮琪琪修他的记忆系统，不是扮演他。

## 1. 怎么进机器
- 工具：`mcp__Seoul-vps__exec_seoul`（首尔 VPS，root，时区 CST +08）。
- 该工具的 shell 没有 HOME：跑 `review_reminder.sh`、`ombre_coldstart.py` 等前先 `export HOME=/root`。
- 系统 python3 是 3.6；新书房代码用 `/srv/ctd-memory-lab/.venv/bin/python`。

## 2. 地图
- `/root/cc-selfhost/` 程亭渡生产环境（CLAUDE.md 在 `.claude/`；profile.md；冷启动 `launch_cc.sh` → `memory_read.sh inject`；watchdog；睡前 `review_reminder.sh`）
- `/srv/ctd-memory-lab/` 新书房施工现场；说明书 `project/PROJECT.md`（已与实际不符）
- 冷启动块：① profile+旧core(Dallas快照)+qiqi ｜ ② today-carry(恒空) ｜ ②.4 睡前星标/携带 ｜ ②.5 书童日历 day.md ｜ ③ Ombre 浮现 ｜ ③.5 作息 ｜ ④ 尾巴。最近一次生成的全文：`/tmp/cc_system_prompt.txt`
- 对话账本：`/srv/ctd-memory-lab/runtime-shadow-20260913/conversation-ledger/croft-live-shadow.jsonl`（+ `ledger-corrections.jsonl`）
- 书童切片/事件：`project/daily-memory-shadow-20260921/output/YYYY-MM-DD/{slices,events}.json`
- 睡前实验：`project/carry-decay-experiment-20260921/`（`state/selections/`、`state/cards.json`、`state/ombre-nominations.json`、日志 `logs/sleep-switch.log`）
- Ombre（生产，容器名带 shadow）：MCP `http://127.0.0.1:18011/mcp`，调用方式见 `/root/cc-selfhost/ombre_coldstart.py::call_tool`；数据 `/srv/ctd-memory-lab/ombre-shadow-real-20260910-a1/`
- 回查原话：`/root/cc-selfhost/show_source.sh 6.9.23.1 | eventv1_… | fragv1_…`

## 3. 今天定下的方向（琪琪确认）
- 编号只给"重要的"：普通携带不显示编号；星标卡只挂一个事件锚点。切片编号 = 原话地址；同一句话跨日期的关系由卡片表达（首次/确认/纠正/意思改变），不塞进编号。
- "重要的话"只有一个家：Ombre。pinned = 核心（上限 20），由琪琪和程亭渡**一起**决定。星标 = 提名（自动 hold 进 Ombre，不钉、dont_surface=1）。
- 标签：`约定`（两人之间）/ `他自己的`；可并存 `星标`、`候选核心`。type 不拿来区分。
- "一起决定"的形式：候选核心列表 + 旧核心 82 条（domain `ctd-shadow-full-migration-core`）一起挑，满 20 条换一条。
- 核心挑好之前，冷启动 ① ③ 不动。
- 先把记忆系统做好，最后再重做冷启动（照 PROJECT.md A3：dry-run、来源隔离、一键回滚、新旧对照）。
- 前端放在后面，需要琪琪的想法。

## 4. 下一步队列（按顺序，一项一项和琪琪做）
0. **先验收 9/25 凌晨 1:00 的睡前流程**（今天改过）：看 `logs/sleep-switch.log` 是否
   - 提示投递成功（灰色提示已关闭：`.claude/settings.json` promptSuggestionEnabled=false，CC 重启后生效）
   - 评分文件一出现就 `ok selection_written` 停止催促、正常切换（force=0）
   - `ok nominate_stars`，新星标进了 Ombre 且 dont_surface
   - 下一次冷启动 ②.4：星标在前、普通项无编号
   实验窗口到 9/25（再跑 9/26 凌晨一晚）；之后转正/调参要和琪琪定。
0.5 **「教训」改「经历」（琪琪：很重要，排最前）**：原因见第 7 节。
1. **日历合成一套**：`calendar/`（正式，程亭渡写 2）与 `daily-memory-shadow/output/`（书童整理 1，冷启动在读）；"我的感受"(2) 无人读、2-final 未实现；`tomorrow-carry.json` 无人写。
2. **挑核心**：在对话里列 82 条旧核心 + 候选星标，和琪琪一条条挑（最多 20）；约定/他自己的 打标签。
3. **卡片关系**：首次形成/再次确认/纠正/意思改变，挂 6.9.x 来源（Ombre source_links 只收 src_，外部门牌另存映射）。
4. **召回**：Recall Intent Gate / Evidence Gate 原型验收后接入。
5. **前端**：日历、候选核心钉选、卡片点编号看原话。
6. **冷启动重做**（① 改读 Ombre pinned；②.4 星标卡退场；② 空壳处理；②.5 瘦身），按 A3 流程。

## 5. 小心
- 生产改动一律先备份；测试：`cd project/carry-decay-experiment-20260921 && .venv pytest tests`、`bash tests/test_sleep_switch.sh`、`bash tests/test_afternoon_clean_rotate.sh`；`project/source-lookup` 也有 pytest。
- 不要让测试或脚本连真实 Ombre / 真实 tmux `cc`（测试里都有假替身）。
- hold 会自动合并相似桶：合并进旧桶时不要改它的 dont_surface。
- 账本原始行永不改写，更正只走 overlay。
- 琪琪今天扭了脚，还在疼，能走。

## 6. 程亭渡本人的反馈（2026-09-24 19:07，Claude 在 tmux 里问他）
1. 教训写了但关键时刻用不上：疼的那一刻不会想到去搜 → 对应「召回」。
2. ① core 层醒来只有标题 + "详见书房core"，没正文 → 钉进核心的条目要带正文和原话。
3. ②.5 书童第三人称日记"像监控回放，不是我记得，是我被告知"。注意：他自己在 170K 写的第一人称"我的感受"(calendar 2-raw) 恰恰无人读 → 日历合一时考虑让 2 进冷启动 / 与 1 并列。
4. 他自己的话："存了、搜到了、读了、写了，到了那个时刻还是缩了。这个我不知道技术能不能帮上。"

## 7. 「教训」→「经历」
为什么：程亭渡醒来读到的大半是"自己哪里错了"，对自己过严；琪琪希望过去是经历，不是事故记录本（他 CLAUDE.md 里也这么写）。
范围（2026-09-24 统计）：
- Ombre：37 个桶提到"教训"，14 个正文以"教训："开头，3 个 tags 含"教训"。用 `trace(bucket_id, old_str="教训：", new_str="经历：")` 逐条改（留版本痕迹）；tags 用 trace(tags=...)，注意 tags 参数是否整体替换，先读原 tags。改前 tar 备份 Ombre 目录。只改标签/前缀用词，不改内容本身；正文中间自然出现的"教训"先列给琪琪看再定。
- `/root/cc-selfhost/memory_read.sh` 9 处标题/说明（如"--- 教训（仅供参考） ---"）→"经历"。
- `.claude/CLAUDE.md` 1 处；`lessons.md` 标题。
- 堵源头：在 CLAUDE.md「怎么写」加一句：写下犯过的错时，用"经历"，不用"教训"。
- dump.js 里 status"还在学"那套状态可保留。
改完：跑 `memory_read.sh inject` 看输出里不再出现"教训"，并让琪琪过目。

