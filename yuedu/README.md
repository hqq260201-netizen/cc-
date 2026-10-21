# 月渡

程亭渡的记忆库前端。整套意象来自名字本身：**亭**边的**渡**口，夜里有月。

开屏是一轮当天真实月相的月亮从江面升起；首页背后是青绿山水和一条带灯的小船（书童）。内容本身尽量不用比喻，一眼能看懂。

配色取自青绿山水的矿物颜料：黛、石青、石绿、泥金、朱砂。默认是夜色，系统浅色模式下切换成晨渡。

```
yuedu/
  server.py          只读后端（Python 3.11 标准库，没有依赖）
  static/index.html  整个前端是一个文件；没接后端时自动显示示例数据
  static/icon.svg    图标：一弯月，三层水（日 / 周 / 月），船头一盏灯
```

## 页面结构

首页是八个大方块，每块一个图标、一个名字、一个数字。点进去是一列短标题，再点一条，从下往上弹出全文。手机优先，字号跟随系统字体大小。

| 方块 | 是什么 | 数据从哪来 |
|---|---|---|
| 今天 | 今天的聊天整理成的几件事，每件都能「看当时的聊天」 | 书童 `output/<日期>/events.json`，原话靠 `slices.json` 加原文账本还原 |
| 日记 | 每天一篇，加上每周、每月的小结 | `summary.md`、`brief.md`、`weeks/*.md`、`months/*.md` |
| 珍藏 | 置顶、永久、重要的记忆 | C-Memory V2 的 `memory` + `memory_flag`（只读），过滤 `tombstone` 和 `dont_surface` |
| 他的感受 | 他自己写的心情 | `calendar/…/2-raw.jsonl` |
| 他眼中的你 | 他看到的你，和你纠正他的地方 | `calendar/…/3-raw.jsonl`、`4-raw.jsonl` |
| 约定 | 约定、待办、想做（没完成的排前面） | `plans-20260926/state/plans.json` |
| 碎碎念 | 两个人随手留的话 | `murmurs-20260926/data/murmurs.json` |
| 全部记忆 | Ombre 记忆桶，最近想起的在前，越久没想起越淡 | `ombre-shadow-real-20260910-a1/dynamic/**/*.md` |

首页上方还有一条「他今早醒来先看的纸条」，内容来自交接便签 `layered-dream-20261021/live/output/<日期>/*.md`。

## 接口

都是 GET、只读，需要先登录。

- `/api/home`：每个分类的数量和纸条
- `/api/list?cat=today|diary|stars|feel|eye|plans|murmur|all&q=关键词`：统一返回 `{id, title, date, time?, tag?, body, quote?, refs?}`
- `/api/day?date=YYYY-MM-DD`：某一天的日记和事件
- `/api/trace?refs=6.10.20.1,6.10.20.2`：当时的聊天原话

登录用 `POST /api/login {"password": …}`，口令和书房共用（默认读 `ui-shadow/.ui-key`）。登录后发一个 HMAC 签名的 HttpOnly Secure cookie，30 天有效。所有路径都能用环境变量覆盖，见 `server.py` 开头的注释。

## 部署（尚未部署）

```ini
# /etc/systemd/system/yuedu.service
[Unit]
Description=月渡 memory library (read-only)
After=network.target

[Service]
ExecStart=/usr/bin/python3.11 /srv/ctd-memory-lab/project/yuedu/server.py
Environment=YUEDU_PORT=18048
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

然后参照书房那条独立 tunnel，在 cloudflared 里加一条 ingress，把某个子域名指到 `http://127.0.0.1:18048`。

## 已知的缺口

- 书童余额还没接上，它在 Croft 的 `/api/bookboy` 里。
- 那 10 条星标提名在库里被标成了 `dont_surface`，按规则不显示。
