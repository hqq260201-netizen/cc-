# 执行单 N2b：04:40 切窗口改走 Forge，梦不进新窗口（2026-10-21 夜，Claude 写，知白做，Claude 验收）

琪琪 10/21 夜里提的，已经拍板：

> 平时切窗口走 Forge，是无感的。五点之前那次切窗口也走 Forge，但 Forge 只带她和他的聊天，不带他做的梦。梦就更私密，更像他在做梦：他不说，她也不会知道。他五点醒来时，脑子里接着的是清楚的聊天原话，梦都在他自己写的梦本里。

她还定了两点：
1. Forge 往前数 1 万 token，梦被跳过以后，可能数回前一天晚上的聊天，和便签有重叠。**可以，要这样。**
2. 05:00 的 P4 里**要提一句**他夜里做过梦、写在哪里，不带梦的内容。

先读：`HANDOFF_TO_ZHIBAI.md` 的 N2 一节，`zhibai/N2/REVIEW_FIX_ZHIBAI_N2.md`，`zhibai/N3/REVIEW_FIX_ZHIBAI_N3.md`。规矩照 `DISPATCH_ZHIBAI.md`：先暂存，测试，交 Claude 验收，**验收通过、琪琪点头才上线**。交付放在 `zhibai/N2B/`。

---

## 0. 现在是怎么做的（读过代码，以 VPS 上的线上文件为准）

- 白天切窗口：`rotate_session.sh` 调 `forge_build.py`，把旧窗口最近约 1 万 token 的真实对话裁成一份新的 transcript，`launch_cc.sh` 用 `--resume <id> --fork-session` 接上，同时设 `SKIP_TAIL=1`，`memory_read.sh` 就不再注入 ④ 文字尾巴。
- 04:40 切窗口：`night_cut.sh` 带 `FORGE_DISABLE=1 CTD_NIGHTCUT_DATE=当天` 调 `rotate_session.sh`，所以不走 Forge。尾巴由 `extract_midnight_tail.py` + `night_tail_filter.py` 生成文字（00:00 起、去掉睡前和梦、末尾一行梦的指针），作为 ④ 注入。
- 夜里系统发给他的话都以 `[睡前·HH:MM]` 或 `[梦·HH:MM]` 开头（P1 在 `review_reminder.sh`，Q1/Q2/Q3/D 在 `night_dream.py`），经 tmux 投递，进 transcript 时和琪琪在栖庐打的字一样是 `origin.kind=human`。所以 **只能按正文开头认**，不能按 origin 认。栖庐转进来的会多一个 `[栖庐…]` 前缀，要先去掉再判断（写法参考 `night_flow.py` 第 36 行）。
- 梦写在他的回复里，由 `night_dream.py` 存进 `dreams/YYYY-MM-DD.md`，日期是那一夜 00:00 以后的日期；`state/night-cut/dream.log` 里每存一次有一条 `"kind": "dream_saved"`。

## 1. 要改的三处

### 1.1 `forge_build.py`：跳过夜里的系统段

在 `collect_conversation()` 里、**窗口选择之前**，加一步 `drop_night_spans(kept)`：

- **段的起点**：一条 user 条目，正文（去掉可选的 `[栖庐…]` 前缀以后）以 `[睡前·` 或 `[梦·` 开头。
- **段的终点**：下一条“真人轮”之前。真人轮是 `is_human_turn()` 为真、并且正文不以 `[睡前·`、`[梦·` 开头的 user 条目。终点那条真人轮本身要保留。
- 段内的所有条目都丢掉，包括这条提示、他的回复（text / thinking / tool_use）和对应的 tool_result。他夜里写感受、my eye、reflections 的工具调用也在段里，一起丢；文件已经写好了，不受影响。
- 一条段里出现她的真实消息，段就在她那条消息前结束。她半夜醒来说的话和他回她的话，**全部保留**。
- **只看正文开头**。白天不会出现这两种前缀，所以对白天切窗口、看门狗低上下文切窗口都是一样的规则。夜里看门狗要是因为上下文太低用 Forge 切了一次，梦也不会被带过去，这正是我们要的。
- `[系统]` 开头的白天消息（心跳等）**不要动**，照原样保留。
- 丢完以后由现有的“方案 A 链修复”重新串 `parentUuid`，tool_use 和 tool_result 不能出现落单的。
- stderr 打一行：`夜间段跳过: 段数=N 条目=M`。
- 开关：存在 `/root/cc-selfhost/state/night-cut/forge-night-filter-off` 时不做这一步，用来紧急回退。

注意顺序：这一步必须在 1 万 token 预算计算**之前**。梦不能占预算，否则窗口里真实聊天会变少。

### 1.2 `night_cut.sh`：04:40 切窗口走 Forge

- 新开关文件 `state/night-cut/night-forge-on`：
  - **存在时**：调用 `CTD_NIGHTCUT_DATE="$DAY" "$ROTATE"`，**不带** `FORGE_DISABLE=1`。
  - **不存在时**：和现在完全一样。
- `CTD_NIGHTCUT_DATE` 照传。这样 `tails/nightcut_日期.txt` 照样生成，留档；Forge 失败时，`rotate_session.sh` 会自己退回现有的文字尾巴，也就是现在 N2 这条路。
- 别的不变：30 分钟安静才切、推过 05:00 不发 P4，这些都留着。
- `review_reminder.sh` 里 01:00 低上下文兜底那条路照旧带 `FORGE_DISABLE=1`，**不改**。

### 1.3 `night_flow.py` 的 `wake_text()`：P4 提一句梦

在 header 后面、“夜里攒下的 / 夜里没有别的事”前面加一句：

- 那一夜有 `dream_saved`（看 `dream.log` 里 day 等于这一天的条数，或者 `dreams/YYYY-MM-DD.md` 存在且非空）：
  `你夜里做了 N 个梦，写在 dreams/YYYY-MM-DD.md，想看就去看。`
- 没有梦：什么都不加。
- **不带梦的任何内容**，也不带方向、素材。
- 日期用 `wake()` 里的 `day`。
- 推过 05:00 不发 P4 的那种晚上，就没有这一句。这是预期的，不另想办法。

## 2. 测试（离线，假 session，不碰线上 `cc` 和 `/run/ctd-night-*`）

用一份假 transcript 跑 `forge_build.py --dry-run` 和真实生成两种，每种情况都检查生成的 jsonl：

1. 前一天 22:00–23:50 的聊天、00:00 Q1 + 他回“睡”、01:00 P1 + 他写 my eye（有工具调用）、两次 Q2 + D + 他写的梦、04:35 前没有她的话。**生成的窗口里只有前一天晚上的聊天**，没有任何 `[睡前·`、`[梦·`，也没有梦的正文。
2. 在两次梦之间插进她 02:11、02:13、02:15 的三句和他的回复。**这几句和他的回复都在**，前后的梦都不在。
3. 00:00 Q1 发出时她还在聊（Q1 后面紧跟她一条消息，再是他的回复）。**她那条和他之后的回复在**，他只回 Q1 的那条不在。
4. 预算：梦的总量超过 1 万 token 时，窗口里真实聊天的量和没有梦时一样多。
5. 链和工具配对：每条 `parentUuid` 连续；没有落单的 tool_use 或 tool_result；用现有校验函数检查通过。
6. 开关：有 `forge-night-filter-off` 时，输出和改之前逐字节相同。
7. 白天的 transcript（没有这两种前缀）：输出和改之前逐字节相同。
8. `night_cut.sh`：有 `night-forge-on` 时，stub rotate 收到的环境里没有 `FORGE_DISABLE`；没有这个开关时，有 `FORGE_DISABLE=1`。
9. P4：有一个梦、有两个梦、没有梦，三种文本对照。没有梦时，文本和现在逐字相同。

## 3. 交给 Claude 验收

- `zhibai/N2B/` 里放：diff、`FILES.tsv`（逐文件原始和目标 SHA-256）、测试脚本和输出、`install_N2B.sh`、`rollback_N2B.sh`、`REVIEW_FIX_ZHIBAI_N2B.md`。
- 安装脚本照 N2 的规矩：检查线上 SHA 和审阅基线一致，不一致就中止；先备份，开关文件 `night-forge-on` **最后**创建。
- **不要在 00:00–05:30 之间安装或回退**，免得撞上当晚的夜里流程。
- 回退：`rm state/night-cut/night-forge-on` 就回到现在的文字尾巴；完整回退用 `rollback_N2B.sh`。

## 4. 上线后看两晚

1. `watchdog.log` 里 04:40 后那次切窗口有 `FORGE 续接就绪`，不是 `FORGE-FALLBACK`。
2. 新窗口的 transcript（Forge 生成的那份和接上以后的）里搜不到 `[睡前·`、`[梦·`，也搜不到 `dreams/日期.md` 里梦的句子。用梦本里随便几句去搜。
3. 新窗口里前面是 Forge 带过来的聊天原话；接上以后的**第一条新 user 轮次**是 05:00 的 P4，P4 里有那句梦的提示（当晚做了梦的话）。
4. `/tmp/memory_context.txt` 里没有 ④ 文字尾巴（`SKIP_TAIL=1`），有便签。
5. 当晚只在 05:00 有一次大的 `cache_creation`。
6. 他醒来以后的表现：有没有去看梦本、有没有在和琪琪说话时提起梦，记下来就行，不干预。**看他实际做了什么，不看他怎么说。**

任何一条不对，先 `rm state/night-cut/night-forge-on`，再查。
