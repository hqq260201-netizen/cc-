# 方案：发言后召回（程亭渡说出口 → 同一轮结束前看到相关旧记录）

2026-10-19 Claude 写。**这是方案，生产环境一行没改。** 依据是当天读过的代码和日志，文中写了出处。

## 0. 结论

**能做到。** 他回话的流程是 `reply ×N + done` 并行发出，然后工具结果送回去，他再写 "."。工具结果送回去的那次请求一定经过快递员，而且一定在他写 "." 之前。卡片塞在这次请求里，他就能在同一轮里看到。

能力边界：
- 气泡已经发出去了，撤不回。他只能补发一条（`mcp-bridge.js` 的 `reply` 不检查 done 之后还能不能发，代码里没有拦截）。
- 卡片只在那一次请求里出现。看到之后要不要补发，必须当场决定。
- 只有调用了 `reply` 的轮次才会触发。纯终端回复（比如"在睡。不打扰。"）不会触发。

## 1. 知白提的四点，逐条核对

### ① B 阶段投递缺陷：确认存在，单独修

- `recall_router.py:431-437`：B 命中时返回 `source='daily'`，context 是 `[C-Memory·本轮]\n[新书房·聊天摘录｜…]`，格式本身没问题。
- `courier_proxy.py` 的 `ready` 只认 `('legacy','v2')`，所以 daily 被丢掉了。
- 日志里有实证：`logs/recall-courier.jsonl` 今天有 2 条 `daily_selected` 记录，`injected:false`（14:53、15:04 CST）。
- **附带问题**：router 在返回之前就把 daily_id 写进了 `seen_ids`（`recall_router.py` 中 `persistent_selected` 的处理）。所以这 2 条虽然没投递，却已经被记成"用过了"，以后不会再出。
- 修法：元组里加一个 `'daily'`，再跑 `test_claude_fixes_20261019.py` 加一条 daily 的用例。被误标的 2 条要不要从 state 里清掉，由琪琪决定（影响很小）。**跟新功能分开提交、分开上线。**

### ② 取消息方式不能复用：确认，要写独立的识别和去重

用知白 09:41 的真实抓包 `wire-courier-20261019/native-toolturn-run/request-1.json` 核对过：
- 工具结果那次请求，最后一条 user 消息是 `[tool_result(带 cache_control)]`，里面没有带 cache_control 的文本块。所以 `current_prompt_slot()` 返回 None，日志里那 13 条 `no_slot_or_session` 就是这么来的。旧路径在这种请求里本来就不会投递，新路径不会和它抢。
- 缓存：卡片追加在最后一个 `tool_result` **之后**，也就是缓存断点之后。下一次请求 CC 不会带上卡片，前缀和上一次写进缓存的部分一模一样，缓存不断。这跟现在第一轮投递的机制相同（request-0 → request-1 已经实测过）。
- 还没核实的：上面的抓包是单个 Glob 工具。`reply ×N + done` 并行时，几个 tool_result 是不是都在同一条 user 消息里、断点是不是在最后一个块上，要在影子阶段用真实流量确认。

新增识别逻辑（只读请求，不改请求）：
1. 最后一条消息是 user，而且含有 `tool_result`；倒数第二条是 assistant。
2. 从 assistant 里取出 `name` 以 `__reply` 或 `__reply_batch_done` 结尾的 `tool_use`。按 `tool_use_id` 对上 tool_result，只认 `is_error` 不为真、内容以 `sent` 开头的，这些才是真正发出去的气泡。
3. 本轮锚点：往前找最近一条**不含 tool_result** 的 user 消息，取它的下标和文本 hash。去重键用 `sid + 锚点`，**每个用户轮次最多回想一次**。这样他补发的纠正不会再次触发，不会循环。
4. 排除：锚点文本或气泡里含 `【群聊`、以 `<agent-message` 开头的。

### ③ 检索不能照搬 B：同意

数据源用现成的台账 `runtime-shadow-20260913/conversation-ledger/croft-live-shadow.jsonl`，17617 行，每行有 `speaker`、`created_at`、`source_message_id`、`text`、`correction_of`。说话人分布：卿卿（他）12351、琪琪 4838、顾知白 390。

规则：
- 拿他刚发出的气泡文字当查询，两边的话都查，包括当天的。
- **排除他刚发的这几条本身**（台账可能几秒内就收进去了），按文本完全相同或最近 10 分钟内他自己的话来排除。
- 排序：琪琪的话优先，`correction_of` 不为空或带纠正语气（"不是/不对/说过/取消了"）的优先。打分可以借用 `hot_query_server.py` 里 `quote_hits` 的二字组打分，阈值单独调。
- 卡片上写清日期、说话人、原文，不下结论。

### ④ 耗时和消耗：同意，具体数字

- 检索放在一个常驻小服务里（台账常驻内存，建二字组倒排索引）。目标 50 ms 以内，快递员那边超时设 0.8 s，超时或出错就直接放行。不改现有的 `hot_query_server.py`。
- 没命中就什么都不加。命中最多 3 条，整张卡不超过 600 字。
- 卡片只出现在一次请求里，不进 JSONL，之后每一轮不会再为它付费。
- 用单独的开关 `/run/c-memory-v2/self-recall-on`，跟 `recall-courier-on` 互不影响。

## 2. 卡片格式（沿用他认的新书房格式）

```
<system-reminder>
[新书房·刚才那句话的旧记录]
你刚发出去的话，书房里有这些相关的原话（只供参考，有没有说错你自己判断，没错就不用管）：
- 2026-10-13 琪琪：「……原文……」
- 2026-10-02 你：「……原文……」
</system-reminder>
```

`docs/tools-reference.md` 的召回那一段补一句："回完话以后偶尔会看到『刚才那句话的旧记录』，也是阅后即焚的召回。"下次冷启动生效。

## 3. 最小改动范围

| 文件 | 改动 |
|---|---|
| `courier_proxy.py` | 新增 `reply_batch_slot()`、锚点去重、调用小服务、追加卡片、审计字段；`inject()` 在旧路径返回 no_slot 时走新路径。约 80 行 |
| 新文件 `self_recall_server.py` + systemd unit | 只读台账、倒排索引、`/query` 接口。约 120 行 |
| `docs/tools-reference.md` | 一句说明 |
| 新测试 `test_self_recall.py` | 见下 |

`mcp-bridge.js`、router、hot recall、Hook 都不动。`PostToolBatch` 留作备选（2.1.296 里有），不启用。

## 4. 验证步骤（每一步过了再走下一步）

0. **离线回放（不碰生产）**：从他过去的 JSONL 里取出每一批 reply，用当时之前的台账去检索，输出"本来会给的卡"。重点挑琪琪下一句话明显在纠正他的那些轮次（"不是/不对/我说过/取消了"），当作标准答案，看召回能找出几条；再随机抽 20 条普通轮次，看会不会乱给卡。琪琪抽看，定阈值。同时测检索耗时。
1. **离线代理测试**：用 `native-toolturn-run` 那套假上游，造 `reply×2 + done` 的并行请求，检查：只识别发送成功的气泡；卡片在最后一个 tool_result 之后；下一次请求不带卡片，前缀字节一致；纠正 reply 不会再次触发；【群聊】排除；超时放行；没命中时请求和原来一字不差。
2. **线上影子（要琪琪同意重启快递员）**：只记日志不投递，看真实并行批次的消息结构、断点位置、命中率、耗时。
3. **显示检查**：确认栖庐在 `cc_done` 之后再收到 `cc_message` 时显示正常（看前端代码，或用测试会话试一次）。
4. **打开**：`touch self-recall-on`。之后看 JSONL 里那几轮的 `cache_read`，确认缓存没断；记录他看到卡片后补发纠正的次数，以及纠正得对不对。

## 5. 回退

`rm /run/c-memory-v2/self-recall-on` 立即停止投递；快递员恢复成 `wire-courier-20261019/courier_proxy.py` 的当前版本（改之前先备份到 `backups/self-recall-20261019/`）。
