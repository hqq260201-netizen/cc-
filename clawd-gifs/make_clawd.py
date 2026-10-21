#!/usr/bin/env python3
"""Clawd 像素 GIF 生成器。

Clawd 的身体照 Croft 里 clawd-static-base.svg 的 15x16 像素格画：
躯干 (2,6) 11x7，手 (0,9)/(13,9) 2x2，四条腿在 y=13..14，眼睛 (4,8)/(10,8) 1x2。
一张 GIF = 场景 + 衣服 + 动作/道具 + 表情，按层叠起来，每帧重画。

用法：python3 make_clawd.py out_dir
"""
import json
import math
import os
import random
import sys

from PIL import Image

W, H, S = 34, 30, 10         # 画布格数和放大倍数（340x300）
OX, OY = 10, 11              # Clawd 15x16 格左上角在画布上的位置
FL = OY + 16                 # 地面
FRAMES, MS = 12, 120

BODY = (222, 136, 109)
BODY_D = (196, 112, 88)
EYE = (20, 18, 18)
BLUSH = (242, 160, 168)
WHITE = (250, 248, 244)
INK = (42, 39, 34)


class Frame:
    def __init__(self, bg):
        self.im = Image.new("RGB", (W, H), bg)
        self.p = self.im.load()
        self.dy = 0

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H and c is not None:
            self.p[x, y] = c

    def rect(self, x, y, w, h, c):
        for i in range(w):
            for j in range(h):
                self.put(x + i, y + j, c)

    # 以 Clawd 自己的格子坐标作画（会跟着身体上下起伏）
    def c(self, x, y, c, bob=True):
        self.put(OX + x, OY + y + (self.dy if bob else 0), c)

    def cr(self, x, y, w, h, c, bob=True):
        for i in range(w):
            for j in range(h):
                self.c(x + i, y + j, c, bob)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------- 场景
def scene_room(f, t, rnd):
    f.rect(0, FL, W, H - FL, (228, 220, 203))
    f.rect(0, FL - 1, W, 1, (214, 205, 186))


def make_window(weather):
    def draw(f, t, rnd):
        wall = (239, 232, 220)
        f.rect(0, 0, W, H, wall)
        x0, y0, x1, y1 = 3, 1, W - 3, OY + 5
        sky = {"snow": (52, 70, 98), "rain": (92, 108, 122), "sun": (150, 205, 232), "night": (24, 32, 58)}[weather]
        f.rect(x0, y0, x1 - x0, y1 - y0, sky)
        if weather == "sun":
            f.rect(x1 - 9, 3, 4, 4, (255, 214, 102))
            for k, (dx, dy) in enumerate([(0, -2), (0, 6), (-2, 2), (6, 2)]):
                if (t + k) % 4 < 2:
                    f.rect(x1 - 8 + dx, 4 + dy, 1, 1, (255, 214, 102))
            cx = 10 + (t % 24)
            for (a, b, w) in [(0, 0, 6), (1, -1, 4), (2, 1, 5)]:
                f.rect(x0 + (cx + a) % (x1 - x0 - 4), 10 + b, w, 2, WHITE)
        if weather == "night":
            f.rect(x1 - 7, 3, 3, 3, (244, 241, 228))
            f.rect(x1 - 6, 3, 2, 2, sky)
            for (sx, sy) in [(6, 4), (11, 8), (17, 3), (8, 12), (21, 11), (26, 13)]:
                if (sx + t) % 5:
                    f.put(sx, sy, (240, 236, 210))
        for k in range(34):
            r = random.Random(k * 7 + 3)
            sx, sy, sp = r.randint(x0, x1 - 1), r.randint(0, 40), r.choice([1, 1, 2])
            if weather == "snow":
                y = y0 + (sy + t * sp // 1) % (y1 - y0)
                f.put(sx + (t // 3 + k) % 2, y, WHITE)
            elif weather == "rain":
                y = y0 + (sy + t * 3) % (y1 - y0)
                f.put(sx, y, (196, 214, 228))
                f.put(sx, y - 1, (160, 184, 204)) if y - 1 >= y0 else None
        f.rect((x0 + x1) // 2, y0, 1, y1 - y0, (140, 107, 82))
        f.rect(x0, (y0 + y1) // 2, x1 - x0, 1, (140, 107, 82))
        for (x, y, w, h) in [(x0 - 1, y0 - 1, x1 - x0 + 2, 1), (x0 - 1, y0, 1, y1 - y0), (x1, y0, 1, y1 - y0)]:
            f.rect(x, y, w, h, (120, 90, 68))
        f.rect(x0 - 3, y1, x1 - x0 + 6, 2, (160, 124, 96))
        f.rect(0, FL, W, H - FL, (214, 200, 178))
    return draw


def scene_rain(f, t, rnd):
    f.rect(0, 0, W, H, (196, 208, 214))
    f.rect(0, FL, W, H - FL, (150, 164, 170))
    for k in range(40):
        r = random.Random(k * 13 + 1)
        x, y0 = r.randint(0, W - 1), r.randint(0, 60)
        y = (y0 + t * 3) % H
        f.put(x, y, (120, 146, 170))
        f.put(x, y - 1, (150, 172, 190))
    for k in range(4):
        x = 4 + k * 11 + (t // 3) % 2
        f.rect(x, FL + 1, 3, 1, (130, 150, 160))


def scene_night(f, t, rnd):
    f.rect(0, 0, W, H, (30, 36, 64))
    for (x, y) in [(3, 3), (8, 8), (14, 2), (22, 6), (29, 10), (5, 13), (26, 15)]:
        if (x + y + t) % 6:
            f.put(x, y, (236, 230, 200))
    f.rect(W - 7, 2, 4, 4, (244, 238, 210))
    f.rect(W - 6, 2, 3, 3, (30, 36, 64))
    f.rect(0, FL, W, H - FL, (56, 60, 92))


def scene_soft(color):
    def draw(f, t, rnd):
        f.rect(0, 0, W, H, color)
        f.rect(0, FL, W, H - FL, mix(color, INK, .12))
    return draw


def scene_shop(f, t, rnd):
    f.rect(0, 0, W, H, (243, 236, 226))
    off = (t * 1) % 12
    for k in range(-1, 5):
        x = k * 12 - off
        f.rect(x, 3, 8, 12, (214, 196, 170))
        f.rect(x + 1, 5, 6, 4, (178, 214, 226))
        f.rect(x, 1, 8, 2, [(224, 122, 95), (127, 176, 105), (91, 141, 239), (233, 169, 59)][k % 4])
    f.rect(0, FL, W, H - FL, (200, 190, 176))
    for k in range(-1, 8):
        f.rect(k * 6 - off % 6, FL + 1, 3, 1, (180, 170, 156))


SCENES = {
    "room": scene_room, "snow": make_window("snow"), "rain_win": make_window("rain"), "sun_win": make_window("sun"),
    "night_win": make_window("night"), "rain": scene_rain, "night": scene_night, "shop": scene_shop,
    "pink": scene_soft((248, 228, 232)), "mint": scene_soft((226, 240, 232)), "sky": scene_soft((222, 236, 246)),
    "cream": scene_soft((243, 239, 231)), "lilac": scene_soft((236, 230, 246)), "peach": scene_soft((250, 232, 214)),
}
BG = {"room": (243, 239, 231)}


# ---------------------------------------------------------------- 衣服
def outfit(name):
    """返回 (behind, lower, upper, head) 四个画层。"""
    none = lambda f, t: None

    if name == "maid":
        def lower(f, t):
            f.cr(2, 11, 11, 2, (43, 43, 51)); f.cr(1, 13, 13, 1, (43, 43, 51))
            for x in range(1, 14, 2):
                f.c(x, 13, WHITE)
            f.cr(5, 10, 5, 3, WHITE); f.cr(6, 13, 3, 1, WHITE)
        def upper(f, t):
            f.cr(5, 6, 5, 1, WHITE); f.c(7, 7, (176, 60, 72))
        def head(f, t):
            for x in range(3, 12):
                f.c(x, 5, WHITE if x % 2 else (43, 43, 51))
            f.c(2, 5, (43, 43, 51)); f.c(12, 5, (43, 43, 51))
        return none, lower, upper, head

    if name == "dress":
        pink, dot = (244, 166, 192), WHITE
        def lower(f, t):
            f.cr(2, 11, 11, 2, pink); f.cr(1, 13, 13, 1, pink)
            for (x, y) in [(3, 11), (6, 12), (9, 11), (11, 12), (4, 13), (8, 13), (12, 13)]:
                f.c(x, y, dot)
        def head(f, t):
            for (x, y) in [(9, 4), (11, 4), (9, 5), (11, 5)]:
                f.c(x, y, (232, 92, 128))
            f.c(10, 5, (196, 60, 96))
        return none, lower, none, head

    if name == "wizard":
        robe, star = (75, 59, 143), (233, 196, 106)
        def behind(f, t):
            f.cr(1, 6, 13, 8, robe)
        def lower(f, t):
            f.cr(2, 11, 11, 2, robe); f.c(4, 12, star); f.c(10, 11, star)
        def head(f, t):
            f.cr(1, 5, 13, 1, robe)
            for y, (a, b) in zip(range(4, -1, -1), [(3, 11), (4, 10), (5, 10), (6, 9), (7, 9)]):
                f.cr(a, y, b - a + 1, 1, robe)
            f.cr(8, -1, 2, 1, robe); f.c(10, -1, robe)
            f.cr(3, 4, 9, 1, star)
            f.c(6, 2, star if t % 4 < 2 else robe); f.c(8, 1, star if t % 4 >= 2 else robe)
        return behind, lower, none, head

    if name == "lab":
        coat = (245, 245, 242)
        def upper(f, t):
            f.cr(2, 10, 3, 3, coat); f.cr(10, 10, 3, 3, coat); f.cr(2, 6, 2, 4, coat); f.cr(11, 6, 2, 4, coat)
            f.c(11, 11, (91, 141, 239)); f.c(11, 12, (91, 141, 239))
            g = (112, 132, 172)
            for (x, y) in [(3, 7), (4, 7), (5, 7), (3, 10), (4, 10), (5, 10), (3, 8), (3, 9), (5, 8), (5, 9),
                           (9, 7), (10, 7), (11, 7), (9, 10), (10, 10), (11, 10), (9, 8), (9, 9), (11, 8), (11, 9), (6, 8), (7, 8), (8, 8)]:
                f.c(x, y, g)
        return none, none, upper, none

    if name == "worker":
        blue, yel = (63, 111, 168), (242, 193, 78)
        def lower(f, t):
            f.cr(3, 10, 9, 3, blue); f.cr(4, 7, 1, 3, blue); f.cr(10, 7, 1, 3, blue)
            f.c(4, 10, yel); f.c(10, 10, yel); f.cr(6, 11, 3, 1, (48, 90, 140))
        def head(f, t):
            f.cr(4, 4, 7, 1, yel); f.cr(2, 5, 11, 1, yel); f.cr(5, 3, 5, 1, yel); f.c(7, 3, (220, 170, 60))
        return none, lower, none, head

    if name == "doctor":
        coat = (245, 245, 242)
        def upper(f, t):
            f.cr(2, 10, 11, 3, coat); f.cr(2, 6, 2, 4, coat); f.cr(11, 6, 2, 4, coat)
            st = (124, 132, 140)
            for (x, y) in [(4, 6), (4, 7), (4, 8), (4, 9), (5, 10), (6, 10), (10, 6), (10, 7), (10, 8), (10, 9), (9, 10), (8, 10)]:
                f.c(x, y, st)
            f.cr(7, 11, 1, 1, (200, 206, 212))
        def head(f, t):
            f.cr(4, 4, 7, 2, coat); f.c(7, 4, (214, 60, 60)); f.cr(6, 5, 3, 1, coat); f.c(7, 5, (214, 60, 60))
            f.c(6, 4, coat); f.c(8, 4, coat)
            f.cr(6, 4, 3, 1, coat); f.c(7, 4, (214, 60, 60))
            f.c(7, 3, (214, 60, 60)) if False else None
        return none, none, upper, head

    if name == "pajama":
        pj, st = (169, 200, 234), (232, 242, 252)
        def lower(f, t):
            f.cr(2, 10, 11, 3, pj)
            for x in range(3, 13, 3):
                f.cr(x, 10, 1, 3, st)
            f.c(7, 10, (240, 200, 90))
        def head(f, t):
            f.cr(2, 5, 11, 1, pj); f.cr(4, 4, 8, 1, pj); f.cr(8, 3, 5, 1, pj); f.cr(12, 4, 2, 1, pj)
            f.c(14, 5, WHITE); f.c(14, 6, WHITE) if t % 6 < 3 else f.c(15, 5, WHITE)
            for x in range(2, 13, 2):
                f.c(x, 5, st)
        return none, lower, none, head

    if name == "prince":
        navy, gold, red = (47, 62, 117), (233, 196, 106), (178, 58, 72)
        def behind(f, t):
            f.cr(1, 7, 13, 7, red)
        def lower(f, t):
            f.cr(2, 10, 11, 3, navy)
            for y in (10, 11, 12):
                f.c(7, y, gold)
            f.c(2, 9, gold); f.c(12, 9, gold)
        def upper(f, t):
            for i, (x, y) in enumerate([(3, 10), (4, 11), (5, 12)]):
                f.c(x, y, red)
        def head(f, t):
            f.cr(4, 5, 7, 1, gold); f.c(4, 4, gold); f.c(7, 4, gold); f.c(10, 4, gold); f.c(7, 3, gold)
            f.c(7, 5, red); f.c(5, 5, (91, 141, 239)); f.c(9, 5, (91, 141, 239))
            if t % 6 == 0:
                f.c(11, 2, WHITE)
        return behind, lower, upper, head

    if name == "chef":
        def lower(f, t):
            f.cr(4, 10, 7, 3, WHITE); f.cr(5, 13, 5, 1, WHITE)
        def head(f, t):
            f.cr(4, 5, 7, 1, WHITE); f.cr(3, 2, 9, 3, WHITE); f.cr(4, 1, 3, 1, WHITE); f.cr(8, 1, 3, 1, WHITE)
            f.cr(4, 4, 7, 1, (232, 226, 216))
        return none, lower, none, head

    if name == "scarf":
        red = (196, 72, 64)
        def upper(f, t):
            f.cr(2, 6, 11, 2, red)
            f.cr(10, 8, 2, 3, red); f.c(10, 11, (230, 220, 210)); f.c(11, 11, (230, 220, 210))
            for x in range(3, 13, 3):
                f.c(x, 6, (230, 220, 210))
        def head(f, t):
            f.cr(3, 5, 9, 1, (91, 120, 170)); f.cr(5, 4, 5, 1, (91, 120, 170)); f.cr(6, 3, 3, 1, WHITE)
        return none, none, upper, head

    if name == "sailor":
        nav = (40, 64, 120)
        def upper(f, t):
            f.cr(2, 6, 11, 1, nav); f.cr(2, 7, 3, 1, nav); f.cr(10, 7, 3, 1, nav)
            f.c(6, 7, (214, 60, 60)); f.c(7, 7, (214, 60, 60)); f.c(8, 7, (214, 60, 60)); f.c(7, 8, (214, 60, 60))
        def lower(f, t):
            f.cr(2, 11, 11, 2, nav); f.cr(1, 13, 13, 1, nav)
            for x in range(2, 13, 2):
                f.c(x, 12, WHITE)
        return none, lower, upper, none

    return none, none, none, none


OUTFIT_NAMES = {"none": "原样", "maid": "女仆装", "dress": "小裙子", "wizard": "帅气巫师", "lab": "研究员", "worker": "工人",
                "doctor": "医生", "pajama": "睡衣", "prince": "王子服", "chef": "厨师", "scarf": "冬天围巾", "sailor": "水手服"}


# ---------------------------------------------------------------- 表情
def face(f, t, kind):
    blink = t % FRAMES in (7,)
    if kind in ("normal", "think", "look_up"):
        dy = -1 if kind == "look_up" else 0
        if blink:
            f.c(4, 9, EYE); f.c(10, 9, EYE)
        else:
            f.cr(4, 8 + dy, 1, 2, EYE); f.cr(10, 8 + dy, 1, 2, EYE)
    elif kind == "happy":
        for (x, y) in [(3, 9), (4, 8), (5, 9), (9, 9), (10, 8), (11, 9)]:
            f.c(x, y, EYE)
        f.cr(2, 10, 2, 1, BLUSH); f.cr(11, 10, 2, 1, BLUSH)
    elif kind == "calm":
        f.cr(3, 9, 2, 1, EYE); f.cr(10, 9, 2, 1, EYE)
        f.cr(2, 10, 1, 1, BLUSH); f.cr(12, 10, 1, 1, BLUSH)
    elif kind == "sad":
        f.c(4, 9, EYE); f.c(10, 9, EYE); f.c(3, 8, EYE); f.c(11, 8, EYE)
        f.c(6, 11, EYE); f.c(7, 10, EYE); f.c(8, 11, EYE)
    elif kind == "cry":
        f.cr(3, 9, 2, 1, EYE); f.cr(10, 9, 2, 1, EYE)
        tear = (120, 180, 232)
        for k in range(3):
            y = 10 + (t + k * 2) % 4
            f.c(3 + (k % 2), y, tear); f.c(11 - (k % 2), y, tear)
        if t % 2:
            f.c(7, 11, EYE); f.c(6, 11, EYE)
        else:
            f.c(7, 11, EYE); f.c(8, 11, EYE)
    elif kind == "angry":
        f.c(4, 9, EYE); f.c(10, 9, EYE); f.c(3, 7, EYE); f.c(4, 8, EYE); f.c(11, 7, EYE); f.c(10, 8, EYE)
        f.cr(6, 11, 3, 1, EYE)
    elif kind == "sulky":   # 别扭：眼睛瞥到一边、脸红、冒一滴汗
        f.cr(5, 8, 1, 2, EYE); f.cr(11, 8, 1, 2, EYE)
        f.cr(2, 10, 2, 1, BLUSH); f.cr(9, 10, 2, 1, BLUSH)
        f.cr(7, 11, 2, 1, EYE)
    elif kind == "surprise":
        f.cr(4, 8, 1, 2, EYE); f.cr(10, 8, 1, 2, EYE); f.cr(7, 10, 1, 2, EYE)
    elif kind == "love":
        pk = (232, 70, 110)
        for (ex) in (4, 10):
            f.c(ex - 1, 8, pk); f.c(ex + 1, 8, pk); f.cr(ex - 1, 9, 3, 1, pk); f.c(ex, 10, pk)
        f.cr(2, 11, 2, 1, BLUSH); f.cr(11, 11, 2, 1, BLUSH)
    elif kind == "sleep":
        f.cr(3, 9, 2, 1, EYE); f.cr(10, 9, 2, 1, EYE)


def effects(f, t, kind):
    if kind == "angry":
        r = (214, 60, 60)
        if t % 4 < 3:
            for (x, y) in [(13, 3), (15, 3), (14, 4), (13, 5), (15, 5)]:
                f.c(x, y, r)
        if t % 3 == 0:
            f.c(-1, 4, (200, 200, 200)); f.c(-2, 3, (220, 220, 220))
    elif kind == "sulky":
        f.c(13, 5 + (t // 4) % 2, (130, 190, 236)); f.c(13, 4 + (t // 4) % 2, (180, 220, 246))
    elif kind == "love":
        for k in range(2):
            y = 4 - (t + k * 6) % 12 // 2
            x = 13 + k * 2
            pk = (232, 92, 128)
            f.c(x, y, pk); f.c(x + 2, y, pk); f.cr(x, y + 1, 3, 1, pk); f.c(x + 1, y + 2, pk)
    elif kind == "happy":
        if t % 4 < 2:
            f.c(-1, 5, (255, 214, 102)); f.c(15, 3, (255, 214, 102))
        else:
            f.c(-2, 3, (255, 214, 102)); f.c(16, 5, (255, 214, 102))
    elif kind == "sleep":
        z = (110, 120, 160)
        for k in range(2):
            ph = (t + k * 6) % 12
            x, y = 14 + ph // 3, 4 - ph // 2
            f.cr(x, y, 3, 1, z); f.c(x + 1, y + 1, z); f.cr(x, y + 2, 3, 1, z)
    elif kind == "think":
        dots = (t // 3) % 4
        for k in range(dots):
            f.c(13 + k * 2, 3, INK)
    elif kind == "sad":
        cl = (150, 160, 176)
        f.cr(2, -1, 11, 2, cl); f.cr(4, -2, 7, 1, cl)
        for k in range(4):
            f.c(3 + k * 3, 1 + (t + k) % 3, (120, 160, 210))
    elif kind == "surprise":
        if t % 4 < 2:
            f.cr(14, 2, 1, 3, (214, 60, 60)); f.c(14, 6, (214, 60, 60))


FACE_NAMES = {"normal": "平静", "calm": "安心", "happy": "开心", "sad": "难过", "cry": "哭哭", "angry": "生气",
              "sulky": "别扭", "surprise": "吃惊", "love": "喜欢", "sleep": "困了", "think": "想事情", "look_up": "望着窗外"}


# ---------------------------------------------------------------- 动作和道具
def arm(f, side, pose):
    """side: 'l' or 'r'；pose: down / up / front / sill / hold"""
    if side == "l":
        spots = {"down": (0, 9, 2, 2), "up": (0, 5, 2, 2), "front": (1, 10, 2, 2), "sill": (1, 5, 2, 2), "hold": (0, 9, 2, 2)}
    else:
        spots = {"down": (13, 9, 2, 2), "up": (13, 5, 2, 2), "front": (12, 10, 2, 2), "sill": (12, 5, 2, 2), "hold": (13, 8, 2, 2)}
    x, y, w, h = spots[pose]
    f.cr(x, y, w, h, BODY)
    if pose == "up":
        f.cr(x + (1 if side == "l" else 0), y + 2, 1, 2, BODY)


def act(name):
    """返回 (arms(f,t)->None, prop_back, prop_front, bob(t)->dy)"""
    still = lambda t: 0
    breathe = lambda t: -1 if t % 6 in (3, 4) else 0
    bounce = lambda t: -1 if t % 4 in (1, 2) else 0
    nop = lambda f, t: None

    if name == "idle":
        return (lambda f, t: (arm(f, "l", "down"), arm(f, "r", "down")), nop, nop, breathe)
    if name == "wave":
        def arms(f, t):
            arm(f, "l", "down")
            arm(f, "r", "up" if t % 4 < 2 else "hold")
        return arms, nop, nop, bounce
    if name == "jump":
        return (lambda f, t: (arm(f, "l", "up" if t % 4 < 2 else "down"), arm(f, "r", "up" if t % 4 < 2 else "down")),
                nop, nop, lambda t: [-2, -3, -2, 0][t % 4])
    if name == "tea":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "hold")
        def front(f, t):
            sip = t % 12 >= 8
            x, y = (13, 6) if sip else (14, 7)
            f.cr(x, y, 3, 2, WHITE); f.c(x + 3, y, WHITE); f.cr(x, y + 2, 3, 1, (220, 212, 200))
            f.cr(x, y, 3, 1, (176, 120, 70))
            if not sip:
                for k in range(2):
                    sy = y - 1 - (t + k * 2) % 4
                    f.c(x + 1 + ((t // 2 + k) % 2), sy, (200, 196, 190))
        return arms, nop, front, breathe
    if name == "music":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "down")
        def front(f, t):
            band, cup = (52, 52, 60), (224, 122, 95)
            f.cr(2, 5, 11, 1, band); f.c(1, 6, band); f.c(13, 6, band)
            f.cr(0, 7, 2, 3, cup); f.cr(13, 7, 2, 3, cup)
            for k in range(2):
                ph = (t + k * 6) % 12
                x, y = (16 + ph // 4, 6 - ph // 2) if k == 0 else (-3 - ph // 4, 6 - ph // 2)
                nc = (91, 141, 239) if k == 0 else (199, 125, 187)
                f.cr(x, y, 1, 3, nc); f.cr(x - 1, y + 2, 1, 1, nc); f.c(x + 1, y, nc)
        return arms, nop, front, lambda t: -1 if t % 4 < 2 else 0
    if name == "shopping":
        def arms(f, t):
            arm(f, "l", "hold"); arm(f, "r", "down")
        def front(f, t):
            sw = (t // 3) % 2
            bag = (196, 160, 112)
            f.c(-1, 10, (150, 120, 84)); f.c(0, 10, (150, 120, 84))
            f.cr(-3 + sw, 11, 4, 4, bag); f.cr(-3 + sw, 11, 4, 1, (170, 136, 92))
            f.cr(-2 + sw, 8, 1, 3, (127, 176, 105)); f.c(-2 + sw, 7, (100, 150, 80))
            f.cr(0 + sw, 9, 2, 2, (214, 170, 100))
        return arms, nop, front, bounce
    if name == "umbrella":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "hold")
        def front(f, t):
            cols = [(224, 92, 92), WHITE]
            rows = [(3, 9, 2), (1, 13, 3), (0, 15, 4)]
            for (a, b, y) in rows:
                for x in range(a - 1, b + 1):
                    f.c(x, y - 3, cols[(x // 3) % 2])
            f.c(7, -2, (120, 90, 68))
            f.cr(14, 2, 1, 7, (120, 90, 68)); f.c(13, 9, (120, 90, 68))
        return arms, nop, front, breathe
    if name == "bowl":
        def arms(f, t):
            arm(f, "l", "front"); arm(f, "r", "front")
        def front(f, t):
            f.cr(4, 11, 7, 1, WHITE); f.cr(5, 12, 5, 1, WHITE); f.cr(5, 11, 5, 1, (91, 141, 239))
            f.cr(5, 10, 5, 1, WHITE); f.cr(6, 9, 3, 1, WHITE)
            f.cr(10, 6 + (t // 3) % 2, 1, 4, (176, 120, 70)); f.cr(11, 6 + (t // 3) % 2, 1, 4, (150, 100, 60))
            for k in range(2):
                f.c(6 + k * 2 + (t // 2) % 2, 8 - (t + k * 3) % 4, (210, 206, 200))
        return arms, nop, front, breathe
    if name == "wand":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "up")
        def front(f, t):
            f.cr(15, 1, 1, 5, (120, 80, 50))
            sp = (255, 224, 120)
            f.c(15, 0, sp)
            if t % 4 < 2:
                f.c(14, 0, sp); f.c(16, 0, sp); f.c(15, -1, sp); f.c(15, 1, sp)
            for k in range(3):
                ph = (t + k * 4) % 12
                f.c(16 + ph // 2, 1 + k * 2 - ph // 3, [(255, 224, 120), (180, 160, 255), (255, 170, 210)][k])
        return arms, nop, front, breathe
    if name == "clipboard":
        def arms(f, t):
            arm(f, "l", "hold"); arm(f, "r", "front")
        def front(f, t):
            f.cr(-2, 7, 4, 6, (176, 132, 90)); f.cr(-1, 8, 2, 4, WHITE); f.c(-1, 6, (150, 150, 150)); f.c(0, 6, (150, 150, 150))
            if t % 4 < 2:
                f.c(-1, 9, INK); f.c(0, 10, INK)
        return arms, nop, front, still
    if name == "wrench":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "up" if t % 6 < 3 else "hold")
        def front(f, t):
            g = (150, 158, 166)
            if t % 6 < 3:
                f.cr(15, 2, 1, 4, g); f.c(14, 1, g); f.c(16, 1, g)
            else:
                f.cr(15, 6, 3, 1, g); f.c(18, 5, g); f.c(18, 7, g)
        return arms, nop, front, still
    if name == "book":
        def arms(f, t):
            arm(f, "l", "front"); arm(f, "r", "front")
        def front(f, t):
            f.cr(3, 10, 4, 3, (91, 141, 239)); f.cr(8, 10, 4, 3, (91, 141, 239)); f.cr(4, 10, 3, 2, WHITE); f.cr(8, 10, 3, 2, WHITE)
            f.cr(7, 10, 1, 3, (60, 100, 190))
            if t % 12 == 6:
                f.cr(7, 9, 3, 2, WHITE)
        return arms, nop, front, still
    if name == "balloon":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "hold")
        def front(f, t):
            sw = (t // 3) % 2
            f.cr(15, 0 + sw, 1, 8 - sw, (150, 150, 150))
            f.cr(14, -5 + sw, 4, 5, (232, 92, 128)); f.cr(15, -6 + sw, 2, 1, (232, 92, 128)); f.c(15, -4 + sw, (255, 200, 216))
        return arms, nop, front, bounce
    if name == "icecream":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "hold")
        def front(f, t):
            f.cr(14, 8, 2, 2, (214, 170, 100)); f.c(14, 10, (214, 170, 100))
            f.cr(13, 5, 4, 3, (250, 200, 220)); f.cr(14, 4, 2, 1, (250, 200, 220)); f.c(15, 3, (214, 60, 60))
            if t % 8 > 5:
                f.c(13, 8, (250, 200, 220))
        return arms, nop, front, breathe
    if name == "flower":
        def arms(f, t):
            arm(f, "l", "front"); arm(f, "r", "front")
        def front(f, t):
            f.cr(7, 6, 1, 5, (100, 160, 90)); f.c(8, 8, (127, 176, 105))
            pc = (244, 166, 192)
            for (x, y) in [(6, 4), (8, 4), (7, 3), (7, 5)]:
                f.c(x, y, pc)
            f.c(7, 4, (242, 193, 78))
        return arms, nop, front, breathe
    if name == "cake":
        def arms(f, t):
            arm(f, "l", "front"); arm(f, "r", "front")
        def front(f, t):
            f.cr(3, 10, 9, 3, (250, 236, 220)); f.cr(3, 10, 9, 1, (244, 166, 192)); f.cr(2, 13, 11, 1, WHITE)
            f.cr(7, 7, 1, 3, (91, 141, 239)); f.c(7, 6, (255, 190, 80) if t % 2 else (255, 140, 60))
        return arms, nop, front, bounce
    if name == "sill":    # 扒在窗台上
        return (lambda f, t: (arm(f, "l", "sill"), arm(f, "r", "sill")), nop, nop, breathe)
    if name == "sleepbed":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "down")
        def front(f, t):
            f.cr(-3, 11, 21, 4, (214, 200, 236)); f.cr(-3, 11, 21, 1, (236, 226, 246))
            for x in range(-2, 18, 4):
                f.c(x, 13, (190, 170, 220))
        return arms, nop, front, lambda t: -1 if t % 12 < 6 else 0
    if name == "laptop":
        def arms(f, t):
            arm(f, "l", "front" if t % 2 else "down"); arm(f, "r", "down" if t % 2 else "front")
        def front(f, t):
            f.cr(3, 9, 9, 3, (180, 186, 194)); f.cr(4, 10, 7, 1, (120, 200, 255) if t % 6 < 3 else (140, 220, 255)); f.cr(2, 12, 11, 1, (150, 156, 164))
            f.c(7, 10, WHITE)
        return arms, nop, front, still
    if name == "broom":
        def arms(f, t):
            arm(f, "l", "front"); arm(f, "r", "front")
        def front(f, t):
            sx = [0, 1, 2, 1][t % 4]
            f.cr(12 + sx, 6, 1, 8, (176, 132, 90)); f.cr(11 + sx, 14, 4, 2, (214, 186, 100))
            if t % 4 == 2:
                f.c(16 + sx, 15, (200, 190, 176)); f.c(18 + sx, 14, (210, 200, 186))
        return arms, nop, front, still
    if name == "plant":
        def arms(f, t):
            arm(f, "l", "down"); arm(f, "r", "hold")
        def front(f, t):
            f.cr(14, 7, 4, 3, (91, 141, 239)); f.cr(18, 7, 2, 1, (91, 141, 239)); f.c(13, 7, (91, 141, 239))
            for k in range(3):
                f.c(19 + (t + k) % 2, 9 + (t + k * 2) % 5, (120, 180, 232))
            f.cr(20, 14, 3, 1, (170, 110, 80)); f.cr(20, 15, 3, 1, (150, 96, 70))
            f.cr(21, 12 - (t // 6), 1, 2 + (t // 6), (100, 160, 90)); f.c(22, 12 - (t // 6), (127, 176, 105))
        return arms, nop, front, still
    return act("idle")


ACT_NAMES = {"idle": "站着", "wave": "挥手", "jump": "蹦蹦跳", "tea": "喝茶", "music": "听歌", "shopping": "买菜", "umbrella": "举伞",
             "bowl": "捧着小碗", "wand": "施魔法", "clipboard": "做记录", "wrench": "修东西", "book": "看书", "balloon": "拿气球",
             "icecream": "吃冰淇淋", "flower": "捧花", "cake": "捧蛋糕", "sill": "扒窗台", "sleepbed": "睡觉", "laptop": "敲电脑",
             "broom": "扫地", "plant": "浇花"}


# ---------------------------------------------------------------- 合成
def render(spec):
    sc = SCENES[spec["scene"]]
    behind, lower, upper, head = outfit(spec["outfit"])
    arms, pback, pfront, bob = act(spec["act"])
    fk = spec["face"]
    out = []
    for t in range(FRAMES):
        f = Frame(BG.get(spec["scene"], (243, 239, 231)))
        sc(f, t, None)
        f.dy = bob(t)
        f.cr(3, 15, 9, 1, mix(f.p[OX + 7, min(H - 1, OY + 15)], (0, 0, 0), .25), bob=False)
        behind(f, t)
        for x in (3, 5, 9, 11):
            lift = spec["act"] in ("shopping",) and ((x in (3, 9)) == (t % 4 < 2))
            f.cr(x, 13, 1, 2 - (1 if lift else 0), BODY, bob=False)
        f.cr(2, 6, 11, 7, BODY)
        lower(f, t)
        face(f, t, fk)
        upper(f, t)
        pback(f, t)
        arms(f, t)
        pfront(f, t)
        head(f, t)
        effects(f, t, fk)
        out.append(f.im.resize((W * S, H * S), Image.NEAREST))
    return out


def save(frames, path):
    pal = [fr.convert("P", palette=Image.ADAPTIVE, colors=64) for fr in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=MS, loop=0, optimize=True, disposal=1)


# 精选组合：衣服 × 动作 × 表情 × 场景
LIST = [
    ("maid", "tea", "happy", "pink"), ("maid", "broom", "calm", "cream"), ("maid", "cake", "love", "pink"), ("maid", "wave", "happy", "room"),
    ("maid", "bowl", "sulky", "peach"),
    ("dress", "umbrella", "happy", "rain"), ("dress", "flower", "love", "pink"), ("dress", "jump", "happy", "sky"), ("dress", "icecream", "happy", "peach"),
    ("dress", "balloon", "happy", "sky"), ("dress", "idle", "sulky", "pink"),
    ("wizard", "wand", "calm", "lilac"), ("wizard", "wand", "happy", "night"), ("wizard", "book", "think", "lilac"), ("wizard", "idle", "angry", "night"),
    ("lab", "clipboard", "think", "mint"), ("lab", "laptop", "normal", "mint"), ("lab", "tea", "calm", "mint"), ("lab", "idle", "surprise", "cream"),
    ("worker", "wrench", "normal", "peach"), ("worker", "wrench", "angry", "peach"), ("worker", "bowl", "happy", "cream"), ("worker", "wave", "happy", "sky"),
    ("doctor", "clipboard", "calm", "mint"), ("doctor", "idle", "normal", "sky"), ("doctor", "tea", "sleep", "mint"),
    ("pajama", "sill", "look_up", "snow"), ("pajama", "sleepbed", "sleep", "night"), ("pajama", "tea", "calm", "night_win"), ("pajama", "book", "sleep", "lilac"),
    ("pajama", "idle", "cry", "night"),
    ("prince", "wave", "happy", "sky"), ("prince", "flower", "love", "pink"), ("prince", "idle", "calm", "lilac"), ("prince", "idle", "sulky", "cream"),
    ("chef", "bowl", "happy", "peach"), ("chef", "cake", "happy", "cream"), ("chef", "idle", "angry", "peach"),
    ("scarf", "sill", "look_up", "snow"), ("scarf", "tea", "calm", "snow"), ("scarf", "shopping", "happy", "shop"), ("scarf", "umbrella", "normal", "rain"),
    ("sailor", "wave", "happy", "sky"), ("sailor", "jump", "happy", "sky"), ("sailor", "icecream", "love", "sky"),
    ("none", "sill", "look_up", "rain_win"), ("none", "sill", "look_up", "sun_win"), ("none", "sill", "happy", "sun_win"), ("none", "sill", "sad", "rain_win"),
    ("none", "music", "happy", "lilac"), ("none", "music", "calm", "mint"), ("none", "shopping", "happy", "shop"), ("none", "umbrella", "normal", "rain"),
    ("none", "umbrella", "cry", "rain"), ("none", "bowl", "happy", "cream"), ("none", "tea", "calm", "room"),
    ("none", "idle", "happy", "room"), ("none", "idle", "sad", "cream"), ("none", "idle", "cry", "cream"), ("none", "idle", "angry", "peach"),
    ("none", "idle", "sulky", "pink"), ("none", "idle", "calm", "mint"), ("none", "idle", "surprise", "sky"), ("none", "idle", "love", "pink"),
    ("none", "plant", "happy", "mint"), ("none", "laptop", "think", "cream"), ("none", "balloon", "happy", "sky"), ("none", "sleepbed", "sleep", "night"),
]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    meta = []
    for i, (o, a, fc, sc) in enumerate(LIST):
        spec = dict(outfit=o, act=a, face=fc, scene=sc)
        name = "clawd-%02d-%s-%s-%s.gif" % (i + 1, o, a, fc)
        save(render(spec), os.path.join(out_dir, name))
        meta.append(dict(file=name, outfit=OUTFIT_NAMES[o], act=ACT_NAMES[a], face=FACE_NAMES[fc]))
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(len(meta), "gifs")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
