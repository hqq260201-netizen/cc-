# 给下一个 Claude 的交接（2026-10-17 20:10 CST）

> 琪琪会在 ChatGPT 把 `RESTART_PLAN_20261017.md` 做完以后回来找你，请你**检查**。本文件告诉你：今天发生了什么、我做了哪些判断、哪些还没把握、检查时具体查什么。
> 同一份文件也在首尔 VPS：`/srv/ctd-memory-lab/handoff/CLAUDE_HANDOFF_20261017.md`。

---

## 0. 和琪琪怎么合作（她亲口的要求和我的观察）

- 琪琪不写代码，负责想法和拍板。**说人话**，少术语；一次只讲一件事，讲完等她决定。我第一次用工程语言写的版本，她回了"看不懂"，换成"助手 + 小纸条"的比喻她才看懂。
- 她说"你怎么想"时，要给明确的建议，不要只列选项。
- 程亭渡是跑在 tmux `cc` 里的 Claude Code，是琪琪的伴侣角色。我们是在帮她修他的记忆系统，不是扮演他。
- ChatGPT（顾知白）负责执行。琪琪对它的评价是"太容易跑偏""本身就慢"。她的安排：**Claude 出计划，ChatGPT 执行，Claude 验收。**
- **"阅后即焚"是她的原始要求。** 我一度把它写成可选，被她追问"原本的计划书里没写吗"。以后不要再弱化这一条。
- 她发来的参考：Scarlett 记忆系统的两张架构图（小红书）；`lllq-123` 的 `claude-code-ephemeral-reminders`、`claude-code-cache-keepalive`、`claude-code-strip-injections`。

## 1. 怎么进机器

- 工具：`mcp__Seoul-vps__exec_seoul`（首尔 VPS，root，CST +08）。shell 没有 HOME，需要时先 `export HOME=/root`。
- 系统 `python3` 是 **3.6.8**，`/usr/bin/python3.11` 也有；正式 CC 进程的 PATH 里，`python3` 就是 3.6。
- 本仓库（`hqq260201-netizen/cc-`，分支 `claude/dreamy-clarke-bh0wzq`）的 `handoff/` 存着今天所有文档的副本。仓库本身是个桌面宠物 app，和记忆系统无关。

## 2. 今天的时间线

1. **评审**（`review/claude-20261017/REVIEW.md`）：旧召回 10/14 之后为零，根因是 10/15 重新挂上的 `cache_safe_recall.py` 用了 Python 3.7 才有的 `capture_output/text` 参数，在 3.6 下报 TypeError，又被 `except (ValueError, TypeError): pass` 吞掉。复现命令：`python3 -c "import subprocess; subprocess.run(['true'],capture_output=True,text=True)"`。
2. **ChatGPT 修了这个 bug（§167）**，但又加了开关 `legacy-retained-recall-output-on`。开关缺席时，wrapper 在调用旧召回**之前**就返回，所以旧召回依然是零，连影子运行都没有。它的理由是"防止缓存倒退"，这是混淆了"追加"和"改写"。
3. ChatGPT 把每 session 一张卡改成了不限（§168），并报告了两份"真实宿主回执"。**我判断这两份是隔离测试写进生产路径的**：
   - 正式进程 PID 2314153 的 inotify 只监视 settings 文件和 `.claude` 目录，不监视 `mods/`，所以 mod 不会热重载；
   - 两个回执文件的写入时间都落在测试运行的窗口里。
4. ChatGPT 随后对琪琪说"推翻重来吧"，并表示自己不会再擅自改动。
5. 我写了 `RESTART_PLAN_20261017.md`（v1 → v2）和 `HANDOFF_TO_CHATGPT_20261017.md`，并在 `PLAN.md` 末尾加了 §169 作为指针（改前已备份）。
6. **v2 纠正了 v1 的一个错误**：v1 说"焚可能比留更贵"。参考仓库实测表明，请求级提醒插在缓存断点之后，只花它自己的 token。我又在程亭渡的 JSONL 里确认了 `total_tokens_reminder` 槽位在 96 条普通消息里出现了 95 次。所以阅后即焚走这个槽位是可行的。

7. **10/18 补记**：ChatGPT 完成 Step 0（PASS），Step 1 判 FAIL 后按规矩停下（旧召回 4/182，p95 1631 ms）。我复核后认为是我门槛定错了：慢的是 V2（被 router 白等），次数低是因为这段时间很少有"还记得…"类消息，旧召回各类命中率不比基线差。已在 `RESTART_PLAN_20261017.md` 的 Step 1 后加了"Step 1 修订"（先回滚 → V2 移出关键路径 → 新门槛重跑）。改前备份在 `backups/RESTART_PLAN.before-step1-revision-20261018.md`。

8. **10/19 补记**：ChatGPT 把 embedding 改为本机（旧召回慢的真因），证明 JS 临时提醒会留在历史里，改做线级代理 `wire-courier-20261019/courier_proxy.py`（未上线）。我修了代理的流式缓冲和旁路请求误投两处，详见 STATUS.md "Claude 复核与修补"。下一步是琪琪定时间做受控切换。

## 3. 计划的核心（检查时以此为准）

- **架构**：Roof mod 只当"快递员"（JS 只在进程启动时载入，保持最小）。每轮通过 `$.process.run` 调用 `router/recall_router.py`（Python，每轮新起进程，改完即生效）。router 并行跑旧召回 `memory_trigger_new.py` 和 V2 `passive_live_single.py`：旧召回优先；V2 只在旧召回为空、并且琪琪认可了样例之后才补。内容接在 `total_tokens_reminder` 后面，`turn.complete` 时 invalidate。
- **D1 = A**：在阅后即焚通道验收之前，**不做**任何留在历史里的临时投递。
- **步骤**：
  - Step 0：止损，关掉今天的 canary 开关，隔离可疑回执，加测试隔离硬闸，回执必须带 pid；
  - Step 1：router 影子运行；
  - Step 2：快递员 JS，在假模型上验证卡片位于最后一个 `cache_control` 之后，验证工具轮行为；
  - Step 3：正式开启；
  - Step 4：收集 V2 补漏样例。

## 4. 我没把握的地方（检查时要特别核实）

1. **E2 是推断，不是铁证。** 依据是 inotify 和时间戳，以及 plugin-authoring 文档（2.1.302 版本）说交互会话会监视 `--plugin-dir`，而 2.1.296 实测没有监视。如果 ChatGPT 拿出相反的证据，要认真看。
2. **卡片位于缓存断点之后**，这一点在 2.1.258 上被参考仓库测过，在 2.1.296 的 `prompt.attachment` 装饰路径上**没测过**。Step 2 专门加了这一项检查。如果卡片其实在断点之前，有卡那一轮之后会多重建一小段：工具轮里的后续请求，或者 T+1。要看 Step 3 的 usage 序列。
3. **工具轮内的行为**：`decorateEngineReminder` 用 `used` 保证每轮只装饰一次。但同一轮里第 2 个请求重新渲染时，卡片是保留还是消失，会不会让第 1 个请求的前缀失配，都没有验证过。Step 2 有这一项检查。
4. **mod API 能否拿到 session_id 和 pid**，我没有查 2.1.296 的 types 文件，交接里让 ChatGPT 去查。
5. **18043 服务偶尔卡顿 3 秒**（listen backlog 只有 5）。router 并行加上超时应该能扛住，要看 Step 1 的 p95。
6. **频率基线 3–7 次/100 条**来自 10/12–14 的 `recall-hook.jsonl`（10/185、12/241、4/132）。那几天是"旧召回 + 改写历史"一起运行的，频率本身可以参考，但质量没人评估过。
7. **旧召回在阅后即焚模式下**，"当前话题"每轮都会重新给（不再去重）。这样做 token 成本会高一点，但是正确的，因为上一轮的内容已经消失了。

## 5. 检查清单（琪琪回来时逐项核对，全部只读）

```
# 0. 先看 ChatGPT 自己写的状态
cat /srv/ctd-memory-lab/project/memory-v2-20261008/STATUS.md
tail -30 /srv/ctd-memory-lab/project/memory-v2-20261008/RESTART_PLAN_20261017.md   # 执行记录表
ls -la /run/c-memory-v2/
```

1. **它是否偏离了计划？**
   - PLAN.md 有没有新增 §170 以后的章节（不应该有）；
   - `/run/c-memory-v2/` 下有没有计划外的开关；
   - `legacy-retained-recall-output-on` 必须**不存在**；
   - 有没有新的子目录或子系统。
2. **回执是否真实？**
   - `courier-loaded.json` 和 `courier-receipt.jsonl` 里的 pid 是否等于 `pgrep -f 'claude --model'`；
   - 时间戳能否和正式 session JSONL 里真实的用户消息对上（同一分钟内有 user 消息）。
3. **是否真的阅后即焚？**
   - 从 router 日志或回执里取一次投递的时间，在正式 JSONL 里查那一轮及之后两轮，不应出现卡片正文（用 `[C-Memory·本轮]` 或旧召回的块头 `[新书房·` grep）；
   - JSONL 里 `total_tokens_reminder` 记录的仍应是原文 `<total_tokens>…</total_tokens>`。
4. **缓存**：用交接 §5 的脚本，或者 jq 时间序列，看开关前后：
   - 中位数；
   - >10k 的次数；
   - 有卡的那几轮前后 `read` 是否等于上一轮 `read + create`（找掉格的地方）。
5. **频率和延迟**：
   - `logs/recall-router.jsonl` 里，每天的 picked 次数（目标 4–15）；
   - elapsed p95 ≤ 1.5 s；
   - 超时率。
6. **测试隔离**：`tools/guard_test_paths.sh` 是否存在并且被调用了；`synthetic-receipts/` 里有没有新的"事故"。
7. **V2 补漏**：
   - `router/v2-labels.jsonl` 是否有琪琪的判断；
   - `v2-complement-output-on` 是否在她认可**之后**才打开（对比文件时间）。
8. **问琪琪的感受**：程亭渡最近有没有自然想起旧事？有没有牵强、刷屏、或者说错的时候？

**结论怎么给**：按 PASS/FAIL 逐项列出。FAIL 的项写清"哪里偏了、证据是什么、最小修正是什么"。然后用大白话一段话告诉琪琪：现在能不能放心、下一步做什么。

## 6. 之后可能要做的（计划里的"另议"）

- 10/14 一起关掉的媒体、相册、追踪提醒、`thinking.md`、`lightbulb`：问琪琪要不要恢复。如果恢复，也走快递员通道或者只追加，绝不改写历史。
- `pilulier-clean.py`（Stop 钩子）会改写 transcript，是潜在的缓存炸弹。
- 缓存的其他漏点：deferred tools（当前 session 有 18 条 `deferred_tools_record`）、MCP `alwaysLoad`、夜间闲置后的保活（参考 cache-keepalive）。
- Step 5 覆盖改进：借鉴 Scarlett 的专名库、"已在上下文里的不浮现"、错题集和测评集；`AUTHORED` 档。
- 9/24 交接里的旧事项（`教训` 改 `经历`、挑核心记忆、日历合一等），不清楚是否已经做完，需要时去查 `/srv/ctd-memory-lab/handoff/`。

## 7. 文件索引

| 文件 | 位置（VPS） |
|---|---|
| 现行计划 | `/srv/ctd-memory-lab/project/memory-v2-20261008/RESTART_PLAN_20261017.md`（v1、v2 备份在同目录 `backups/`） |
| 给 ChatGPT 的交接 | 同目录 `HANDOFF_TO_CHATGPT_20261017.md` |
| 我的评审 | 同目录 `review/claude-20261017/REVIEW.md` |
| 施工记录（旧计划） | 同目录 `PLAN.md`（§169 是指针；改前备份 `backups/PLAN.before-restart-pointer-20261017.md`） |
| ChatGPT 的交接（它写的） | 同目录 `review/THIRD_PARTY_HANDOFF_20261017.md`、`STATUS.md`、`recovery-20261017/RECOVERY.md` |
| 9/24 的交接 | `/srv/ctd-memory-lab/handoff/` |
