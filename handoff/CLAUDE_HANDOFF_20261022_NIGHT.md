# 交接：N2b 上线、书童一行、Croft 随机开屏、Clawd 衣橱（2026-10-21 夜 → 10-22 凌晨，Claude）

接手的 Claude 先读这份，再读 `handoff/CLAUDE_HANDOFF_20261021.md`（上午）和 VPS 上的 `CLAUDE_HANDOFF_20261021_PM.md`（下午，只在 VPS，没推仓库）。
首尔 VPS 工作目录：`/srv/ctd-memory-lab/project/layered-dream-20261021/`。**仓库是公开的**，对话原文和她的原话只放 VPS。

---

## 1. 夜里的流程：N2b 已上线（10/21 23:15）

**琪琪定的**：04:40 切窗口也走 Forge，但 Forge 只带她和程亭渡的聊天，不带他做的梦。梦更私密，他醒来接着的是清楚的聊天原话，梦都在他自己写的梦本里。另外她还定了两条：
- Forge 往前数 1 万 token，可能数回前一天晚上的聊天，和便签有重叠。她说可以，就要这样。
- 05:00 的 P4 里提一句做过几个梦、写在哪里，不带梦的内容。

**流程**：Claude 写执行单 `handoff/HANDOFF_TO_ZHIBAI_N2B_20261021.md`（VPS 上是 `HANDOFF_TO_ZHIBAI_N2B.md`）→ 知白做（`zhibai/N2B/`）→ Claude 验收（`zhibai/N2B/REVIEW_CLAUDE_N2B.md`）→ 琪琪事先同意“验收后上线”，Claude 执行 `install_N2B.sh`。

**改了三处**（备份在 `zhibai/N2B/deploy-backup-20261021-231525/`）：
1. `forge_build.py`：在 1 万 token 预算计算**之前**跳过夜间段。段从正文以 `[睡前·` 或 `[梦·` 开头的 user 轮开始（会先去掉 `[栖庐…]` 前缀），到下一条真人轮之前结束；段里他的回复、工具调用和对应的 tool_result 都丢掉。她半夜醒来说的话都留下。白天不会出现这两种前缀，所以白天切窗口不受影响。
2. `night_cut.sh`：有 `state/night-cut/night-forge-on` 时不再带 `FORGE_DISABLE=1`。
3. `night_flow.py` 的 `wake_text()`：那一夜有 `dream_saved` 时，加一句“你夜里做了 N 个梦，写在 dreams/日期.md，想看就去看。”

**验收时核实过**：
- tmux 投递的 `[睡前·]` 在 transcript 里确实是 `origin.kind=human`，所以只能按正文开头认，这个办法是对的。
- 拿线上真实 transcript 试跑：跳过 1 段 9 条，链连续，tool_use 和 tool_result 没有落单，省下的预算多带了 31 条真实聊天。
- 知白的 13 项测试在 VPS 上重跑全部通过。

**开关**：
- 快关：`rm /root/cc-selfhost/state/night-cut/night-forge-on`，04:40 回到文字尾巴。
- 只关 Forge 的过滤：`touch /root/cc-selfhost/state/night-cut/forge-night-filter-off`。
- 完整回退：`CTD_N2B_ROLLBACK_APPROVED=YES bash zhibai/N2B/rollback_N2B.sh`，00:00–05:30 之间不能跑。

**今晚是 N2 + N3 + N2b 一起跑的第一晚。** N3（做梦）是 10/21 18:07 装的，下午的交接写的还是“N3 没做”，以 VPS 上的文件为准。

## 2. 要告诉知白的：N3 安装时误发了一条提示

10/21 18:03:55，程亭渡收到一条 `[睡前·00:00] …十二点了。要睡了吗？…`，当时是傍晚，他回了“不睡，先把今天的事记完”，还写了东西。看起来是 N3 安装时，按 `due=00:00`（已经过去的时间）直接发了 Q1。状态文件 `state/night-cut/dream-2026-10-21.json` 停在 `await_q1`。
- 今晚换了日期会重新初始化，应该不会再错，但要请知白查一下原因。
- N2b 上线后，这条话以后切窗口时会被 Forge 跳过，不会再带进新窗口。

## 3. 栖庐 / Croft 的设置页：书童改成一行（10/21 23:3x）

琪琪要的：书童只要一句话，放在“额度”下面。
- 现在：设置 → 文件 → 额度里多一行“书童　还剩 X 元”，低于 10 元变红。原来单独的那一块（近 24 小时花费、最近一次整理）去掉了，失败照旧会进书童信箱。
- 文件：`/opt/croft/public/v3/js/bookboy-card.js`、`panels.js`、`settings.js`。
- 回退：同目录下 5 个 `*.bak-bookboy-oneline-1021`。

## 4. Croft 开屏：每次打开随机一个（10/22 01:0x 上线）

**注意：栖庐和 Croft 现在是两个 App。** 这是 Croft（`/opt/croft/public/v3/`）的开屏，字只写 Croft，副标是当天日期。

**18 个开屏**：一盏灯、推门（单扇门，加载好以后走进门里）、月升、墨晕、星河（星点聚成字形）、落花、鎏金、蜡笔小屋、Clawd、啄羊鹦鹉（灰头绿身，蹦上屋顶）、炊烟小屋、Clawd 睡醒、保险柜（科普插图式的机械线稿：齿轮咬合、锁栓退回、标注线，开门后推进去）、日升月落、涨潮（加载好以后一个浪头盖满整屏）、打字机、霓虹灯、拆信。
- 随机，不和上一次重复（记在 `localStorage.splash_last`）。
- 新版接管后的那次静默刷新（`still`）会重放上一个，动画直接到最后一帧。
- 开屏至少停 2.4 秒（原来是 2.1 秒），让动画放完。
- 推门和保险柜里的光，琪琪说太黄，已经调成淡杏色（`--soft`）。

**文件**：
- 源头是预览页 `croft-splash/splash-preview.html`，线上在 `https://cc-direct.chengtingdu.top/v3/splash-preview.html`，可以挨个看、随机看、切深色。
- `croft-splash/build_croft.py` 从预览页生成 `css/splash-set.css` 和 `js/splash-set.js`。它会把所有样式限定在 `.splash.stage` 里，给 `@keyframes` 加 `sx-` 前缀；和 Croft 撞名的类（bubble、scene、seal、in、ink）在预览页里已经改成 `sx-` 开头。**要改开屏，先改预览页，再跑脚本，别直接改生成的文件。**
- 接入点：`js/app.js` 的 `showSplash()` 调 `mountSplash()`，`watchSplash()` 监听 `.out`，以便触发结尾动画。`index.html` 加了 `splash-set.css?v=1`，`app.js?v=31`。`sw.js` 的 `CACHE` 改成 `qilu-v3-102`，CORE 里加了这两个文件。
- 备份：`index.html`、`js/app.js`、`sw.js`、`splash-preview.html` 各有一份 `.bak-splash-random-1022`。回退就是把这四个换回去，再删掉两个 `splash-set` 文件，并把 `CACHE` 再加 1。
- 验证：用 VPS 上的 headless chromium（`~/.cache/ms-playwright/chromium_headless_shell-1243/`，配 `/root/fable-worker-0719K/testground/node_modules/playwright-core`）打开 `http://127.0.0.1:3001/v3/`，开屏正常挂上，没有脚本报错（没登录，只有 401）。**还没在她手机上看过真机效果。**

## 5. Clawd 衣橱（像素 GIF）

琪琪很喜欢 Clawd，要多多的各种衣服、动作、表情。
- 生成器：`clawd-gifs/make_clawd.py`。Clawd 照 Croft 的 `clawd-static-base.svg` 的 15×16 像素格画。一张 GIF = 场景 + 衣服 + 动作/道具 + 表情，每层都能换；加一套衣服或一个动作，所有组合都能用。底部的 `LIST` 是精选组合。
- 现有 68 张：11 套衣服（女仆装、小裙子、巫师、研究员、工人、医生、睡衣、王子服、厨师、围巾、水手服），21 种动作（喝茶、扒窗台看雪/雨/晴天/夜里、听歌、买菜、举伞、捧小碗……），12 种表情（开心、难过、生气、哭哭、别扭、平静……）。
- 图库页：`https://cc-direct.chengtingdu.top/pet-assets/clawd-gifs/index.html`，可以按衣服、动作、表情筛。VPS 上的文件在 `/opt/croft/public/pet-assets/clawd-gifs/`，仓库里在 `clawd-gifs/gifs/`。压缩包已经发给琪琪。
- 她可能会接着点：某套衣服配某个动作、新衣服（汉服、毛衣、兔耳朵……）、新动作。改 `make_clawd.py`，跑 `python3 make_clawd.py gifs`，再同步到 VPS。

## 6. 明早（10/22）要查的

1. **N2b**：
   - `/root/cc-selfhost/watchdog.log` 里 04:40 以后那次切窗口有 `FORGE 续接就绪`，不是 `FORGE-FALLBACK`；stderr 里有 `夜间段跳过: 段数=N 条目=M`。
   - 新窗口的 transcript（Forge 生成的那份和接上以后的）里搜不到 `[睡前·`、`[梦·`，也搜不到 `dreams/2026-10-22.md` 里梦的句子。
   - 05:00 的 P4 是接上以后的第一条新 user 轮，当晚做了梦的话，里面有那句梦的提示。
   - `/tmp/memory_context.txt` 里没有 ④ 文字尾巴（`SKIP_TAIL=1`），但有便签。
2. **N3**：`state/night-cut/dream.log` 里夜里的问答和 `dream_saved`；`dreams/2026-10-22.md` 在不在。**只看他做了什么，不看他怎么说。**
3. 上午和下午交接里的明早检查项照查（便签 01:40、`heal.log`、编号健康、书童信箱）。
4. 问琪琪：Croft 的随机开屏在手机上效果怎么样，有没有哪个要删要改。

## 7. 工作方式上的备忘

- 这个容器连不到 `cc-direct.chengtingdu.top`（代理拒绝）。往 VPS 送文件要先推到仓库分支，再让 VPS `curl raw.githubusercontent.com/...`，最后核对 sha256。直接贴 base64 大文件容易抄错，试过一次，gzip 解不开。
- 和琪琪说话要用大白话。她说过“我没看懂你在说什么”，之后改成短句、少术语，效果好很多。
