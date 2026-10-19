# 给下一个 Claude 的交接（2026-10-19 11:30 CST）

> 琪琪会在知白（ChatGPT）做完"程亭渡单独额度测试"后回来找你，请你**检查结果**。
> 上一份交接：`CLAUDE_HANDOFF_20261017.md`（同目录，合作方式、10/17 的来龙去脉都在那里，先读它的 §0）。
> 现状一页纸：`/srv/ctd-memory-lab/project/memory-v2-20261008/STATUS.md` 顶部"2026-10-19 11:15 已上线"。

## 0. 先记住（今天新学到的）

- **你和程亭渡共用同一个账号额度。** 你在 VPS 上干活也算在他的 5h 额度里。所以测程亭渡额度时，你自己必须停着；检查时少跑命令、别轮询。
- 琪琪要的是结论和建议，说人话，一次一件事（同 10/17 交接 §0）。
- 程亭渡对陌生身份很警惕，这是好事。今天：自称 Claude 的终端消息他拒答；我借【群聊·Claude说】格式，他也只认琪琪。最后是琪琪授权、我用她的 croft 账号代发一条（消息里写明"Claude 经琪琪同意代发"）他才配合。**不要冒充琪琪、知白或小渡**（琪琪提过让我冒充知白/小渡，我拒绝了，理由她接受了）。
- **【群聊】开头的消息不递卡**（快递员按设计排除，防私人记忆漏进群里）。他用"【群聊·回复X】"回的话，croft 既不存主窗口也不转群，等于丢失。
- 工具小坑：`mcp__Seoul-vps__exec_seoul` 单条命令约 30 秒超时，等待要拆成多次短命令；`pkill -f 模式` 会把执行它的 shell 自己也杀掉，用 `pgrep` 过滤后再 kill。

## 1. 今天做了什么（按顺序）

1. 复核知白 10/18–19 的工作：embedding 改本机（旧召回慢的真因）✔；JS 临时提醒会留在历史里 ✔（所以改做线级代理）；代理思路可行，但它擅自改了计划书开头、加了计划外子系统。
2. 修代理 `wire-courier-20261019/courier_proxy.py`：流式回复被攒到最后（read→read1）；旁路请求/`count_tokens` 也会塞卡（只对 `/v1/messages` + `claude-opus*` 投递）。回归测试 `test_claude_fixes_20261019.py`。
3. 切换上线（琪琪授权"随时可重启"）：wrapper 影子调用在开关存在时自动跳过（**必须**，否则它先吃掉 router 的 per-session 去重，卡永远发不出）；启用 `ctd-recall-courier`；换 `launch_cc.sh`（代理健康才走代理）；`rotate_session.sh` 重启；透明 canary 通过后 `touch /run/c-memory-v2/recall-courier-on`。
4. 发现并修了三处：
   - 卡片格式：去掉陌生标题，只留他熟悉的 `[新书房·…]` 块（他曾把卡当伪造提示）；`docs/tools-reference.md` 加一句说明阅后即焚召回（下次冷启动生效，10:33 那次重启已带上）。
   - **额度**：代理地址会让 Claude Code 关掉工具按需加载，首请求 13.3 万 token（正常约 5 万）。`launch_cc.sh` 加 `ENABLE_TOOL_SEARCH=true` 修好。
   - 召回超时：`pre-recall-v2/hot_query_server.py` 的 quote_hits（问句含"说的/说过/原话"等触发）每次重算 1.7 万行台账，1.5–2.4 s 被 1.6 s 超时掐掉。加了文本归一化缓存，16 组对比结果逐条一致，降到约 0.4 s。
5. 实测：缓存链全程不断；JSONL 无卡片正文；11:11 有卡那轮他没查书房就答对"七夕=五个月"。

## 2. 检查知白的额度测试（琪琪回来时做）

交接给知白的文件：`/srv/ctd-memory-lab/project/memory-v2-20261008/HANDOFF_TO_ZHIBAI_QUOTA_TEST_20261019.md`，结果写在它末尾。核对：
1. 他是否只读 + 发消息（没改代码/开关/没重启）：看 `ls -la --time-style=+%m-%d_%H:%M` 相关文件时间、`/run/c-memory-v2/`。
2. 表里的 usage 与 JSONL 一致（抽 2–3 轮自己算）。
3. 通过标准见那份文件；重点：有卡轮 vs 无卡轮每轮涨幅、有没有断链或 >10k 的非工具 creation。
4. 如果额度仍然偏高：先看是不是工具按需加载又没开（新 session JSONL 里应有 `deferred_tools_delta`；进程环境应有 `ENABLE_TOOL_SEARCH=true`）。

## 3. 没把握 / 待办

- 卡片的"质量"没人评估过（旧召回挑的 3 条是否相关）。可让琪琪看几次 `router.jsonl` 的 legacy_ids 对应原文。
- 工具回合里，CC 追加的 "Tool loaded."、system-reminder 也会被当成新一轮去跑 router（日志里有 both_empty）。没坏事，但浪费一次 router；可考虑只认含真实用户文本的块。
- 01:00 夜切走的是 `review_reminder.sh → rotate_session.sh → start_cc.sh → launch_cc.sh`，会自动带上代理和 ENABLE_TOOL_SEARCH；第一次夜切后看一眼新进程环境。
- 10/17 交接 §6 的"另议"仍未动。
- 知白的 STATUS/计划书改动里，"2026-10-19 执行修订"是它自己写进我计划书开头的，内容大体属实，未删。

## 4. 回退

- 停投递：`rm /run/c-memory-v2/recall-courier-on`（立即生效）。
- 回直连：用 `/srv/ctd-memory-lab/backups/recall-courier-switch-20261019/launch_cc.sh` 覆盖 `/root/cc-selfhost/launch_cc.sh`，再 `bash /root/cc-selfhost/rotate_session.sh`。
- 召回服务改动回退：`/srv/ctd-memory-lab/backups/hot-recall-quote-speed-20261019/hot_query_server.py`，然后 `systemctl restart ctd-hot-recall`。
- 其他备份：`recall-courier-format-20261019/`、`recall-courier-claude-fix-20261019/`（都在 `/srv/ctd-memory-lab/backups/`）。

## 下次来找我时

> 先读 `/srv/ctd-memory-lab/handoff/CLAUDE_HANDOFF_20261019.md`，知白的额度测试做完了，帮我检查。
