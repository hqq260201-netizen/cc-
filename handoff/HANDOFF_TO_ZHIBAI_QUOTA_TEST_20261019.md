# 给知白：程亭渡单独额度测试（Claude 写，2026-10-19）

## 背景（一句话）
10/19 上午记忆投递已上线（线级快递员，阅后即焚），缓存链实测连续。但当时 Claude 和程亭渡共用同一账号额度，5 小时额度的涨幅分不清是谁用的。这次测试只看程亭渡自己。
现状详见 `STATUS.md` 顶部"2026-10-19 11:15 已上线"。

## 前提
- 开测前确认 Claude 不在工作（问琪琪）。测试期间账号上只有程亭渡在用。
- **只读 + 发消息**：不改代码、不改开关、不重启程亭渡、不动缓存相关的任何东西。发现异常就停，记下来，交给琪琪/Claude。

## 怎么测
1. 每轮前后各读一次状态栏额度：`tmux capture-pane -pt cc | grep 'Claude 5h'`（取 5h 百分比）。
2. 跑约 10 轮，两类都要有：
   - **无卡轮**：自然的 `[系统]` 报时消息即可，不用你发。
   - **有卡轮**：在终端发 5 个问旧事的问题，开头写明"我是知白"（他认你）。例如"还记得…吗"类问题，主题从书房里挑，别挑冷启动里已有的。**不要用【群聊】格式**——群聊消息按设计不递卡。
   - 发消息：`tmux send-keys -t cc -l '内容'; tmux send-keys -t cc Enter`，等他答完再发下一条。
3. 每轮记一行：时间｜有卡/无卡｜5h% 前→后｜cache_read｜cache_creation｜input｜output｜有无工具调用。
   - usage 取当前 session JSONL（`ls -t /root/.claude/projects/-root-cc-selfhost/*.jsonl | head -1`），按 message.id 去重。
   - 有没有卡看 `logs/recall-courier.jsonl` 里同一时间的 `injected`。

## 通过标准
- 每轮 `cache_read` = 上一轮 `read + creation`（不断链）；
- 有卡轮的 creation 与无卡轮同量级（差几百 token 以内）；卡片本身算在 input 里，几百 token；
- 除工具结果外，没有单次 >10k 的 creation；
- JSONL 里搜不到卡片正文（`grep -c '新书房·自动召回' <jsonl>` 应为 0）；
- 额度：给出无卡轮、有卡轮各自平均每轮涨多少 %。参考：10/19 实测一轮有卡对话约 read 8 万 / creation 0.2k / input 0.5k / output 0.6k。

## 结果写哪
写在本文件末尾，一张表 + 一句结论（能不能放心）。不要新开文件、不要改 PLAN.md。

## 紧急回退
`rm /run/c-memory-v2/recall-courier-on`（立即停止递卡，不用重启）。
