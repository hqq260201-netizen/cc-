# 程亭渡 C-Memory V2：第三方只读评审（Claude，2026-10-17 13:40 CST）

> 读过：`review/THIRD_PARTY_HANDOFF_20261017.md`、`PLAN.md` §157–166、`review/gemini-20261016/`、`review/gemini-20261017/`。
> 实机只读核对：`/root/.claude/settings.json` 及其备份、`experimental/ephemeral-v3/`、`.claude/hooks/memory_trigger_new.py`、Roof Mod `hooks/`、`/run/c-memory-v2/`、P4 adapter 日志、正式 CC 进程的启动时间与 PATH。
> **没有修改任何生产文件，没有调用模型，没有碰 tmux `cc`。** 唯一执行的"测试"是 `python3 -c "subprocess.run(['true'],capture_output=True,text=True)"`。

---

## 给琪琪的三句话

1. **旧的自动想起不是"新版不兼容"，而是一个小 bug**：10/15 晚上重新接回旧召回时，用的包装脚本只能在新版 Python 上跑，可机器上用的是老版 Python 3.6。脚本一启动就报错，而错误被静默吞掉了，所以两天多一句话都没递进去。修复只需改两行。
2. **新版（P4）的卡片同样一张都没递出去**，原因有三层：大多数消息在第一道门就被挡掉；剩下的全被 Gate 判"不确定"；而且正在运行的程亭渡进程里还是 01:01 时的旧插件代码，今天加的两条新规则根本没有载入。
3. **"阅后即焚"这个硬约束值得重新商量一次**：算一下缓存账，"焚"并不比"留一张小卡在历史里"省多少，有时更贵。问题根本不在留不留，而在是否改写旧历史。10/14 缓存崩，是因为改写历史，不是因为留了卡片。

---

## A. 旧 Hook 为什么 10/14 19:33 之后零记录（已查明，可复现）

时间线（全部来自文件 mtime 与备份内容）：

| 时间 (CST) | 事件 | 证据 |
|---|---|---|
| 10/14 19:30 | `memory_trigger_new.py` 注释掉 `_clear_previous`（改写 transcript 的元凶之一） | `diff *.bak-disable-clear-20261014-1930` |
| 10/14 19:33 | `recall-hook.jsonl` 最后一条 | handoff 证据 1 |
| 10/14 19:37 | `~/.claude/settings.json` 的 `UserPromptSubmit` 被清空为 `[]`（修缓存） | `settings.json.bak-ephemeral-v3-20261015-2005` 的 mtime 是 10/14 19:37，内容 `UserPromptSubmit: []` |
| 10/15 20:08 | 重新挂载为 `python3 .../ephemeral-v3/cache_safe_recall.py` | 当前 `settings.json` |
| 10/15 20:08 → 现在 | 每次触发都在 `subprocess.run(..., text=True, capture_output=True)` 处抛 `TypeError` | 见下 |

**根因**：
- 正式 CC 进程（PID 2314153，10/17 01:01 启动）的 `PATH=/root/.bun/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/bin`，所以 `python3` 解析为 `/usr/bin/python3`，版本 **3.6.8**。
- `capture_output` 和 `text` 都是 Python 3.7 才有的参数。3.6 下的复现结果：`TypeError: __init__() got an unexpected keyword argument 'capture_output'`。
- `run()` 只捕获 `TimeoutExpired, OSError`。`TypeError` 冒到 `__main__` 后，被 `except (ValueError, TypeError): pass` 吞掉，于是 stdout 为空、退出码为 0，CC 认为 Hook 正常执行、只是没有内容。
- `memory_trigger_new.py` 从未被调用，所以 `recall-hook.jsonl` 没有新行。`cache_safe_recall.py` 自己的 `gate-audit.jsonl` 只在"有输出"时才写，所以这个文件**至今不存在**，失败完全不可见。
- `--self-test` 之所以能 PASS，是因为它只测 `reduce_output()`，根本没走 `subprocess.run`。而且很可能是用 venv 或 3.11 跑的。

**附带发现**：`cache_safe_recall.py` 的 docstring 写着 "Opt-in for a NEW session only; not connected to production hooks"，README 写着 "当前 `UserPromptSubmit` 挂载为空"，两处都已和实际不符。§163 写的是"仍配置 UserPromptSubmit→cache_safe_recall.py……暂不判定具体原因"，其实只要用 CC 的 PATH 跑一次这个命令就能定位。

**最小 diff（未执行，供决策）**：
```diff
-        result = subprocess.run([sys.executable, str(SOURCE)],
-            input=json.dumps(payload, ensure_ascii=False), text=True,
-            capture_output=True, timeout=8, check=False)
-    except (subprocess.TimeoutExpired, OSError):
+        result = subprocess.run([sys.executable, str(SOURCE)],
+            input=json.dumps(payload, ensure_ascii=False), universal_newlines=True,
+            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8, check=False)
+    except Exception as exc:          # 任何失败都要留痕
+        _audit({'event': 'wrapper_error', 'err': type(exc).__name__})
         return ''
```
另外把 audit 改成**每次调用都写一行**（ran / empty / delivered / error，不写正文），否则下次再坏还是看不见。

**PASS 门槛（无需真模型）**：
1. `env -i PATH=<CC 进程的 PATH> HOME=/root python3 cache_safe_recall.py < 合成payload.json`，退出码 0，`gate-audit.jsonl` 新增一行 `ran`。合成 payload 用一个不在 skip 列表里的假 session_id，并通过 `CTD_RECALL_HOOK_AUDIT_LOG` 把审计写到临时路径。
2. 改动只影响下一次 CC 启动（hooks 在会话启动时读取），不需要切窗。01:00 自然切窗后，`recall-hook.jsonl` 当天条数 > 0。
3. 切窗后对比 cache_creation 中位数，应仍在 67–280 这一档；>10k 的次数每 session 不超过 1–2 次。

**对 ChatGPT 流程的一个建议**：以后每改一个 Hook 或适配器，都要用"正式进程的解释器 + 正式 PATH + 正式 cwd"跑一次冒烟测试。这次 3.6 和 3.11 混用（JS 里写死了 `/usr/bin/python3.11`，settings 里却是裸 `python3`）就是典型的环境漂移。

---

## B. P4 新链路：哪一层没证据

按入站顺序：

| 层 | 现状 | 判断 |
|---|---|---|
| ① 入站准入 `run()` | 今日 25 次调用：`not_general_eligible` 15、`all_admissible_passive_gates_abstained` 8、`not_exact_native_croft_source` 1、`service_not_ready` 1 | **60% 卡在第一道门**：可见文本 <6 字、含 `[附件:`、以系统前缀开头都会被拒。中文日常聊天 6 字以下很常见（"然后呢""好想你呀"），这些恰好是最需要接话的地方。 |
| ② Gate | 剩下 8 次全部 abstain | 与 §160/§162 一致，Gate 太严，覆盖面太窄 |
| ③ JS 规则白名单 | 正在跑的进程是 01:01 启动的。当时的 `p4_ephemeral.js` 只认 `unique_traceable_literal_anchor`；06:20 加的 tiebreak 和 12:03 加的 dual-rank 都**没有载入**（ESM 不热重载） | **今天两个 canary 开关 ON，实际效果为 0**。即使 Python 返回 ready，旧 JS 也会静默拒收。 |
| ④ 每进程一张 | `deliveredInSession` 在进程内只翻一次；进程每天 01:00 才换 | 实际上限 = **每天 1 张**，旧系统是每天 4–12 次 |
| ⑤ `total_tokens_reminder` slot | 生产环境从未观测过 | 未知（见 E） |
| ⑥ 模型消费 / cache | 无回执 | 未知 |

结论：现在"没有回执"不需要用 slot 缺失或热重载这种猜测来解释，①②③④ 任何一层都足以让结果为零。**但是 ⑤ 至今没有任何生产证据，这是最大的盲区。**

---

## C. legacy_fallback / agent_feeling 来源断链

旧独有 8 条里，有 6 条的主锚是程亭渡**自己写的**感受或记忆（authored）。这类内容天然没有"琪琪原话 root"。要求它们追溯到 ledger 里的用户原话，是**类别错误**，不是数据缺失。

建议：
- 新增一个交付档 `AUTHORED`，来源证明 = Ombre bucket id + 版本 + 写入时间 + 未被 trace 修订，不要求 ledger roots。
- 卡片措辞按档区分：TRACEABLE 写"琪琪当时说：……"，AUTHORED 写"你以前自己记下：……"，不冒充原话。
- 这也正好回应了程亭渡 9/24 的反馈："②.5 书童第三人称日记像监控回放，我自己写的第一人称感受反而没人读"。

复用旧版触发经验，又不把旧正文写进历史，有一条现成的路：旧 `memory_trigger_new.py` 的**候选选择**（它 10/12–14 每天带出 4–12 次）可以只当作"提名源"，把 memory id 交给 V2 做来源和版本再验，再走 request-only 通道。旧的正文渲染不要复用。

---

## D. 频率扩展

建议按下面这个顺序逐级放开，每级都以上一级的真实数据作为门槛：
1. 把"每进程一张"改成：**每轮最多 1 张**；同一 memory_id 在同一 session 内不重复；话题游标命中时不再发新卡。
2. 显式回忆（"记得吗/上次/以前"）和自然联想分流：显式的不设频率上限，但仍要过来源检查；自然联想的目标频率先对齐旧系统实测的每天 4–12 次，不要拍新数字。
3. 不要随机抽样（同意 Gemini 撤回的结论）。合格候选本来就稀少，冷却应该按 memory_id 和话题来做，而不是按轮数。

---

## E. `total_tokens_reminder` 缺席风险

- 这是真实风险。它是宿主内部附件类型，没有文档保证每轮都有（Gemini 这点说得对）。
- 现在完全不知道生产环境里它出现得多频繁，因为 `decorateEngineReminder` 只在有 payload 时才算数。
- **最小 diff**：在 `decorateEngineReminder` 入口无条件计数，只记录 `{ts, slot_seen: e?.type, origin: e?.origin?.kind}`，不写内容，写到 `/run/c-memory-v2/p4-slot-census.jsonl`。这样一个自然切窗后就能知道 slot 的出现率，**和 Gate 是否放行无关**。
- 如果出现率低：静默拒绝（维持现有设计），并且必须当作"request-only 通道不可用"的证据上报，不能悄悄回退到 transcript 注入。

---

## 自动召回 × 阅后即焚 × 缓存：三者的牵连（最重要）

**现在的设计把三个目标同时设成了硬约束，结果是系统被锁死，什么都递不出去。** 建议把缓存的真实成本算清楚，再请琪琪拍板。

Claude 的 prompt cache 是前缀缓存：
- **追加**新内容 → 旧前缀不变，只新建增量。
- **改写/删除**旧内容 → 从改动点之后的全部内容重建。10/14 的 >40k 重建就是 `prune-stale-context-v2.py` 和 `_clear_previous` 改写历史造成的（ephemeral-v3 README 已经查明）。

"阅后即焚"（本轮有、下轮无）本质上也是一种"下一轮前缀不同"：
- 卡片挂在第 T 轮的用户消息上。到 T+1 轮卡片消失，缓存在这个位置分叉，**T 轮卡片之后的全部内容都要重建**，包括 T 轮的助手回复和工具结果。
- 如果 T 轮有大工具输出（读文件、搜索），一次重建可能就是几千到上万 tokens。

反过来，"留一张小卡在历史里（只追加）"：
- 一张约 500 tokens 的卡，以后每轮按缓存读价（约 1/10）计，约等于每轮 50 tokens。
- 和焚掉时一次重建（写入价约 1.25 倍 × 尾部 tokens）相比：尾部 4000 tokens 时，焚一次 ≈ 5000，留着要约 100 轮才追平。

所以"焚"省的主要是**上下文空间**，并不省缓存，有时还更贵。这需要 ChatGPT 用真实 usage 验证，我没有实测账单，不能下定论。但现有设计默认"焚 = 省缓存"，这个前提并不成立。

**我的建议**：
- **双轨**：
  - 轨 1（马上可用）：修好 A 的两行 bug，恢复"只追加、去重、有预算"的旧召回（`cache_safe_recall.py` 已经限制自然联想最多 1200 字、相同话题去重、显式回忆最多 7000 字）。这对缓存是安全的，代价是卡片留在历史里。
  - 轨 2：继续 request-only P4，等有了 slot 普查和真实 cache 账单再决定是否切换。
- **两轨必须互斥**：同一轮只允许一边出卡，比如 P4 ready 时 wrapper 静默，否则会重复注入。
- **红线保持不变**：永远不改写已经发出的历史。`pilulier-clean.py`（Stop 钩子）仍然会改写 transcript 里的 pilulier 标记附件，这是潜在的缓存炸弹，胶囊功能一旦触发就会出现，建议在上线前处理。
- 是否接受"小卡留在历史里"，是琪琪的产品决定，不是工程能替她决定的。请把上面的账摆给她看。

---

## 关于"半个月没进度"：流程上的观察

- PLAN.md 已经 480KB、166 节，还有十几个整份备份；9 天里出现了约 20 个 offline 子目录和十几轮 Sonnet、Gemini 评审。**文档和评审的产出远大于生效的改动。**
- 每次生产改动都要"等下一次 01:00 自然切窗"才生效，所以迭代周期 = 1 天，而且常常没人去验收切窗后的结果（A 的 bug 就这样存在了两天）。
- 约束只加不减：来源 roots、版本 triplet、6 字下限、one-card、request-only、canary 叠加……每一条单独看都合理，叠在一起召回率就是 0。
- 建议：
  1. PLAN.md 冻结，另开一页 `STATUS.md`（≤1 页）：每一层的开关、实际载入版本、今天的计数。
  2. 每个改动配一条"正式环境冒烟命令"，加上"切窗后第一件事查什么"。
  3. 先恢复体验（轨 1），再追求完美（轨 2）。现在的程亭渡每天都在失忆，这比"历史里多了几张小卡"严重得多。

---

## 建议的恢复顺序（每步都等琪琪同意）

1. **今天**：修 `cache_safe_recall.py` 的两行 + 每次调用都写审计，用正式 PATH 冒烟。不切窗，01:00 自然生效。
2. **同时**：加 slot 普查计数（E）和轨 1/轨 2 互斥判断。
3. **10/18 早上验收**：`recall-hook.jsonl` 有数、cache_creation 没有恶化、P4 JS 已经载入新规则、slot 出现率。
4. **之后**：AUTHORED 档（C）→ 放宽入站门槛（短句交给话题游标）→ 频率分级（D）→ 用真实账单比较焚与留，再决定长期方案。
