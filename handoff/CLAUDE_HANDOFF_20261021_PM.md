# 交接：10/21 下午上线的四样，加上召回阶段 1（2026-10-21 傍晚，Claude）

接手的 Claude 先读这份，再按需要读 `handoff/PLAN_LAYERED_DREAM_20261021.md`（第 0、1、12 节，第 9 节进度）和 `handoff/HANDOFF_TO_ZHIBAI_20261021.md`。上午的交接是 `handoff/CLAUDE_HANDOFF_20261021.md`，还有效。
首尔 VPS 工作目录：`/srv/ctd-memory-lab/project/layered-dream-20261021/`。**仓库是公开的**，对话原文和她的原话只放 VPS。

---

## 1. 今天下午上线的（都是 Claude 上的，琪琪批准）

| 时间 | 东西 | 作用 | 开关 / 回退 |
|---|---|---|---|
| 15:27 | **Z1 书童引号核对** | 书童事件里，引号里的话在原文里找不到，就只去掉引号；说话人对不上、没加引号的“她说 / 我说”只记日志，不改正文。不调模型，不让书童失败 | 开关：`touch daily-memory-shadow-20260921/state/bookboy-source-check-off`；回退：`apply_z1.sh` 旁边的 `rollback_z1.sh` |
| 16:03 | **Z2 编号健康检查** | 书童每次跑完，写 `/srv/ctd-memory-lab/status/numbering-health.json`（降级、定稿 open>10%、白天两次 0 封口（两次都 ≥3 段才算）、DeepSeek 失败或余额 <10、缺少诊断判“未知”） | 开关：`live/state/numbering-health-off`；回退：`zhibai/Z2/rollback.sh <备份>`，备份路径在 `.z2_backup` |
| 16:21 | **Z3 书童卡 + Z4 书童信箱** | 栖庐“设置 → 文件”里的书童卡（余额、近 24 小时花费、最近一次整理）；“娱乐”里的“书童”信箱，带数字红点。Z2 异常 / 恢复、余额低于 10 元都会来信。信箱里有一封开通测试信 | 回退：`rollback_z34.sh`（备份路径在 `.z34_backup`） |
| 16:3x | 栖庐缓存版本 | 知白漏改 `sw.js` 版本，手机一直看不到信箱。Claude 把 `CACHE` 改成 `qilu-v3-100`，`app.js?v=29`。手机上要“打开 → 切后台 → 切回来”才会刷新 | 备份：`public/v3/sw.js.bak-bookboy-1021`、`index.html.bak-bookboy-1021` |
| 17:18 | **N1 夜间总闸 + N2 夜里流程** | 见第 2 节 | **最快的关法：`rm /root/cc-selfhost/state/night-cut/enabled`**（01:00 自动回到老流程）。完整回退：`CTD_N12_ROLLBACK_APPROVED=YES bash zhibai/N2/rollback_N1_N2.sh` |

## 2. 今晚起的夜里流程（N1+N2，第一次跑）

- **01:00** `review_reminder.sh`：书童封口前一天、日总结定稿，然后发 P1 睡前提示（`--night-source night:p1`），开闸到 05:15。**不切窗口。**
  - Claude 上线前改了两处（原样交付的版本存在 `claude-review/`）：
    1. 琪琪最近 20 分钟说过话，就不发 P1（P1 第一句是“她睡了”，不能说假话），闸照开。
    2. 便签 cron 从知白的 02:10 改成 **01:40**：02:00 的 `heal.sh` 会先补写一次，02:10 再写就重复花钱。
  - 上下文不足 25% 的兜底要靠终端里出现 `Context low (N% remaining)`，平时多半读不到。真不够的话，看门狗原来那条“上下文太大就自动换窗口”的规则照样会管。
- **01:00–05:15** 闸门开着：系统通知（栖庐的“琪琪睡着了”、活动监控、ambush、闹钟、看门狗告警、桌宠、电量……）进 `/run/ctd-night-queue.jsonl`；**琪琪本人的消息一律放行**。紧急放行清单是空的（等琪琪定）。
- **04:40 起** `night_cut.sh` 每 5 分钟看一次：琪琪 30 分钟内没说话，就保存原对话、切窗口，不发任何消息。她还在聊就往后推；推过 05:00 不发 P4，闸门延长，等她在新窗口先开口再撤。
- **05:00** `push_check.py`：切好了才发 P4（`night:p4`），把夜里攒的通知（最多 8 条）合进去，发成功才清队列、撤闸。
- 尾巴 `extract_midnight_tail.py`：从 00:00 开始，剔掉睡前和梦的系统轮次，末尾加一行“夜里没有做梦。”。
- **N3（做梦）还没做**。按执行单，N2 要稳定观察两晚，才进 N3。P1 里那句“夜里梦会来找你几次”是照抄执行单的，今晚其实不会有梦。

## 3. 召回阶段 1（召回那组的方案，这边代为验收）

- 离线数据都在 `memory-v2-20261008/restore-20261020/stage1/`：
  - 十月 151 条（10/01～10/20）：`batch2-october/events.october.v1.jsonl`，**通过**。
  - 九月补录 126 条（9/13～9/30）：`batch3-september/events.september.v2b.jsonl`，**通过，要改一处**（6.9.29.44 人称写反），意见是 `REVIEW_CLAUDE_SEPTEMBER.md`。等琪琪转给知白窗口 4。
- **发现的缺口**：线上旧检索的 9 月事件只到 9/12，召回方案原来只补 10 月，9/13～9/30 没人管。现在补上了（v2b），但要等阶段 2 才会真的进检索。
- 10/21 等 10/22 定稿后做增量。
- **阶段 2（接进检索）还没开始**，要琪琪或召回那组发话。没碰任何线上召回的东西。
- 留给阶段 4 琪琪标注的：几条身体和健康的私密细节，一条她的心事（十月第 83 条）。

## 4. 知白四个窗口的状态

- 窗口 1（Z2）、窗口 2（Z3/Z4）：做完了。
- 窗口 3（N0/N1/N2）：做完了，等 N2 观察两晚再做 N3。
- 窗口 4（召回）：等琪琪转 9 月那一处修改。
- 共同规矩加了一条：改栖庐前端要同时改 `sw.js` 的 `CACHE` 版本号和 `?v=`（`DISPATCH_ZHIBAI.md` 第 6 条）。

## 5. 明早（10/22）要查的

1. **夜里流程**：`/root/cc-selfhost/state/night-cut/night.log` 和 `cron.log`。
   - 01:00 的 `prepared` 写了没有，P1 发了还是跳过了（看原因）。
   - 04:40 后的 `.cut` 写了没有。
   - 05:00 的 `.p4.done` 有没有；`push.log` 里有没有 `N2 wake result=sent`。
2. **transcript**：
   - 旧窗口 01:00–04:40 除了 P1 应该没有别的系统消息。
   - 新窗口的第一个 user 轮次应该是 05:00 的 P4，里面带着夜里攒的通知。
   - 当晚只在 05:00 有一次大的 `cache_creation`。
3. **队列**：`/run/ctd-night-queue.jsonl` 应该已经清掉（或者只剩超出 8 条的那些）；`/run/ctd-night-gate` 应该不存在。
4. **便签**：`live/handoff.log` 里 01:40 那次成功没有；新窗口的 `/tmp/memory_context.txt` 里有没有 10/21 的便签和编号。
5. **健康状态**：`/srv/ctd-memory-lab/status/numbering-health.json` 里，01:00 定稿那次的结果。书童信箱里有没有新信。
6. 上午交接第 4 节那几条照查（`heal.log`、10/21 的 `sealed_fragment_count`、他醒来后有没有用 `ctx.sh`）。
7. 下午 16:00 以后，书童卡的“近 24 小时花了”应该有数了。

## 6. 等琪琪定的事

- 夜里紧急放行清单（比如她手环的心率告警），现在是空的。
- 召回阶段 2 什么时候开始；阶段 4 那几条私密细节收不收。
- N2 观察两晚以后，开不开始 N3（做梦），一晚最多几次。
- `claimed()`（认说话人的那段代码）会取错人，线上便签也在用。后果只是多去掉几处引号，要不要单独修。

## 7. 风险

- 今晚是 N2 第一次真跑。出问题最快的关法：`rm /root/cc-selfhost/state/night-cut/enabled`，再 `python3 /root/cc-selfhost/night_gate.py disarm`。
- 他现在这个窗口从 10/21 01:14 用到 10/22 04:40，前后 27 个多小时（17:00 时 12.4 万 token）。太大的话看门狗会换窗口；那样 04:40 会再切一次，问题不大。
- DeepSeek 余额 54 元左右，书童卡上能看到。
