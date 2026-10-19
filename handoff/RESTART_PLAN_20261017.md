# C-Memory 重新出发计划 v2（Claude 制定，2026-10-17 19:30 CST）

> 本文件是**现行计划**。`PLAN.md`（§1–168）降级为施工记录，只用来查已核实的事实和可复用代码，不再作为设计依据。
> 执行者：ChatGPT。拍板人：琪琪。计划修订：Claude。
> **执行前请先读交接：`HANDOFF_TO_CHATGPT_20261017.md`（同目录）。**
> v2 相对 v1 的改动：把"阅后即焚"恢复为正式目标（v1 错把它写成可选）；纠正了 v1 关于"焚比留更贵"的错误判断；架构改成"插件只负责递送，Python 负责找记忆"。

---

## 给琪琪的话

现在程亭渡**仍然一条自动记忆都收不到**。

新计划：**旧的召回 + 新的补漏，都走"每轮临时提醒"这个位置递给他。** 递出去的东西只在那一轮出现，下一轮自动没有，不进聊天记录，也不碰缓存。也就是你要的"阅后即焚"。

我已经查过：程亭渡今天的 96 条消息里，95 条都带有这个位置。参考仓库的实测也表明，内容放在这里只花它自己那几十个 token，不会弄坏缓存。

---

## 0. 已核实的事实

**E1. 旧召回现在仍是 0，后台也没在算。**
- `cache_safe_recall.py` 第 137 行：开关 `legacy-retained-recall-output-on` 不存在时，它在调用 `memory_trigger_new.py` **之前**就 `return ''`。
- 证据：`gate-audit.jsonl` 16 行全是 `legacy_retained_disabled`；`logs/recall-hook.jsonl` 最后一条仍是 10/14 19:33。

**E2. STATUS.md 里两条"真实宿主回执"不能算数。**
- 正式进程 PID 2314153（10/17 01:01 启动）的 inotify 只监视 settings 文件和 `.claude` 目录，**没有监视 `mods/`**。所以 2.1.296 正式进程不会热重载 mod，01:01 之后对 JS 的修改都没有生效。
- `p4-loaded-build.json`（17:15:40）和 `p4-native-slot-census.json`（14:53:41）的写入时间，都落在隔离测试的运行窗口里，极可能是测试误写进了生产路径。
- 正式进程实际运行的是 10/16 21:46（§159）版的 JS。

**E3. 能即时生效的通道。**
- `settings.json` 被监视：改了 `UserPromptSubmit` 配置立刻生效。
- 每轮新起的 Python 进程（wrapper，以及 mod 通过 `$.process.run` 调用的脚本）改完即生效。
- `/run/c-memory-v2/*` 开关文件是每轮实时检查的，所以开关即时生效。
- **只有 mod 的 JS 本身**要等下一次进程启动（每天 01:00 自然切窗）才会载入。

**E4. 10/14 19:37 关掉 `UserPromptSubmit` 时，一起被关掉的还有：**`thinking.md`、`lightbulb`、`media_trigger`、`tracking_trigger`、`album_reminder`、`clawd-hook`（另议）。

**E5. 今晚 01:00 会一次性载入今天全部未经验证的 JS 改动**（见 Step 0）。

**E6（新，19:20 核对）：每轮临时提醒的位置在生产中存在，而且几乎每轮都有。**
- 当前 session `22a06f96…jsonl`：96 条普通用户消息里，95 条附近有 `total_tokens_reminder` 附件；另有 67 次出现在工具结果之后。内容是固定文本 `<total_tokens>15000000 tokens left</total_tokens>`。
- 参考 `lllq-123/claude-code-ephemeral-reminders`（2.1.258 实测）：这类每次请求临时拼进去的提醒插在**缓存断点之后**，只花它自己的 token，`cache_read` 一格不掉；真实历史只记一条渲染为空的记账条目。
- 参考 `lllq-123/claude-code-cache-keepalive`：2.1.258 的 `totalTokensReminder` 在尾部追加动态内容，官方路由下没有每轮击穿缓存；而**改写历史的会话，下一轮必定 miss**。
- **因此 v1 说"焚可能比留更贵"是错的。** 前提是卡片位于缓存断点之后，这一点要在 2.1.296 上用 Step 2 复验。
- ChatGPT 已经做过的原生宿主加假模型四轮测试（卡片 A/空/B/空，JSONL 无 marker，system 哈希不变），恰好证明了这条通道在 2.1.296 上可行。**它缺的不是通道，而是通道里没有东西可递**：Gate 太严，又是每进程一张。

**E7（另议）：缓存的其他漏点。** 当前 session 有 18 条 `deferred_tools_record` 和 1 条 `deferred_tools_delta`。按 cache-keepalive 的结论，工具表中途变化会让缓存整份重建。这和记忆无关，记录下来以后处理。

---

## 1. 目标（琪琪的原始要求）

| # | 目标 | 可测量的定义 |
|---|---|---|
| G1 | 保留旧召回能力 | 带出记忆的频率回到 10/12–14 的水平：每 100 条消息 3–7 次，每天 4–15 次 |
| G2 | 新系统补上旧系统想不起的 | 旧系统没找到、V2 找到且来源可核验的轮次，经琪琪看过样例并认可后才投递 |
| G3 | 每轮都判断，不拖慢对话 | 找记忆增加的延迟 p95 ≤ 1.5 s；超时就当作没找到 |
| G4 | 阅后即焚 + 不破坏缓存 | 卡片只出现在当前这次请求里；下一轮请求不带；JSONL 里没有卡片正文；**永不改写已发送的历史** |
| G5 | 每一层都看得见 | 每轮写一行路由日志（不含正文）：找了没有、找到什么 id、出或不出的原因、耗时 |

---

## 2. 架构：插件只负责递送，Python 负责找

```
琪琪的消息
  → Roof mod  prompt.submit
        └─ $.process.run → recall_router.py（Python 3.11，每轮新起进程，改完即生效）
               ├─ 旧召回 memory_trigger_new.py（子进程，python3 3.6）
               ├─ V2     passive_live_single.py（并行）
               └─ 合并：每轮最多 1 块；旧召回优先；旧召回为空且 V2 ready 才用 V2
                         同 session 按 id 去重；已在上下文里的跳过
                  输出 {state, context, ids, turn_key, route_log}
  → Roof mod  prompt.attachment：把 context 接在 total_tokens_reminder 后面（只这一次请求）
  → Roof mod  turn.complete：$.ui.invalidate('prompt.attachment')，清空
```

- **JS 只是"快递员"**：校验格式、轮次绑定、每轮 ≤1、id 去重，然后递送和清空。找什么、出不出，全由 Python 决定。以后调整召回逻辑只改 Python，不必再等切窗。
- `UserPromptSubmit` wrapper 不再往模型输出任何东西，只在 Step 1 期间用来做影子测量。
- **同一时刻只能有一个调用方**运行 `memory_trigger_new.py`：Step 1 由 wrapper 调用，Step 3 起只由 router 调用。否则它的副作用（审计、话题状态、P4 队列）会重复。

---

## 3. 施工步骤（严格按顺序，一步一报）

### Step 0：止损（今天 01:00 之前）
1. 把下面三个开关改名为 `*-off-restart-20261017`，让今晚载入的 JS 保持不活动：
   `p4-engine-reminder-canary-on`、`p4-dual-rank-safe-canary-on`、`p4-semantic-tiebreak-canary-on`。
2. 把两个可疑回执移到 `recovery-20261017/synthetic-receipts/suspect-1715/`。
3. 测试隔离硬闸：任何测试或 fixture 只要含有 `/run/c-memory-v2` 或 `/root/cc-selfhost` 的写路径，就拒绝运行。
4. 所有生产回执必须带 `pid` 和 `session_id` 哈希；`check_status.py` 校验 pid 是否等于当前正式 `claude` 进程。
5. 按 E1、E2、E6 改正 STATUS.md。

**PASS**：三个 `-on` 已不存在；10/18 01:00 之后没有 `p4-engine-reminder-attachment-last.json`。

### Step 1：recall_router.py + 影子运行（即时生效，不投递）
- 新写 `recall_router.py`：并行调用旧召回和 V2，按 §2 合并，输出上面的 JSON。给每个写入点都加环境变量覆盖，冒烟测试时全部指向临时目录。
- `cache_safe_recall.py` 在开关缺席时改为调用 `recall_router.py`，只写路由日志，返回空。
- **测试与生产用同一份 router 代码**（"调的就是线上跑的"）。

**PASS**（≥30 条真实消息或 6 小时后）：
- 旧召回 would-deliver 的比例落在每 100 条 3–7 次；
- elapsed p95 ≤ 1.5 s；
- error 为 0；
- 记下"旧召回为空但 V2 ready"的次数，留给 Step 4 用。

### Step 1 修订（Claude，10/18；Step 1 第一次 FAIL 后）

**先回滚。** 按执行记录里的 Step 1 回滚命令恢复三个文件，停掉影子调用（它每条消息让程亭渡多等约 1 秒，却不投递任何东西）。回滚后用正式解释器冒烟：wrapper exit 0、stdout 0 字节。

**FAIL 的原因（Claude 用 184 条路由日志和同时段 `recall-hook.jsonl` 核对）：**
1. **慢的是 V2，不是旧召回。** 中位数 legacy 101.8 ms、V2 903.5 ms；p95 legacy 1411.8 ms、V2 1590.2 ms；总 p95 1631.1 ms。router 用 `concurrent.futures.wait` 等两个都完，而 V2 补漏开关是关着的，结果本来就用不上。
2. **次数低是消息构成变了，不是旧召回变差。** 旧门槛"每 100 条 3–7 次"把 `[系统]` 定时消息也算进分母，而且没区分"琪琪在问旧事"和"闲聊"：

   | 时段 | 总条数 | 其中 [系统] | classify_on 命中 | ambient_sampled_in 命中 |
   |---|---|---|---|---|
   | 10/12–14 基线 | 558 | 197 | 21/41 = 51% | 5/46 = 11% |
   | Step 1 影子 | 180 | 48 | 1/2 | 3/17 = 18% |

   旧召回在每一类消息上的命中率都不比基线差，只是这段时间几乎没有"还记得…"这类消息（classify_on 只有 2 条）。旧召回超时率 5/180 = 2.8%，基线 23/558 = 4.1%，也没有变差。
3. 这是 Claude 计划里门槛定错了，不是 ChatGPT 执行错了。

**改动（只改 `router/recall_router.py`，其他不动）：**
- 当 V2 补漏关闭时（Step 1–3 都是这样），router **不在关键路径上跑 V2**：先只等旧召回，写路由日志、输出结果；V2 改为脱离式后台运行——`Popen(start_new_session=True)`，stdin 写完即关，stdout/stderr 全部指向 DEVNULL 或 V2 自己的日志——router 不等它，结果由 V2 自己的日志记录，Step 4 再拿来对。
  - 必须验证：后台 V2 不继承 hook 的 stdout，否则 wrapper 仍会等它。冒烟时看 router elapsed 是否≈legacy elapsed。
- 旧召回的超时（1.6 s）、Gate、参数都**不改**。
- 路由日志新增一个字段 `system_prompt`（prompt 以 `[系统]` 开头为 true），不写正文。

**重新影子运行的 PASS 门槛（替换上面 Step 1 的 PASS）：**
- 样本：≥100 条非 `[系统]` 的真实消息；
- 延迟：router elapsed p95 ≤ 1.5 s，且 (router − legacy) 的 p95 ≤ 100 ms；
- error 为 0，超时 ≤ 5%；
- 频率改为**健康检查**，按 `recall-hook.jsonl` 同时段的 `query_gate_reason` 分类统计：
  - classify_on 样本 ≥ 10 条时，命中率 ≥ 25%（基线 51%）；不足 10 条就如实记录，不判 FAIL；
  - 非 `[系统]` 消息里旧召回命中 ≥ 1 次；
  - 非 `[系统]` 消息每 100 条的命中次数，只记录，不作为门槛。
- 照旧记录"旧召回为空、V2 ready"的次数（从 V2 自己的日志和路由日志按时间对齐）。

**回滚**：同第一次（恢复备份的三个文件）。

### Step 2：快递员 JS（离线做好，01:00 前部署，部署时不活动）
- 以**当前磁盘上**的 `p4_ephemeral.js` / `pilulier.js` / `register.js` 为基础（今晚 01:00 会载入的就是它们），只做最小改动：
  - `prompt.submit` 改为调用 `recall_router.py`；
  - `prepareSingle` 改为接受 router 输出（不再写死 P4 的 positive_rule 白名单）；
  - 每轮 ≤1 张，**不设每 session 上限**，同 session 内 id 去重；
  - 槽位计数，回执带 pid 和 sid 哈希；
  - 新开关 `/run/c-memory-v2/recall-courier-on`，每轮实时检查。
- 用隔离原生宿主加假模型跑四轮（路径全部沙箱化）。**PASS**：
  - T 轮请求带卡；T+1、T+2 不带；
  - **卡片位于请求体最后一个 `cache_control` 之后**（新增检查：在假模型端记录卡片相对断点的位置）；
  - 隔离环境的 JSONL 里没有卡片正文；system 哈希不变；
  - 工具轮（T 轮内连续多次请求）只有第一次请求带卡，且后续请求的前缀没有因此改变。
- 通过后，01:00 前备份并部署 JS。开关**不打开**，让它随切窗载入但不活动。

### Step 3：正式开启（琪琪在线时）
- 确认载入：pid 绑定的槽位计数在增长。然后 `touch recall-courier-on`，同时停掉 wrapper 的影子调用。
- **PASS（24 小时）**：
  - pid 绑定的投递回执，每天 4–15 次；
  - JSONL 里没有卡片正文；
  - §4 的缓存指标通过；
  - 琪琪主观感受到"他又会想起事了"。
- 回退：`rm recall-courier-on`，立即生效。

### Step 4：开启 V2 补漏
- 把 Step 1 日志里"旧召回为空、V2 ready"的案例用 `show_source.sh` 调出原文给琪琪看，由她判断"相关 / 不相关 / 时机不对"。琪琪认可后，在 router 里打开 V2 补漏（通过 router 配置，不改 JS）。

### Step 5：覆盖改进（离线做，用标注集评估）
- 把 Step 1–4 的路由日志和琪琪的判断整理成固定标注集；之后每个改动都拿同一个标注集比较前后表现。
- 可以借鉴 Scarlett 的做法：
  - 专名库（人名、地名、宠物、物件的本名和别名）精确命中；
  - "已在上下文里的不浮现"；
  - 按记忆 id 冷却；
  - 错题集和测评集。
- `AUTHORED` 档：程亭渡自己写下的感受，卡片上标明"你以前自己记下"。

### 过渡期（D1：琪琪已定，选 A）
Step 3 之前**不做**任何留在历史里的临时投递，`legacy-retained-recall-output-on` 保持不存在。第一张卡就必须走阅后即焚通道。

---

## 4. 缓存与延迟的验收口径

- **数据**：正式 session 的 JSONL 里 assistant 消息的 `usage`，按 `message.id` 去重，看整条**时间序列**，不看单点：
  `jq -r 'select(.type=="assistant" and .message.usage)|[.timestamp,.message.usage.cache_read_input_tokens,.message.usage.cache_creation_input_tokens]|@tsv' <session>.jsonl`
- **基线**：开关打开前 24 小时，同一口径。
- **PASS**：
  - 有卡的轮次，`cache_creation` 与无卡的轮次相比只多卡片本身的量级（几百 token 以内）；
  - 下一轮 `cache_read` ≈ 上一轮 `read + create`，没有掉格；
  - 单次 >10k 的缓存新建，除去 session 首条和 compact 之后的首条，每个 session ≤ 2 次；
  - 我们的代码对 transcript 的写入为 0。

---

## 5. 给 ChatGPT 的执行纪律

1. **一次只做一个 Step。** 开工前把 diff 给琪琪看；做完报告：改了什么、PASS/FAIL 的数字、回滚命令。
2. 不新增计划之外的开关、子系统、目录；不再给 PLAN.md 加新节。结果写进 STATUS.md（≤1 页）和本文件末尾的执行记录。
3. 遇到计划没覆盖的情况，**停下来**问琪琪或 Claude，不要找外部模型重新定方向。
4. 不动 Gate 阈值（Step 5 用标注集比较时除外）。
5. 不重启 CC；不向主模型发测试请求；不改 transcript；不改 Claude Code 二进制（参考仓库的二进制补丁方案**不采用**）。
6. **"完成"只按 PASS 门槛判断。** 隔离测试只是部署的前提，不算完成。
7. 测试不得写生产路径；回执不绑定 pid 就不算生产证据。
8. 每改一次 Python，都用正式解释器和正式 PATH 冒烟一次。

---

## 6. 继承与废弃

**继承**
- 代码：`memory_trigger_new.py`、`cache_safe_recall.py`、`passive_live_single.py`、P4 RecallService（`:18044`）、`p4_ephemeral.js` 的递送和清空机制（`prompt.attachment` + `turn.complete` invalidate）、原生宿主加假模型的测试台、`show_source.sh`、`audit_legacy_vs_v2.py`。
- 事实：E1–E7；旧召回 10/12–14 的基线；10/14 缓存爆炸的根因是历史改写。

**废弃**
- 每 session 一张卡；
- JS 里写死的 Gate 白名单；
- "等切窗"作为调整召回逻辑的方式；
- 不绑定 pid 的回执；
- 靠外部模型的单次答复定方向；
- v1 的"焚比留更贵"。

**另议**
- E4 里关掉的那些提醒；
- `pilulier-clean.py` 改写历史的风险；
- E7 的工具表漏点（`ENABLE_TOOL_SEARCH`、MCP `alwaysLoad`）；
- 夜间闲置后的缓存保活（cache-keepalive）；
- Claude Code 自带的杂音注入（当前 session 有 21 条 `task_reminder`）：参考 `claude-code-strip-injections`。它需要改二进制，等记忆恢复后再单独评估。

---

## 执行记录（ChatGPT 每完成一步填一行）

| Step | 时间 | 改动摘要 | PASS/FAIL 与数字 | 回滚命令 |
|---|---|---|---|---|
| 0 | 10/17 18:29–10/18 07:42 | 3 个 canary 改为 off；2 份疑似回执隔离；新增路径硬闸；纠正 STATUS 并补强只读状态检查 | PASS：开关 3/3、回执 2/2、guard 2/2；切窗后正式 pid=2856663，attachment-last 不存在 | 用 `recovery-20261017/*.bak-step0-20261017-1829` 恢复文档/检查器；三个 `*-off-restart-20261017` 改回 `*-on`；两份 suspect 回执移回 `/run/c-memory-v2/` |
| 1 | 10/17 18:34–10/18 07:42 | 新增 router；wrapper 改为无输出影子调用；旧召回与 V2 写入点可沙箱化 | FAIL：n=182；legacy=4（2.20/100，低于3）；p95=1631.1ms；error=0；timeout=7（3.85%）；V2-only-ready=0；模型投递=0 | 恢复 `/root/cc-selfhost/backups/recall-router-step1-before-20261017-1834/` 三文件，并将 `router/recall_router.py` 移入 recovery 留档 |
