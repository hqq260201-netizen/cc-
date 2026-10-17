# C-Memory 重新出发计划（Claude 制定，2026-10-17 18:10 CST）

> 本文件是**现行计划**。`PLAN.md`（§1–168）降级为施工记录，只用来查已核实的事实和可复用代码，不再作为设计依据。
> 执行者：ChatGPT。拍板人：琪琪。计划修订：Claude。
> 位置：`/srv/ctd-memory-lab/project/memory-v2-20261008/RESTART_PLAN_20261017.md`

---

## 给琪琪的话

现在程亭渡**仍然一条自动记忆都收不到**。下午那个 bug 修好了，但 ChatGPT 随后又加了一道开关，旧召回在开始找记忆之前就直接退出，连后台都没在算。它报告的两个"真实回执"，我查下来很可能是测试误写进生产目录的。

新计划只有一个思路：**先把旧的召回原样接回来，再让新系统补上旧系统漏掉的。** 两者走同一个入口：改动当场生效，删一个文件当场撤回，也不需要重启程亭渡。

有一件事需要你决定（见 D1）：想起的那段小卡片，是"留在聊天记录里"，还是"用完就消失"。我建议先留着。

---

## 0. 先纠正的事实（2026-10-17 17:49 只读核对）

**E1. 旧召回现在仍是 0，后台也没在算。**
- `cache_safe_recall.py` 第 137 行：开关 `/run/c-memory-v2/legacy-retained-recall-output-on` 不存在时，会**在调用 `memory_trigger_new.py` 之前**就 `return ''`。
- 实际证据：`gate-audit.jsonl` 共 16 行，全部是 `legacy_retained_disabled`；`logs/recall-hook.jsonl` 最后一条仍是 10/14 19:33。
- 关这道门的理由是"防止缓存倒退"，这个理由不成立。**只追加不会破坏前缀缓存；改写旧历史才会。** 10/14 的缓存爆炸来自 `prune-stale-context-v2.py` 和 `_clear_previous` 的历史改写（见 `ephemeral-v3/README.md`），不是因为卡片留在了历史里。

**E2. STATUS.md 里两条"真实宿主回执"不能算数。**
- 正式进程 PID 2314153（10/17 01:01 启动）的 inotify 只监视 5 个对象：`~/.claude/settings.json`、`cc-selfhost/.claude/settings.json`、`settings.local.json`，以及两个 `.claude` 目录。**它没有监视 `mods/ctd-roof-names/`**。所以 2.1.296 的正式进程不会热重载 mod，01:01 之后对 JS 的所有修改都没进入程亭渡正在运行的会话。
- `p4-loaded-build.json` 写于 17:15:40.42：补丁落盘是 17:15:28，隔离四轮测试在 17:16:47 结束，回执正好落在测试期间。和 14:50 那次一样，极可能是测试写进了生产路径。
- `p4-native-slot-census.json`（150 次）写于 14:53:41，落在 14:46–14:53 的隔离测试窗口内，而写它的 `register.js` 代码正式进程从未载入。理由同上。
- 结论：**生产环境里从未观测到 `total_tokens_reminder` 槽位。** 正式进程运行的是 10/16 21:46（§159）版的 JS：每进程一张卡，只认字面锚点规则。

**E3. 反过来，有两条通道是即时生效的。**
- `settings.json` 被监视，所以 `UserPromptSubmit` 配置的改动会立刻生效。14:57 出现的第一条 gate-audit 就是证明。
- wrapper 和 P4 adapter 都是每轮新起的 Python 进程，改完代码下一条消息就会用上。**本计划只走这两条通道。**

**E4. 10/14 19:37 清空 `UserPromptSubmit` 时，一起被关掉的还有：**`thinking.md` 每轮注入、`lightbulb`、`media_trigger.py`、`tracking_trigger.py`、`album_reminder.py`、`clawd-hook`。相册、媒体、追踪这几项提醒至今都是关着的（另议，见 §6）。

**E5. 今晚 01:00 自然切窗时**，正式进程会一次性载入今天全部 JS 改动：不限张数、dual-rank、tiebreak、census、loaded-build。这些都没有经过生产验证。Step 0 会让它们保持不活动。

---

## 1. 目标（回到琪琪最初的要求）

| # | 目标 | 可测量的定义 |
|---|---|---|
| G1 | 保留旧召回能力 | 自然聊天中带出记忆的频率回到 10/12–14 的水平：每 100 条消息 3–7 次，每天 4–15 次 |
| G2 | 新系统补上旧系统想不起的 | 记录"旧系统没找到、V2 找到且来源可核验"的轮次，经琪琪看样例认可后投递 |
| G3 | 每轮都判断，不拖慢对话 | 整个 Hook 增加的延迟 p95 ≤ 1.5 s；硬超时 3 s，超时就当作没找到 |
| G4 | 不破坏缓存 | 永不改写已发送的历史；具体指标见 §4 |
| G5 | 每一层都看得见 | 每轮每层写一行**不含正文**的日志：ran / empty / delivered / error / elapsed_ms |

**D1（琪琪决定）：想起的小卡片留在历史里，还是"阅后即焚"？**
- **留（推荐）**：只追加，缓存安全，已有几个月的实际使用经验。预算是自然联想 ≤1200 字、明确回忆 ≤7000 字，同一话题去重。代价是占一点上下文；按缓存读价算，每张卡每轮约几十 token。
- **焚**：卡片下一轮消失。但这会让缓存从卡片所在位置往后整段重建，一次可能几千 token。它依赖的宿主槽位在生产里还没见过，要等 Step 6 才能做。
- D1 只影响 Step 2 和 Step 4 能不能开。Step 0、1、3 不受影响，可以先做。

---

## 2. 架构：一个入口，两路检索

```
琪琪的消息
  → UserPromptSubmit → cache_safe_recall.py（唯一入口，每轮都跑）
       ├─ 旧召回 memory_trigger_new.py   （子进程，python3 3.6，已有）
       ├─ V2   passive_live_single.py    （子进程，/usr/bin/python3.11，并行，超时 2.0 s）
       └─ 合并：每轮最多 1 块
              旧召回有结果 → 用旧召回
              旧召回为空、V2 ready → 用 V2
              同一 session 内按 memory/source id 去重（复用 reduce_output 的 seen 状态）
  → 只追加进本轮（D1=留）
```

- Roof mod 的 P4 engine 通道保持**关闭**。代码保留，到 Step 6 再评估。
- 为什么这样设计：改动立即生效；删一个开关文件立即回退；只追加，缓存安全；不依赖未经验证的宿主槽位；不需要重启程亭渡。

---

## 3. 施工步骤（严格按顺序，一步一报）

### Step 0：止损（今天 01:00 之前）
1. 把下面三个开关改名，不删除，名字后加 `-off-restart-20261017`：
   `p4-engine-reminder-canary-on`、`p4-dual-rank-safe-canary-on`、`p4-semantic-tiebreak-canary-on`。
   `p4-topic-cursor-shadow-on` 保留（它只做观察）。
2. 把 `/run/c-memory-v2/p4-loaded-build.json` 和 `p4-native-slot-census.json` 移到 `recovery-20261017/synthetic-receipts/suspect-1715/`。
3. 测试隔离硬闸：所有测试和 fixture 在运行前，先 grep 自身及其拷贝的插件代码；只要出现 `/run/c-memory-v2` 或 `/root/cc-selfhost` 的写路径就拒绝运行。
4. 回执规范：以后所有"生产回执"必须带 `pid` 和 `session_id` 的哈希。`check_status.py` 要校验 pid 等于当前正式 `claude` 进程，不等就标为 synthetic。
5. 按 E1、E2 改正 STATUS.md。

**PASS**：`ls /run/c-memory-v2` 中不再有那三个 `-on`；STATUS.md 已改正；10/18 01:00 切窗后不存在 `p4-engine-reminder-attachment-last.json`。

### Step 1：旧召回影子运行（立即生效，不投递）
- 修改 `cache_safe_recall.py`：开关缺席时**照常调用** `memory_trigger_new.py`，照常跑 `reduce_output`，然后只写审计、返回空。审计行格式：`{event:'legacy_shadow', would_chars, ids_sha, elapsed_ms}`。
- 给 gate-audit 路径加一个环境变量覆盖（`CTD_GATE_AUDIT_LOG`），用于冒烟测试。先列出 `memory_trigger_new.py` 的全部写入点：recall-hook 审计、状态文件、P4 shadow 队列。每个写入点都要有覆盖变量或可以关掉，冒烟时全部指向临时目录。
- 冒烟方法：`env -i PATH=<正式进程的 PATH> HOME=/root python3 cache_safe_recall.py < 合成payload`，session_id 用假的。

**PASS**（≥30 条真实消息或 6 小时后）：
- `recall-hook.jsonl` 重新出现当天记录；
- would_deliver 的比例落在每 100 条 3–7 次；
- 整个 wrapper 的 elapsed p95 ≤ 1.5 s；
- error 为 0。

任何一项 FAIL：停下，报告，不要自己调参。

### Step 2：旧召回恢复投递（需要 D1 = 留）
- `touch /run/c-memory-v2/legacy-retained-recall-output-on`。回退方法：删掉这个文件，立即生效。
- **PASS（24 小时）**：带出频率在每天 4–15 次；§4 的缓存指标通过；琪琪主观感受到"他又会想起事了"。

### Step 3：V2 补足影子
- wrapper 并行调用 `/usr/bin/python3.11 p4/passive_live_single.py`（stdin `{prompt}`，超时 2.0 s），只记日志：`v2_reason, v2_ready, old_empty, same_memory`。不投递。
- 每一个"旧召回为空且 V2 ready"的案例，用 `show_source.sh` 调出原文给琪琪看，由她判断"相关 / 不相关 / 时机不对"。
- **PASS**：加上 V2 之后延迟仍满足 p95 ≤ 1.5 s；收集到至少 10 个补足案例，并有琪琪的判断。

### Step 4：V2 补足投递（需要 D1 = 留，且琪琪认可 Step 3 的样例）
- 新开关 `/run/c-memory-v2/v2-complement-output-on`。只在旧召回为空时投递 V2，每轮最多一块。
- PASS 条件同 Step 2，另外要求 V2 卡片的来源校验失败数为 0。

### Step 5：V2 覆盖改进（离线做，用标注集评估）
- 把 Step 1–3 的日志和琪琪的判断整理成固定标注集。之后每一个 Gate 改动，都要拿同一个标注集比较前后表现，**不再靠外部模型的意见调方向**。
- 候选改进：
  - 新增 `AUTHORED` 档：程亭渡自己写的感受，来源证明 = Ombre bucket + 版本 + 未被修订；卡片写"你以前自己记下"；
  - lexical tie 的处理；
  - 短句续聊交给 topic cursor。

### Step 6（可选，只在 D1 = 焚，或 Step 2 数据显示上下文膨胀时做）：request-only
- 前提一：在一个**新的正式 session** 里拿到绑定了 pid 的槽位计数，证明 `total_tokens_reminder` 每轮都存在。
- 前提二：用真实 usage 比较"焚"和"留"的缓存成本。只有"焚"确实更好才切换。

---

## 4. 缓存与延迟的验收口径（所有步骤通用）

- **数据来源**：正式 session 的 JSONL 里 assistant 消息的 `usage`（按 `message.id` 去重）。这是真实的 provider 账单数据，只读即可拿到。
- **基线**：开关打开前 24 小时，用同一口径计算。
- **PASS**：
  - `cache_creation_input_tokens` 中位数不超过基线的 2 倍；
  - 单次 >10k 的缓存新建，除去 session 第一条和 compact 之后的第一条，每个 session ≤ 2 次；
  - 我们的代码对 transcript 的写入为 0（`/root/.claude/backups/pilulier/` 没有新文件）。
- **延迟**：wrapper 自己记录 `elapsed_ms`，取 p95。

---

## 5. 给 ChatGPT 的执行纪律

1. **一次只做一个 Step。** 开工前把 diff 给琪琪看；做完报告三件事：改了什么、PASS/FAIL 的数字、回滚命令。
2. **不新增计划之外的东西**：开关、子系统、目录都不加；不再给 PLAN.md 加新节。结果只写进 STATUS.md（≤1 页）和本文件末尾的执行记录。
3. **遇到计划没覆盖的情况：停下来**，写清问题，等琪琪或 Claude 修订计划。不要找外部模型重新定方向。
4. **Gate 阈值不动**，Step 5 有标注集对比时除外。
5. **不重启 CC，不向主模型发测试请求，不改 transcript。** 除 Step 0 里的开关操作外，不碰 `mods/` 目录。
6. **"完成"只按 PASS 门槛判断。** 隔离测试和假模型测试只是开工的前提，不算完成。
7. **测试不得写生产路径**（Step 0.3）。回执不绑定 pid 就不算生产证据（Step 0.4）。
8. **每改一次 wrapper，都用正式解释器和正式 PATH 冒烟一次。**

---

## 6. 继承与废弃

**继承（已核实、可复用）**
- 代码：`memory_trigger_new.py`、`cache_safe_recall.py`（含 `reduce_output` 和去重）、`passive_live_single.py`、P4 RecallService（`127.0.0.1:18044`）、ledger、`show_source.sh`、`audit_legacy_vs_v2.py`；原生宿主加假模型的测试台只留给 Step 6 用。
- 事实：
  - 旧召回 10/12–14 的基线；
  - 10/14 缓存爆炸的根因是历史改写；
  - Python 3.6 bug 及其修复；
  - E1–E5。

**废弃（不再作为前提）**
- "每 session 一张"；
- 把 request-only 当作上线前提；
- "等下一次切窗"作为迭代方式；
- 不绑定 pid 的回执；
- 靠外部模型的单次答复定方向。

**另议（不在本计划内，需要琪琪决定是否恢复）**
- 10/14 一起关掉的媒体、相册、追踪提醒（E4）；
- `thinking.md` 每轮注入；
- `pilulier-clean.py` 改写历史的风险（目前只在胶囊功能触发时出现）。

---

## 执行记录（ChatGPT 每完成一步填一行）

| Step | 时间 | 改动摘要 | PASS/FAIL 与数字 | 回滚命令 |
|---|---|---|---|---|
| | | | | |
