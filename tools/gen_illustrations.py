# -*- coding: utf-8 -*-
"""
为 75 篇短文生成主题插图（扁平矢量 SVG，16:9 宽幅）

用法：
    python tools/gen_illustrations.py            # 生成全部
    python tools/gen_illustrations.py Y01 B一A   # 只生成指定篇目

输出：
    assets/img/<id>.svg          每篇一张
    data/passages.json           写入 img 字段（"assets/img/<id>.svg"）

设计：薄荷绿主题调色板 × 35 个主题场景模板，风格统一、体积约 2-4 KB/张。
"""
import os
import sys
import json
import random

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'img')
DATA = os.path.join(ROOT, 'data', 'passages.json')

W, H = 960, 540
GY = 428          # 人物站立基准线

# ---------------- 调色板 ----------------
PALETTES = {
    'mint':   dict(bg1='#f3fbf8', bg2='#e6f6ef', main='#17a67a', dark='#0f7d5c',
                   soft='#c4e8da', accent='#e0913c', ink='#2b3d45'),
    'blue':   dict(bg1='#f2f8fd', bg2='#e4eef9', main='#2f6fb5', dark='#1e4d83',
                   soft='#cfe0f2', accent='#17a67a', ink='#2b3d45'),
    'warm':   dict(bg1='#fdf8f1', bg2='#faeddb', main='#e0822f', dark='#b25f1c',
                   soft='#f7dcb6', accent='#17a67a', ink='#40342a'),
    'violet': dict(bg1='#f8f5fc', bg2='#ece5f7', main='#7b5ea7', dark='#5a4180',
                   soft='#ded3f0', accent='#e0822f', ink='#332b40'),
    'teal':   dict(bg1='#f0faf9', bg2='#dff2f0', main='#1f8b8b', dark='#146666',
                   soft='#c6e6e4', accent='#e0822f', ink='#2b3d45'),
}

# ---------------- 基础元件 ----------------
def R(x, y, w, h, fill, rx=0, **kw):
    a = ''.join(' %s="%s"' % (k.replace('_', '-'), v) for k, v in kw.items())
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s"%s/>' % (
        x, y, w, h, rx, fill, a)


def C(cx, cy, r, fill, **kw):
    a = ''.join(' %s="%s"' % (k.replace('_', '-'), v) for k, v in kw.items())
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"%s/>' % (cx, cy, r, fill, a)


def E(cx, cy, rx, ry, fill, **kw):
    a = ''.join(' %s="%s"' % (k.replace('_', '-'), v) for k, v in kw.items())
    return '<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s"%s/>' % (
        cx, cy, rx, ry, fill, a)


def P(d, fill='none', **kw):
    a = ''.join(' %s="%s"' % (k.replace('_', '-'), v) for k, v in kw.items())
    return '<path d="%s" fill="%s"%s/>' % (d, fill, a)


def L(x1, y1, x2, y2, stroke, w=4, cap='round'):
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" stroke-linecap="%s"/>' % (
        x1, y1, x2, y2, stroke, w, cap)


def person(cx, gy, s=1.0, head='#f8d3ae', body='#17a67a', dark=None,
           arms='down', hair=None, skirt=False):
    """扁平人物：圆头 + 圆角矩形身体 + 双腿 + 双臂"""
    dark = dark or body
    r = 27 * s
    hy = gy - 152 * s + r          # 头心
    by = hy + r + 2 * s            # 身体顶
    bh = 76 * s
    o = []
    # 腿
    lt = by + bh - 8 * s
    o.append(R(cx - 19 * s, lt, 14 * s, gy - lt, dark, 7 * s))
    o.append(R(cx + 5 * s, lt, 14 * s, gy - lt, dark, 7 * s))
    # 手臂
    if arms == 'down':
        o.append(R(cx - 39 * s, by + 8 * s, 12 * s, 56 * s, body, 6 * s))
        o.append(R(cx + 27 * s, by + 8 * s, 12 * s, 56 * s, body, 6 * s))
    elif arms == 'up':
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" transform="rotate(25 %.1f %.1f)"/>'
                 % (cx - 44 * s, by - 26 * s, 12 * s, 62 * s, 6 * s, body, cx - 38 * s, by + 6 * s))
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" transform="rotate(-25 %.1f %.1f)"/>'
                 % (cx + 32 * s, by - 26 * s, 12 * s, 62 * s, 6 * s, body, cx + 38 * s, by + 6 * s))
    elif arms == 'front':
        o.append(R(cx - 40 * s, by + 14 * s, 22 * s, 12 * s, body, 6 * s))
        o.append(R(cx + 18 * s, by + 14 * s, 22 * s, 12 * s, body, 6 * s))
    elif arms == 'none':
        pass
    # 身体
    if skirt:
        o.append(P('M %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f Z'
                   % (cx - 26 * s, by, cx + 26 * s, by, cx + 38 * s, by + bh, cx - 38 * s, by + bh), body))
    else:
        o.append(R(cx - 28 * s, by, 56 * s, bh, body, 16 * s))
    # 头
    o.append(C(cx, hy, r, head))
    if hair:
        o.append(P('M %.1f %.1f a %.1f %.1f 0 0 1 %.1f 0 Z' % (cx - r, hy - 2 * s, r, r, 2 * r), hair))
    return '\n'.join(o)


def cloud(x, y, s=1.0, fill='#ffffff', op=0.9):
    return ('<g opacity="%.2f">%s%s%s</g>' % (op,
            E(x, y, 46 * s, 26 * s, fill),
            E(x - 38 * s, y + 8 * s, 30 * s, 20 * s, fill),
            E(x + 40 * s, y + 8 * s, 32 * s, 21 * s, fill)))


def tree(x, gy, s=1.0, trunk='#a9744f', leaf='#17a67a'):
    o = [R(x - 6 * s, gy - 70 * s, 12 * s, 70 * s, trunk, 4 * s),
         C(x, gy - 92 * s, 40 * s, leaf),
         C(x - 32 * s, gy - 70 * s, 27 * s, leaf),
         C(x + 32 * s, gy - 70 * s, 27 * s, leaf)]
    return '\n'.join(o)


def heart(x, y, s=1.0, fill='#e05a5a'):
    d = ('M %.1f %.1f C %.1f %.1f %.1f %.1f %.1f %.1f '
         'C %.1f %.1f %.1f %.1f %.1f %.1f '
         'C %.1f %.1f %.1f %.1f %.1f %.1f '
         'C %.1f %.1f %.1f %.1f %.1f %.1f Z') % (
        x, y - 10 * s,
        x - 20 * s, y - 30 * s, x - 40 * s, y - 10 * s, x - 40 * s, y + 5 * s,
        x - 40 * s, y + 22 * s, x - 20 * s, y + 34 * s, x, y + 48 * s,
        x + 20 * s, y + 34 * s, x + 40 * s, y + 22 * s, x + 40 * s, y + 5 * s,
        x + 40 * s, y - 10 * s, x + 20 * s, y - 30 * s, x, y - 10 * s)
    return P(d, fill)


def star(x, y, r, fill):
    pts = []
    import math
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append('%.1f,%.1f' % (x + rr * math.cos(ang), y - rr * math.sin(ang)))
    return '<polygon points="%s" fill="%s"/>' % (' '.join(pts), fill)


def coin(x, y, r, main, soft):
    return (C(x, y, r, soft, stroke=main, stroke_width=3) + '\n' +
            L(x - r * 0.42, y - r * 0.30, x, y, main, 3) +
            L(x + r * 0.42, y - r * 0.30, x, y, main, 3) +
            L(x, y, x, y + r * 0.42, main, 3) +
            L(x - r * 0.42, y + 0.12 * r, x + r * 0.42, y + 0.12 * r, main, 3) +
            L(x - r * 0.42, y + 0.52 * r, x + r * 0.42, y + 0.52 * r, main, 3))


def bubble(x, y, w, h, fill, stroke, tail='left'):
    """对话/思考气泡"""
    o = [E(x + w / 2, y + h / 2, w / 2, h / 2, fill, stroke=stroke, stroke_width=3.5)]
    if tail == 'left':
        o.append(P('M %.1f %.1f L %.1f %.1f L %.1f %.1f Z'
                   % (x + 6, y + h - 20, x - 26, y + h + 22, x + 46, y + h - 4), fill))
    else:
        o.append(P('M %.1f %.1f L %.1f %.1f L %.1f %.1f Z'
                   % (x + w - 6, y + h - 20, x + w + 26, y + h + 24, x + w - 46, y + h - 4), fill))
    return '\n'.join(o)


def lines(x, y, n, w, gap, color, lw=7):
    """气泡里的文字线"""
    out = []
    for i in range(n):
        ww = w if i % 2 == 0 else w * 0.72
        out.append(R(x, y + i * gap, ww, lw, color, lw / 2, opacity=0.75))
    return '\n'.join(out)


# ---------------- 场景：语言 / 沟通 ----------------
def sc_speech(p, v):
    o = [person(268, GY, 1.0, body=p['main'], dark=p['dark'], arms='front')]
    o.append(bubble(430, 128, 330, 150, '#ffffff', p['main'], 'left'))
    o.append(lines(470, 168, 3, 240, 34, p['soft']))
    o.append(bubble(640, 300, 210, 92, p['soft'], p['main'], 'right'))
    o.append(lines(672, 326, 2, 140, 26, '#ffffff', 6))
    for i, r in enumerate((40, 62, 84)):
        o.append(P('M 836 %d A %d %d 0 0 1 836 %d' % (232 - r, r, r, 232 + r), 'none',
                   stroke=p['accent'], stroke_width=5, opacity=0.6 - i * 0.15))
    return '\n'.join(o)


def sc_book(p, v):
    o = []
    if v == 'stack':
        for i, (dx, dy) in enumerate([(0, 0), (0, -34), (0, -68), (60, -34)]):
            o.append(R(300 + dx, 300 + dy, 300, 30, p['main'] if i % 2 == 0 else p['accent'], 6))
            o.append(R(312 + dx, 308 + dy, 200, 8, '#ffffff', 4, opacity=0.6))
        o.append(R(300, 330, 300, 26, p['dark'], 6))
        o.append(person(700, GY, 0.95, body=p['soft'], dark=p['main'], arms='front'))
    else:
        # 打开的书
        o.append(P('M 250 350 L 470 318 L 470 400 L 250 424 Z', p['main']))
        o.append(P('M 710 350 L 490 318 L 490 400 L 710 424 Z', p['main']))
        o.append(P('M 470 318 L 490 318 L 490 400 L 470 400 Z', p['dark']))
        o.append(P('M 250 424 L 470 400 L 710 424 L 710 436 L 250 460 Z', p['dark']))
        for i in range(3):
            o.append(R(276, 356 + i * 22, 150, 7, '#ffffff', 3.5, opacity=0.7))
            o.append(R(534, 356 + i * 22, 150, 7, '#ffffff', 3.5, opacity=0.7))
        o.append(P('M 470 300 C 430 240 500 210 470 160', 'none', stroke=p['accent'], stroke_width=5))
        o.append(star(470, 140, 20, p['accent']))
        if v == 'magnifier':
            o.append(C(596, 232, 56, '#ffffff', stroke=p['dark'], stroke_width=6))
            o.append(L(636, 272, 686, 322, p['dark'], 12))
        else:
            o.append(C(596, 226, 16, p['accent'], opacity=0.85))
            o.append(C(556, 262, 10, p['accent'], opacity=0.7))
            o.append(C(640, 264, 8, p['accent'], opacity=0.6))
    return '\n'.join(o)


# ---------------- 场景：职场 / 演讲 ----------------
def sc_office(p, v):
    o = []
    if v == 'shadow':
        o.append(E(700, 300, 96, 130, '#8f9aa4', opacity=0.35))
        o.append(person(700, GY, 1.05, head='#e3e8ea', body='#8f9aa4', dark='#77828b', arms='down'))
    # 桌子
    o.append(R(250, 372, 460, 18, p['dark'], 6))
    o.append(R(288, 390, 16, 40, p['dark'], 5))
    o.append(R(656, 390, 16, 40, p['dark'], 5))
    # 显示器
    o.append(R(392, 246, 176, 116, '#ffffff', 10, stroke=p['main'], stroke_width=5))
    o.append(R(462, 362, 36, 12, p['main'], 4))
    o.append(R(408, 262, 144, 12, p['soft'], 6))
    o.append(R(408, 286, 110, 9, p['soft'], 4.5, opacity=0.8))
    o.append(R(408, 304, 130, 9, p['soft'], 4.5, opacity=0.8))
    o.append(R(408, 322, 84, 9, p['soft'], 4.5, opacity=0.8))
    # 人
    o.append(person(700, GY, 0.92, body=p['main'], dark=p['dark'], arms='front'))
    if v == 'heart':
        o.append(R(300, 340, 40, 32, '#ffffff', 6, stroke=p['accent'], stroke_width=4))
        o.append(heart(320, 342, 0.62, p['accent']))
    else:
        o.append(R(300, 344, 44, 28, '#ffffff', 6, stroke=p['main'], stroke_width=4))
        o.append(R(310, 336, 24, 10, p['soft'], 5))
    return '\n'.join(o)


def sc_crowd(p, v):
    o = []
    for i, x in enumerate((150, 250, 350, 780, 870)):
        o.append(person(x, GY, 0.68, head='#f8d3ae',
                        body=p['soft'] if i % 2 else p['main'], dark=p['dark'], arms='down'))
    # 讲台
    o.append(R(430, 300, 120, 130, p['accent'], 8))
    o.append(P('M 424 300 L 556 300 L 540 262 L 440 262 Z', '#ffffff', opacity=0.9))
    o.append(person(490, 300, 0.92, body=p['main'], dark=p['dark'], arms='up', hair='#4a3b32'))
    # 麦克风
    o.append(L(600, 300, 620, 250, p['dark'], 5))
    o.append(C(624, 240, 14, p['dark']))
    for i, r in enumerate((52, 80, 108)):
        o.append(P('M 660 %d a %d %d 0 0 1 0 %d' % (240 - r, r, r, 2 * r), 'none',
                   stroke=p['accent'], stroke_width=4, opacity=0.55 - i * 0.13))
    return '\n'.join(o)


# ---------------- 场景：成长 / 阶梯 ----------------
def sc_stairs(p, v):
    o = []
    steps = [(300, 392), (368, 356), (436, 320), (504, 284), (572, 248)]
    for i, (x, y) in enumerate(steps):
        o.append(R(x, y, 120, 40, p['main'] if i % 2 == 0 else p['soft'], 5))
        o.append(R(x, y, 120, 8, '#ffffff', 3, opacity=0.5))
    o.append(R(260, 392, 44, 40, p['dark'], 5))
    if v == 'fall':
        o.append(person(470, 320, 0.9, body=p['accent'], dark='#b25f1c', arms='front'))
        o.append(P('M 520 250 l 26 -22 M 546 250 l -26 -22', 'none', stroke=p['accent'], stroke_width=5, stroke_linecap='round'))
        o.append(star(566, 214, 16, p['accent']))
    elif v == 'heavy':
        o.append(person(500, 284, 0.9, body=p['main'], dark=p['dark'], arms='down'))
        o.append(R(470, 200, 62, 46, p['dark'], 8))
        o.append(L(496, 200, 496, 246, '#ffffff', 4, cap='butt'))
    else:
        o.append(person(500, 248, 1.0, body=p['main'], dark=p['dark'], arms='up', hair='#4a3b32'))
        o.append(star(700, 150, 22, p['accent']))
        o.append(star(748, 196, 14, p['accent']))
    return '\n'.join(o)


# ---------------- 场景：交通 ----------------
def sc_car(p, v):
    o = []
    if v in ('bus', 'green', 'compare'):
        # 公交车
        o.append(R(320, 250, 400, 150, p['main'], 16))
        o.append(R(340, 272, 100, 62, '#eaf6fb', 8))
        o.append(R(454, 272, 100, 62, '#eaf6fb', 8))
        o.append(R(568, 272, 100, 62, '#eaf6fb', 8))
        o.append(R(340, 350, 328, 26, p['dark'], 6))
        o.append(C(398, 416, 34, '#3b4a52'))
        o.append(C(398, 416, 15, p['soft']))
        o.append(C(672, 416, 34, '#3b4a52'))
        o.append(C(672, 416, 15, p['soft']))
        o.append(R(760, 300, 12, 60, p['dark'], 4))
    if v == 'car':
        o.append(R(300, 300, 380, 96, p['main'], 18))
        o.append(P('M 372 300 L 420 246 L 566 246 L 614 300 Z', p['main']))
        o.append(P('M 392 300 L 424 258 L 508 258 L 540 300 Z', '#eaf6fb'))
        o.append(P('M 520 300 L 552 258 L 566 258 L 590 300 Z', '#eaf6fb'))
        o.append(C(392, 412, 40, '#3b4a52'))
        o.append(C(392, 412, 17, p['soft']))
        o.append(C(620, 412, 40, '#3b4a52'))
        o.append(C(620, 412, 17, p['soft']))
        o.append(R(300, 348, 380, 14, p['dark'], 6))
        # 价签
        o.append(P('M 700 210 l 130 0 l 0 66 l -40 40 l -90 0 Z', p['accent']))
        o.append(C(716, 243, 9, '#ffffff'))
        o.append(L(734, 236, 800, 236, '#ffffff', 7))
        o.append(L(734, 256, 786, 256, '#ffffff', 7))
    if v == 'green':
        # 自行车
        o.append(C(214, 388, 46, 'none', stroke=p['accent'], stroke_width=8))
        o.append(C(320, 388, 46, 'none', stroke=p['accent'], stroke_width=8))
        o.append(P('M 214 388 L 268 320 L 320 388', 'none', stroke=p['accent'], stroke_width=8))
        o.append(L(268, 320, 300, 300, p['accent'], 8))
        o.append(C(300, 296, 10, p['accent']))
        # 推车的人
        o.append(person(150, GY, 0.82, body=p['main'], dark=p['dark'], arms='front'))
        o.append(L(176, 330, 240, 320, p['dark'], 5))
        o.append(tree(830, GY, 0.8, '#a9744f', p['main']))
        o.append(C(870, 200, 16, p['soft']))
        o.append(C(160, 180, 20, p['soft']))
    if v == 'compare':
        # 左边小汽车
        o.append(R(180, 322, 210, 66, p['accent'], 14))
        o.append(P('M 224 322 L 256 284 L 322 284 L 350 322 Z', p['accent']))
        o.append(C(240, 400, 30, '#3b4a52'))
        o.append(C(240, 400, 12, p['soft']))
        o.append(C(340, 400, 30, '#3b4a52'))
        o.append(C(340, 400, 12, p['soft']))
        o.append(L(460, 250, 460, 400, p['dark'], 5))
        o.append(C(460, 325, 40, '#ffffff', stroke=p['dark'], stroke_width=4))
        o.append(L(444, 310, 476, 340, p['dark'], 5))
        o.append(L(476, 310, 444, 340, p['dark'], 5))
    else:
        # 站牌
        if v == 'bus':
            o.append(R(240, 200, 12, 230, p['dark'], 4))
            o.append(R(190, 190, 112, 62, p['accent'], 8))
            o.append(R(204, 206, 84, 8, '#ffffff', 4))
            o.append(R(204, 224, 60, 8, '#ffffff', 4))
            o.append(person(760, GY, 0.85, body=p['accent'], dark='#b25f1c', arms='down'))
    return '\n'.join(o)


# ---------------- 场景：人际关系 ----------------
def sc_two(p, v):
    o = []
    if v == 'back':
        o.append(person(370, GY, 1.0, body=p['main'], dark=p['dark'], arms='down', hair='#4a3b32'))
        o.append(person(600, GY, 1.0, body=p['accent'], dark='#b25f1c', arms='down', hair='#3b2f28'))
        o.append(P('M 480 190 L 470 300 L 492 340 L 474 400', 'none', stroke='#b0bac0', stroke_width=6, stroke_linecap='round'))
    elif v == 'handshake':
        o.append(person(350, GY, 1.0, body=p['main'], dark=p['dark'], arms='front'))
        o.append(person(620, GY, 1.0, body=p['accent'], dark='#b25f1c', arms='front'))
        o.append(R(430, 300, 110, 34, '#f8d3ae', 16))
        o.append(L(430, 312, 540, 312, p['dark'], 4))
    elif v == 'gloves':
        o.append(person(300, GY, 0.98, body=p['main'], dark=p['dark'], arms='front'))
        o.append(person(560, GY, 0.98, body=p['accent'], dark='#b25f1c', arms='front'))
        # 手套
        o.append(R(680, 300, 74, 96, p['soft'], 18, stroke=p['main'], stroke_width=4))
        o.append(R(676, 356, 26, 44, p['soft'], 12, stroke=p['main'], stroke_width=4))
        o.append(R(706, 356, 22, 38, p['soft'], 11, stroke=p['main'], stroke_width=4))
        o.append(R(730, 356, 20, 32, p['soft'], 10, stroke=p['main'], stroke_width=4))
    elif v == 'shield':
        o.append(person(320, GY, 1.0, body=p['main'], dark=p['dark'], arms='front'))
        o.append(person(640, GY, 1.0, body=p['accent'], dark='#b25f1c', arms='front'))
        o.append(P('M 480 210 L 560 240 L 560 330 C 560 372 480 400 480 400 C 480 400 400 372 400 330 L 400 240 Z',
                   '#ffffff', stroke=p['main'], stroke_width=5))
        o.append(P('M 440 306 l 26 28 l 58 -60', 'none', stroke=p['main'], stroke_width=9, stroke_linecap='round'))
    else:  # heart / date
        o.append(person(340, GY, 1.02, body=p['main'], dark=p['dark'], arms='front', hair='#4a3b32'))
        o.append(person(620, GY, 1.02, body=p['accent'], dark='#b25f1c', arms='front', skirt=True))
        o.append(heart(480, 200, 1.0, '#e05a5a'))
    return '\n'.join(o)


def sc_date(p, v):
    o = [R(300, 350, 380, 16, p['dark'], 6),
         R(322, 366, 14, 62, p['dark'], 5),
         R(644, 366, 14, 62, p['dark'], 5),
         person(300, GY, 0.86, body=p['main'], dark=p['dark'], arms='front'),
         person(700, GY, 0.86, body=p['accent'], dark='#b25f1c', arms='front', skirt=True)]
    # 蜡烛
    o.append(R(470, 288, 22, 62, '#ffffff', 6, stroke=p['soft'], stroke_width=3))
    o.append(P('M 481 288 c -14 -12 0 -22 0 -34 c 0 12 14 22 0 34 Z', p['accent']))
    o.append(R(410, 320, 34, 30, p['soft'], 6))
    o.append(R(520, 320, 34, 30, p['soft'], 6))
    o.append(heart(560, 190, 0.62, '#e05a5a'))
    o.append(C(398, 214, 12, p['accent'], opacity=0.7))
    o.append(C(586, 250, 9, p['accent'], opacity=0.6))
    return '\n'.join(o)


def sc_baby(p, v):
    o = []
    # 婴儿
    o.append(R(430, 290, 130, 92, p['soft'], 26))
    o.append(C(495, 236, 62, '#f8d3ae'))
    o.append(C(468, 226, 9, '#3b2f28'))
    o.append(C(524, 226, 9, '#3b2f28'))
    o.append(P('M 476 262 q 20 20 40 0', 'none', stroke='#c9736a', stroke_width=5, stroke_linecap='round'))
    o.append(C(452, 256, 12, '#f2a3a3', opacity=0.6))
    o.append(C(540, 256, 12, '#f2a3a3', opacity=0.6))
    o.append(R(408, 300, 30, 54, p['soft'], 14))
    o.append(R(552, 300, 30, 54, p['soft'], 14))
    o.append(R(448, 372, 40, 40, p['main'], 12))
    o.append(R(510, 372, 40, 40, p['main'], 12))
    # 奶瓶
    o.append(R(660, 300, 44, 100, '#ffffff', 12, stroke=p['main'], stroke_width=4))
    o.append(R(668, 274, 28, 30, p['accent'], 8))
    o.append(R(660, 340, 44, 22, p['soft'], 4))
    # 球
    o.append(C(300, 386, 40, p['accent']))
    o.append(P('M 262 386 a 40 40 0 0 0 76 0', 'none', stroke='#ffffff', stroke_width=4))
    o.append(star(760, 220, 18, p['accent']))
    o.append(star(230, 210, 13, p['accent']))
    return '\n'.join(o)


# ---------------- 场景：情绪 / 日历 ----------------
def sc_calendar(p, v):
    o = []
    # 日历
    o.append(R(300, 210, 250, 210, '#ffffff', 14, stroke=p['main'], stroke_width=5))
    o.append(R(300, 210, 250, 44, p['main'], 14))
    o.append(R(300, 238, 250, 16, p['main']))
    for i in range(3):
        for j in range(4):
            x = 322 + j * 58
            y = 274 + i * 46
            o.append(R(x, y, 40, 30, p['soft'], 5, opacity=0.55))
    o.append(C(438, 320, 20, 'none', stroke=p['accent'], stroke_width=5))
    # 乌云 + 雨
    o.append(cloud(660, 196, 1.15, '#9fb0bd', 0.95))
    o.append(cloud(770, 236, 0.9, '#9fb0bd', 0.8))
    for i, x in enumerate((624, 664, 704, 744)):
        o.append(L(x, 250 + i % 2 * 18, x - 8, 292 + i % 2 * 18, '#7fa7c4', 6))
    # 咖啡杯
    o.append(R(180, 356, 84, 72, '#ffffff', 10, stroke=p['accent'], stroke_width=4))
    o.append(P('M 264 372 q 26 4 26 22 q 0 18 -26 20', 'none', stroke=p['accent'], stroke_width=6))
    o.append(P('M 202 340 q 8 -18 0 -34 M 226 340 q 8 -18 0 -34', 'none', stroke='#c0cbd2', stroke_width=4))
    return '\n'.join(o)


def sc_mirror(p, v):
    o = []
    if v == 'compare':
        o.append(person(250, GY, 0.78, body=p['main'], dark=p['dark'], arms='down'))
        o.append(person(420, GY, 1.18, body=p['accent'], dark='#b25f1c', arms='down'))
        o.append(P('M 560 300 l 60 0 M 560 340 l 60 0', 'none', stroke='#98a3ab', stroke_width=8, stroke_linecap='round'))
        o.append(P('M 700 280 l 0 100', 'none', stroke='#98a3ab', stroke_width=8, stroke_linecap='round'))
        o.append(P('M 660 280 l 80 0 M 660 380 l 80 0', 'none', stroke='#98a3ab', stroke_width=8, stroke_linecap='round'))
    elif v == 'body':
        o.append(R(300, 168, 20, 260, p['dark'], 6))
        for i in range(5):
            o.append(L(320, 200 + i * 50, 356, 200 + i * 50, p['soft'], 5))
        o.append(person(560, GY, 1.05, body=p['main'], dark=p['dark'], arms='front', hair='#4a3b32'))
        o.append(R(660, 214, 150, 190, '#ffffff', 14, stroke=p['main'], stroke_width=5))
        o.append(C(735, 300, 48, p['soft']))
        o.append(R(700, 348, 70, 40, p['soft'], 18))
        o.append(heart(830, 200, 0.6, '#e05a5a'))
    else:
        o.append(R(330, 150, 300, 250, '#ffffff', 18, stroke=p['main'], stroke_width=6))
        o.append(P('M 356 380 L 604 190 L 630 210 L 382 400 Z', p['soft'], opacity=0.55))
        o.append(person(480, 400, 0.98, body=p['main'], dark=p['dark'], arms='front', hair='#4a3b32'))
        o.append(R(390, 400, 180, 16, p['dark'], 6))
        o.append(C(760, 220, 22, p['accent'], opacity=0.8))
        o.append(C(812, 268, 14, p['accent'], opacity=0.6))
    return '\n'.join(o)


def sc_stress(p, v):
    o = []
    # 头部侧影
    o.append(P('M 300 400 C 300 250 420 170 520 190 C 610 208 640 300 620 360 C 606 400 560 410 520 404 Z',
               p['soft'], stroke=p['main'], stroke_width=5))
    o.append(C(470, 268, 40, '#ffffff', stroke=p['main'], stroke_width=4))
    o.append(C(470, 268, 16, p['main'], opacity=0.35))
    # 压力射线
    for i in range(5):
        import math
        a = math.radians(-70 + i * 32)
        x1 = 520 + 120 * math.cos(a)
        y1 = 270 + 120 * math.sin(a)
        o.append(L(x1, y1, x1 + 46 * math.cos(a), y1 + 46 * math.sin(a), p['accent'], 7))
    # 心跳线
    o.append(P('M 660 350 l 40 0 l 16 -40 l 22 76 l 20 -56 l 16 20 l 60 0', 'none',
               stroke='#d9534f', stroke_width=6, stroke_linecap='round'))
    o.append(heart(690, 250, 0.7, '#e05a5a'))
    o.append(L(300, 430, 640, 430, p['main'], 5))
    return '\n'.join(o)


def sc_person_think(p, v):
    o = [person(430, GY, 1.05, body=p['main'], dark=p['dark'], arms='front', hair='#4a3b32')]
    o.append(bubble(560, 130, 300, 150, '#ffffff', p['main'], 'left'))
    if v == 'voice':
        for i, r in enumerate((30, 44, 58)):
            o.append(P('M 640 %d a %d %d 0 0 1 0 %d' % (250 - r, r, r, 2 * r), 'none',
                       stroke=p['accent'], stroke_width=4, opacity=0.75 - i * 0.18))
        o.append(lines(600, 172, 2, 200, 34, p['soft'], 8))
    elif v == 'star':
        o.append(star(700, 200, 26, p['accent']))
        o.append(star(760, 236, 15, p['accent']))
        o.append(lines(600, 172, 2, 200, 34, p['soft'], 8))
    else:
        o.append(lines(600, 172, 3, 214, 34, p['soft'], 8))
    o.append(C(280, 250, 18, p['accent'], opacity=0.6))
    o.append(C(240, 300, 12, p['accent'], opacity=0.45))
    return '\n'.join(o)


def sc_smile(p, v):
    o = [C(470, 268, 150, p['main']),
         C(470, 268, 128, '#ffffff', opacity=0.22)]
    o.append(C(420, 236, 16, p['dark']))
    o.append(C(528, 236, 16, p['dark']))
    o.append(P('M 396 308 q 78 76 152 0', 'none', stroke=p['dark'], stroke_width=12, stroke_linecap='round'))
    o.append(P('M 400 312 q 72 66 146 0 Z', '#ffffff', opacity=0.55))
    for i, (dx, dy, s) in enumerate(((320, 150, 0.7), (640, 168, 0.85), (250, 320, 0.5), (700, 330, 0.6))):
        o.append(heart(dx, dy, s, '#e05a5a'))
    for i in range(8):
        import math
        a = i * math.pi / 4
        o.append(L(470 + 176 * math.cos(a), 268 + 176 * math.sin(a),
                   470 + 208 * math.cos(a), 268 + 208 * math.sin(a), p['accent'], 6))
    return '\n'.join(o)


# ---------------- 场景：金钱 ----------------
def sc_money(p, v):
    o = []
    if v == 'piggy':
        o.append(E(470, 320, 150, 108, p['main']))
        o.append(P('M 340 288 L 300 238 L 356 254 Z', p['main']))
        o.append(R(430, 246, 80, 14, p['dark'], 6))
        o.append(C(588, 330, 20, p['dark']))
        o.append(C(596, 330, 8, p['soft']))
        o.append(R(392, 372, 34, 44, p['dark'], 12))
        o.append(R(514, 372, 34, 44, p['dark'], 12))
        o.append(P('M 348 424 q 10 -22 34 -14', 'none', stroke=p['dark'], stroke_width=6))
        o.append(coin(470, 190, 44, p['accent'], '#fbe4c2'))
        o.append(coin(220, 380, 34, p['accent'], '#fbe4c2'))
        o.append(coin(720, 380, 30, p['accent'], '#fbe4c2'))
    elif v == 'scales':
        o.append(R(460, 200, 20, 200, p['dark'], 8))
        o.append(R(330, 210, 280, 16, p['dark'], 8))
        o.append(L(340, 218, 340, 290, p['main'], 5))
        o.append(L(600, 218, 600, 290, p['main'], 5))
        o.append(P('M 280 290 q 60 56 120 0 Z', p['soft'], stroke=p['main'], stroke_width=5))
        o.append(P('M 540 290 q 60 56 120 0 Z', p['soft'], stroke=p['main'], stroke_width=5))
        o.append(coin(340, 268, 30, p['accent'], '#fbe4c2'))
        o.append(coin(600, 258, 30, p['accent'], '#fbe4c2'))
        o.append(C(480, 180, 16, p['accent']))
    elif v == 'child':
        o.append(person(340, GY, 0.82, body=p['main'], dark=p['dark'], arms='front'))
        o.append(person(640, GY, 1.02, body=p['accent'], dark='#b25f1c', arms='front'))
        o.append(coin(490, 300, 40, p['main'], p['soft']))
        o.append(coin(524, 344, 32, p['accent'], '#fbe4c2'))
        o.append(coin(200, 250, 24, p['accent'], '#fbe4c2'))
        o.append(coin(780, 260, 22, p['accent'], '#fbe4c2'))
    else:  # coins
        o.append(coin(470, 300, 74, p['main'], p['soft']))
        o.append(coin(360, 360, 54, p['accent'], '#fbe4c2'))
        o.append(coin(586, 356, 54, p['accent'], '#fbe4c2'))
        o.append(coin(300, 300, 34, p['main'], p['soft']))
        o.append(coin(660, 296, 34, p['main'], p['soft']))
        o.append(R(250, 390, 460, 20, p['dark'], 8))
        o.append(C(200, 220, 14, p['accent'], opacity=0.7))
        o.append(C(790, 220, 18, p['accent'], opacity=0.7))
    return '\n'.join(o)


# ---------------- 场景：理财 / 图表 ----------------
def sc_chart(p, v):
    o = [L(240, 400, 740, 400, p['dark'], 6), L(250, 400, 250, 150, p['dark'], 6)]
    if v == 'savings':
        o.append(P('M 280 360 L 400 300 L 520 330 L 640 210 L 720 170', 'none',
                   stroke=p['main'], stroke_width=9, stroke_linecap='round'))
        o.append(P('M 720 170 l -44 6 l 12 -44 Z', p['accent']))
        for x, y in ((280, 360), (400, 300), (520, 330), (640, 210)):
            o.append(C(x, y, 11, '#ffffff', stroke=p['main'], stroke_width=5))
        o.append(coin(760, 300, 34, p['accent'], '#fbe4c2'))
        o.append(coin(300, 190, 26, p['accent'], '#fbe4c2'))
    else:
        hs = [(290, 150), (370, 120), (450, 250), (530, 250), (610, 130), (690, 100)]
        for i, (x, h) in enumerate(hs):
            fill = p['accent'] if h > 200 else p['main']
            o.append(R(x, 400 - h, 54, h, fill, 6))
            o.append(R(x, 400 - h, 54, 10, '#ffffff', 4, opacity=0.35))
        o.append(P('M 430 300 q 70 -46 146 0', 'none', stroke=p['accent'], stroke_width=5, stroke_dasharray='10 8'))
        o.append(C(504, 262, 30, 'none', stroke=p['accent'], stroke_width=5))
    return '\n'.join(o)


# ---------------- 场景：自然 / 生长 ----------------
def sc_sprout(p, v):
    o = []
    if v == 'sunrise':
        o.append(C(480, 320, 130, p['accent'], opacity=0.85))
        for i in range(8):
            import math
            a = math.pi + i * math.pi / 7
            o.append(L(480 + 150 * math.cos(a), 320 + 150 * math.sin(a),
                       480 + 190 * math.cos(a), 320 + 190 * math.sin(a), p['accent'], 8))
    else:
        o.append(C(700, 176, 62, p['accent']))
    # 土堆
    o.append(P('M 300 400 q 180 -70 360 0 Z', p['dark']))
    o.append(R(300, 396, 360, 14, p['dark'], 6))
    # 幼苗
    o.append(P('M 480 390 C 480 330 470 290 480 250', 'none', stroke=p['main'], stroke_width=10, stroke_linecap='round'))
    o.append(P('M 480 320 C 420 320 396 286 404 258 C 442 254 476 286 480 320 Z', p['main']))
    o.append(P('M 482 288 C 540 288 566 254 558 226 C 520 222 486 254 482 288 Z', p['soft']))
    if v == 'seed':
        o.append(E(360, 376, 26, 18, p['accent']))
        o.append(E(612, 380, 22, 15, p['accent']))
        o.append(star(760, 250, 20, p['accent']))
    return '\n'.join(o)


def sc_signpost(p, v):
    o = [R(462, 200, 24, 230, p['dark'], 8)]
    o.append(P('M 300 226 L 520 226 L 500 280 L 300 280 Z', p['main']))
    o.append(P('M 560 300 L 780 300 L 760 354 L 560 354 Z', p['accent']))
    o.append(P('M 240 316 L 452 316 L 452 366 L 240 366 Z', p['soft']))
    o.append(L(320, 253, 460, 253, '#ffffff', 8))
    o.append(L(590, 327, 720, 327, '#ffffff', 8))
    o.append(L(268, 341, 400, 341, p['dark'], 8))
    o.append(P('M 300 280 l -40 40 l 40 0 Z', p['dark']))
    o.append(P('M 520 226 l 40 -40 l 0 40 Z', p['dark']))
    o.append(tree(830, GY, 0.9, '#a9744f', p['main']))
    o.append(tree(140, GY, 0.75, '#a9744f', p['soft']))
    if v == 'purpose':
        o.append(star(700, 150, 24, p['accent']))
        o.append(star(756, 196, 15, p['accent']))
    return '\n'.join(o)


def sc_town(p, v):
    o = []
    # 远山
    o.append(P('M 0 340 L 150 210 L 300 340 Z', p['soft'], opacity=0.7))
    o.append(P('M 220 340 L 380 180 L 540 340 Z', p['soft'], opacity=0.55))
    o.append(P('M 620 340 L 790 206 L 960 340 Z', p['soft'], opacity=0.65))
    # 房子
    for x, w, h, c in ((200, 110, 90, p['main']), (330, 92, 74, p['accent']),
                       (600, 100, 84, p['main']), (740, 84, 66, p['accent'])):
        o.append(R(x, GY - h, w, h, c, 4))
        o.append(P('M %d %d L %d %d L %d %d Z' % (x - 12, GY - h, x + w / 2, GY - h - 46, x + w + 12, GY - h), p['dark']))
        o.append(R(x + w * 0.3, GY - h + 24, 26, 26, '#eaf6fb', 3))
    # 学校（带旗）
    o.append(R(440, GY - 120, 120, 120, '#ffffff', 4, stroke=p['main'], stroke_width=5))
    o.append(P('M 428 %d L 500 %d L 572 %d Z' % (GY - 120, GY - 176, GY - 120), p['main']))
    o.append(R(494, GY - 236, 6, 60, p['dark'], 3))
    o.append(P('M 500 %d L 546 %d L 500 %d Z' % (GY - 236, GY - 220, GY - 204), p['accent']))
    for i in range(3):
        o.append(R(456 + i * 36, GY - 100, 24, 40, p['soft'], 3))
    o.append(R(430, GY, 140, 12, p['dark'], 4))
    o.append(tree(120, GY, 0.8, '#a9744f', p['main']))
    o.append(tree(860, GY, 0.7, '#a9744f', p['main']))
    return '\n'.join(o)


# ---------------- 场景：网络 / 科技 ----------------
def sc_internet(p, v):
    o = []
    o.append(C(480, 288, 132, p['main'], opacity=0.18))
    o.append(C(480, 288, 112, 'none', stroke=p['main'], stroke_width=6))
    o.append(E(480, 288, 112, 42, 'none', stroke=p['main'], stroke_width=5))
    o.append(E(480, 288, 42, 112, 'none', stroke=p['main'], stroke_width=5))
    o.append(L(368, 288, 592, 288, p['main'], 5))
    nodes = [(300, 200), (660, 196), (250, 360), (700, 356), (480, 140), (480, 440)]
    for x, y in nodes:
        o.append(L(480, 288, x, y, p['soft'], 4))
        o.append(C(x, y, 17, p['main']))
        o.append(C(x, y, 7, '#ffffff'))
    if v == 'hearts':
        o.append(heart(300, 168, 0.5, '#e05a5a'))
        o.append(heart(660, 164, 0.5, '#e05a5a'))
        o.append(heart(700, 318, 0.42, '#e05a5a'))
    elif v == 'people':
        for x, s in ((250, 0.6), (700, 0.6), (480, 0.62)):
            o.append(person(x, GY, s, body=p['accent'], dark='#b25f1c', arms='front'))
    return '\n'.join(o)


def sc_laptop(p, v):
    o = []
    o.append(P('M 300 160 L 660 160 L 676 356 L 284 356 Z', '#ffffff', stroke=p['main'], stroke_width=6))
    o.append(P('M 240 356 L 720 356 L 748 400 L 212 400 Z', p['main']))
    o.append(R(420, 366, 120, 10, p['dark'], 5))
    o.append(R(324, 184, 312, 26, p['soft'], 6))
    o.append(R(324, 226, 200, 12, p['soft'], 6, opacity=0.8))
    o.append(R(324, 252, 260, 12, p['soft'], 6, opacity=0.8))
    o.append(R(324, 278, 160, 12, p['soft'], 6, opacity=0.8))
    o.append(C(640, 300, 30, p['accent'], opacity=0.8))
    o.append(C(360, 306, 20, p['accent'], opacity=0.6))
    if v == 'elder':
        o.append(person(190, GY, 0.78, body=p['accent'], dark='#b25f1c', arms='front', hair='#d9d2cb'))
        o.append(person(790, GY, 0.9, body=p['main'], dark=p['dark'], arms='front'))
        o.append(heart(480, 130, 0.5, '#e05a5a'))
    else:
        o.append(person(790, GY, 0.85, body=p['main'], dark=p['dark'], arms='front'))
    return '\n'.join(o)


def sc_tv(p, v):
    o = []
    o.append(R(280, 170, 400, 230, '#ffffff', 14, stroke=p['main'], stroke_width=6))
    o.append(R(300, 190, 360, 176, p['soft'], 8))
    o.append(C(480, 278, 48, '#ffffff', opacity=0.95))
    o.append(P('M 462 254 L 510 278 L 462 302 Z', p['main']))
    o.append(R(438, 400, 84, 12, p['dark'], 5))
    o.append(R(456, 340, 48, 62, p['dark'], 6))
    o.append(R(676, 200, 14, 60, p['accent'], 5))
    o.append(R(268, 200, 14, 60, p['accent'], 5))
    for i in range(3):
        o.append(P('M %d %d a %d %d 0 0 1 0 %d' % (790, 190 + i * 44, 30 + i * 14, 30 + i * 14, 2 * (30 + i * 14)),
                   'none', stroke=p['accent'], stroke_width=4, opacity=0.5 - i * 0.12))
    return '\n'.join(o)


def sc_email(p, v):
    o = []
    for x, y, s, c in ((250, 250, 1.0, p['main']), (470, 210, 1.15, p['accent']), (690, 262, 0.9, p['main'])):
        o.append(R(x - 90 * s, y - 60 * s, 180 * s, 120 * s, '#ffffff', 8, stroke=c, stroke_width=5))
        o.append(P('M %.1f %.1f L %.1f %.1f L %.1f %.1f' % (
            x - 90 * s, y - 60 * s, x, y + 4 * s, x + 90 * s, y - 60 * s), 'none', stroke=c, stroke_width=5))
    o.append(L(700, 150, 830, 150, p['dark'], 8))
    o.append(P('M 830 150 l -34 -22 l 0 44 Z', p['dark']))
    o.append(C(180, 380, 16, p['accent'], opacity=0.7))
    o.append(C(820, 380, 20, p['accent'], opacity=0.7))
    return '\n'.join(o)


def sc_shield(p, v):
    o = []
    o.append(bubble(280, 150, 300, 150, '#ffffff', p['main'], 'left'))
    o.append(lines(320, 192, 3, 214, 34, p['soft'], 8))
    o.append(P('M 640 180 L 740 220 L 740 322 C 740 372 640 402 640 402 C 640 402 540 372 540 322 L 540 220 Z',
               p['main']))
    o.append(P('M 640 180 L 740 220 L 740 322 C 740 372 640 402 640 402 Z', p['dark'], opacity=0.25))
    o.append(P('M 596 296 l 34 34 l 74 -76', 'none', stroke='#ffffff', stroke_width=11, stroke_linecap='round'))
    o.append(person(240, GY, 0.8, body=p['accent'], dark='#b25f1c', arms='front'))
    o.append(R(820, 300, 60, 44, p['accent'], 8))
    o.append(P('M 830 300 a 20 20 0 0 1 40 0', 'none', stroke=p['accent'], stroke_width=9))
    return '\n'.join(o)


# ---------------- 场景：生活事物 ----------------
def sc_dog(p, v):
    o = []
    # 身体
    o.append(E(470, 336, 106, 66, p['main']))
    # 头
    o.append(C(620, 268, 62, p['main']))
    o.append(P('M 566 224 L 546 160 L 600 200 Z', p['dark']))
    o.append(P('M 676 224 L 700 160 L 644 200 Z', p['dark']))
    o.append(C(600, 262, 11, '#3b2f28'))
    o.append(C(646, 262, 11, '#3b2f28'))
    o.append(E(622, 296, 22, 16, '#ffffff'))
    o.append(C(622, 296, 10, '#3b2f28'))
    o.append(P('M 622 306 q 14 14 0 20', 'none', stroke='#3b2f28', stroke_width=4))
    # 腿
    for x in (398, 442, 512, 556):
        o.append(R(x, 380, 24, 48, p['dark'], 11))
    # 尾巴
    o.append(P('M 366 320 C 320 300 312 250 340 232', 'none', stroke=p['dark'], stroke_width=18, stroke_linecap='round'))
    # 脚印
    for x in (200, 250, 700, 750):
        o.append(E(x, 400, 16, 12, p['soft']))
        o.append(C(x - 12, 386, 6, p['soft']))
        o.append(C(x, 382, 6, p['soft']))
        o.append(C(x + 12, 386, 6, p['soft']))
    o.append(heart(790, 200, 0.55, '#e05a5a'))
    return '\n'.join(o)


def sc_carrot(p, v):
    o = []
    # 锅
    o.append(P('M 330 300 L 640 300 L 620 420 L 350 420 Z', '#8f9aa4'))
    o.append(E(485, 300, 155, 30, '#a8b3bb'))
    o.append(P('M 640 316 q 60 10 54 52', 'none', stroke='#8f9aa4', stroke_width=14, stroke_linecap='round'))
    # 蒸汽
    for i in range(3):
        o.append(P('M %d 268 c -20 -26 16 -40 -4 -66' % (410 + i * 60), 'none', stroke='#c0cbd2', stroke_width=6))
    # 胡萝卜
    o.append(P('M 250 210 L 300 320 L 272 330 L 226 226 Z', '#e0822f'))
    o.append(P('M 238 210 l -20 -46 l 44 22 Z', '#4e9a52'))
    o.append(P('M 258 212 l 4 -52 l 30 34 Z', '#4e9a52'))
    # 鸡蛋
    o.append(E(480, 236, 40, 50, '#ffffff', stroke=p['soft'], stroke_width=4))
    # 咖啡豆
    o.append(E(690, 232, 34, 24, '#7a4a2b'))
    o.append(P('M 662 232 q 28 -18 56 0', 'none', stroke='#5b3620', stroke_width=5))
    o.append(E(730, 268, 26, 18, '#7a4a2b'))
    o.append(P('M 710 268 q 20 -14 40 0', 'none', stroke='#5b3620', stroke_width=4))
    return '\n'.join(o)


def sc_milk(p, v):
    o = [R(200, 400, 560, 16, p['dark'], 6)]           # 桌面
    # 倾倒的杯子
    o.append('<g transform="rotate(38 400 350)">')
    o.append(R(352, 300, 96, 110, '#ffffff', 10, stroke=p['main'], stroke_width=5))
    o.append(R(352, 340, 96, 70, p['soft'], 8))
    o.append('</g>')
    # 溅出的奶
    o.append(P('M 452 388 C 520 372 560 402 620 384 C 680 366 720 400 780 388 L 780 400 L 452 400 Z', '#ffffff',
               stroke=p['soft'], stroke_width=4))
    o.append(C(600, 356, 16, '#ffffff', stroke=p['soft'], stroke_width=3))
    o.append(C(660, 330, 11, '#ffffff', stroke=p['soft'], stroke_width=3))
    o.append(C(540, 344, 9, '#ffffff', stroke=p['soft'], stroke_width=3))
    # 抹布
    o.append(R(230, 356, 90, 44, p['accent'], 12))
    o.append(L(240, 370, 310, 370, '#ffffff', 5))
    o.append(L(240, 386, 296, 386, '#ffffff', 5))
    return '\n'.join(o)


def sc_clock(p, v):
    o = []
    # 窗户（夜）
    o.append(R(560, 150, 300, 230, '#22344a', 12, stroke=p['dark'], stroke_width=8))
    o.append(C(680, 218, 34, '#f3e6b8'))
    o.append(C(664, 210, 30, p['bg2']))
    for x, y, s in ((760, 196, 0.8), (820, 250, 0.6), (620, 300, 0.5), (790, 320, 0.45)):
        o.append(star(x, y, 16 * s, '#f3e6b8'))
    o.append(L(710, 150, 710, 380, p['dark'], 6))
    o.append(L(560, 265, 860, 265, p['dark'], 6))
    # 时钟
    o.append(C(290, 268, 110, '#ffffff', stroke=p['main'], stroke_width=9))
    o.append(C(290, 268, 92, p['soft'], opacity=0.35))
    for i in range(12):
        import math
        a = i * math.pi / 6
        o.append(L(290 + 84 * math.sin(a), 268 - 84 * math.cos(a),
                   290 + 94 * math.sin(a), 268 - 94 * math.cos(a), p['dark'], 5))
    o.append(L(290, 268, 290, 200, p['main'], 9))
    o.append(L(290, 268, 344, 292, p['accent'], 7))
    o.append(C(290, 268, 9, p['dark']))
    o.append(R(266, 176, 48, 16, p['dark'], 5))
    # 台面
    o.append(R(140, 400, 780, 14, p['dark'], 6))
    return '\n'.join(o)


def sc_noarms(p, v):
    o = [person(470, GY, 1.1, body=p['main'], dark=p['dark'], arms='none', hair='#4a3b32')]
    # 翅膀
    o.append(P('M 400 300 C 320 280 280 320 300 372 C 340 356 372 340 400 330 Z', p['accent'], opacity=0.9))
    o.append(P('M 540 300 C 620 280 660 320 640 372 C 600 356 568 340 540 330 Z', p['accent'], opacity=0.9))
    o.append(heart(700, 190, 0.7, '#e05a5a'))
    o.append(heart(250, 210, 0.55, '#e05a5a'))
    for i in range(6):
        import math
        a = math.pi * (0.15 + i * 0.14)
        o.append(L(470 + 200 * math.cos(a), 200 - 160 * math.sin(a),
                   470 + 232 * math.cos(a), 200 - 186 * math.sin(a), p['accent'], 6))
    return '\n'.join(o)


def sc_photo(p, v):
    o = []
    o.append(R(300, 150, 380, 270, '#ffffff', 10, stroke=p['main'], stroke_width=8))
    # 左半负片（暗）
    o.append(R(314, 164, 176, 242, '#3b4a52', 6))
    o.append(C(400, 250, 42, '#6b7b8a', opacity=0.8))
    o.append(P('M 340 330 L 400 280 L 470 330 Z', '#55646c'))
    # 右半风景（亮）
    o.append(R(504, 164, 162, 242, p['soft'], 6))
    o.append(C(600, 220, 30, '#f3e6b8'))
    o.append(P('M 504 340 L 570 270 L 630 330 L 666 300 L 666 406 L 504 406 Z', p['accent']))
    o.append(P('M 504 406 L 666 406 L 666 380 L 504 366 Z', p['main']))
    o.append(L(470, 180, 500, 240, p['accent'], 6))
    o.append(P('M 500 240 l -26 4 l 12 -22 Z', p['accent']))
    o.append(R(390, 420, 200, 14, p['dark'], 6))
    return '\n'.join(o)


def sc_violin(p, v):
    o = []
    # 卷轴琴头 + 指板
    o.append(R(432, 148, 36, 34, p['dark'], 10))
    o.append(C(428, 152, 12, p['dark']))
    o.append(C(468, 148, 12, p['dark']))
    o.append(R(440, 178, 22, 118, p['dark'], 8))
    # 琴身：上小下大双椭圆 + 腰
    o.append(E(450, 306, 80, 58, p['main']))
    o.append(E(450, 378, 98, 70, p['main']))
    o.append(P('M 386 318 q 34 26 0 52', 'none', stroke=p['bg2'], stroke_width=10))
    o.append(P('M 514 318 q -34 26 0 52', 'none', stroke=p['bg2'], stroke_width=10))
    # f 孔
    o.append(L(408, 300, 402, 352, p['dark'], 6))
    o.append(L(492, 300, 498, 352, p['dark'], 6))
    # 弦 + 拉弦板
    for dx in (-7, 0, 7):
        o.append(L(450 + dx, 190, 450 + dx, 392, '#ffffff', 3))
    o.append(E(450, 404, 26, 16, p['dark']))
    # 弓
    o.append('<g transform="rotate(-36 700 320)">')
    o.append(L(560, 320, 840, 320, '#a9744f', 9))
    o.append(L(566, 306, 834, 306, p['soft'], 4))
    o.append(R(546, 300, 22, 40, p['dark'], 6))
    o.append('</g>')
    # 音符
    for x, y, s in ((700, 170, 1.0), (780, 230, 0.72), (300, 200, 0.6)):
        o.append(C(x, y + 26 * s, 13 * s, p['accent']))
        o.append(R(x + 10 * s, y - 34 * s, 5 * s, 58 * s, p['accent'], 2))
        o.append(P('M %d %d q 34 %d 34 %d' % (x + 15 * s, y - 34 * s, 10 * s, 22 * s), 'none',
                   stroke=p['accent'], stroke_width=5 * s))
    return '\n'.join(o)


def sc_rocket(p, v):
    o = []
    if v == 'castle':
        for x, w, h in ((300, 90, 150), (400, 120, 210), (540, 90, 150)):
            o.append(R(x, GY - h, w, h, p['main'], 6))
            for i in range(3):
                o.append(P('M %d %d L %d %d L %d %d Z' % (
                    x + i * w / 3, GY - h, x + w / 6 + i * w / 3, GY - h - 40, x + (i + 1) * w / 3, GY - h), p['dark']))
        o.append(P('M 400 %d L 460 %d L 460 %d L 400 %d Z' % (GY - 300, GY - 380, GY - 300, GY - 300), p['accent']))
        o.append(P('M 460 %d L 520 %d L 520 %d L 460 %d Z' % (GY - 300, GY - 360, GY - 300, GY - 300), p['accent']))
        for i in range(4):
            o.append(R(430 + i * 30, GY - 160, 18, 26, '#f3e6b8', 4))
        for x, y, s in ((680, 150, 1.0), (760, 210, 0.7), (240, 200, 0.6)):
            o.append(star(x, y, 22 * s, p['accent']))
        o.append(C(820, 300, 12, p['accent'], opacity=0.7))
    else:
        o.append(P('M 480 150 C 540 200 546 300 540 360 L 420 360 C 414 300 420 200 480 150 Z', p['main']))
        o.append(P('M 480 150 C 540 200 546 300 540 360 L 480 360 Z', p['dark'], opacity=0.25))
        o.append(C(480, 268, 34, '#eaf6fb', stroke=p['dark'], stroke_width=5))
        o.append(P('M 420 300 L 386 380 L 420 362 Z', p['accent']))
        o.append(P('M 540 300 L 574 380 L 540 362 Z', p['accent']))
        o.append(P('M 440 360 q 40 70 80 0 q -40 34 -80 0 Z', p['accent']))
        o.append(C(480, 396, 16, '#f3e6b8'))
        for i in range(4):
            o.append(C(420 + i * 40, 420 + (i % 2) * 18, 20 - i * 3, p['soft'], opacity=0.75))
        for x, y, s in ((700, 160, 0.9), (270, 190, 0.7), (760, 260, 0.55)):
            o.append(star(x, y, 22 * s, p['accent']))
        o.append(cloud(230, 320, 0.85, '#ffffff', 0.85))
        o.append(cloud(760, 340, 0.7, '#ffffff', 0.8))
    return '\n'.join(o)


def sc_columns(p, v):
    o = []
    for x in (300, 480, 660):
        o.append(R(x - 40, 210, 80, 190, p['main'], 4))
        o.append(R(x - 52, 190, 104, 26, p['main'], 4))
        for i in range(4):
            o.append(R(x - 24 + i * 16, 220, 8, 170, p['dark'], 2, opacity=0.55))
    o.append(P('M 220 400 L 740 400 L 780 430 L 180 430 Z', p['soft']))
    o.append(P('M 240 190 L 720 190 L 700 158 L 260 158 Z', p['dark']))
    o.append(R(430, 320, 100, 80, '#ffffff', 6, stroke=p['accent'], stroke_width=5))
    o.append(P('M 456 340 l 22 24 l 46 -48', 'none', stroke=p['accent'], stroke_width=8, stroke_linecap='round'))
    o.append(star(480, 118, 20, p['accent']))
    return '\n'.join(o)


def sc_apple(p, v):
    o = []
    o.append(P('M 470 190 C 520 150 600 168 604 224 C 660 236 668 330 620 372 '
               'C 580 410 520 404 486 380 C 452 404 392 410 352 372 '
               'C 304 330 312 236 368 224 C 372 168 420 150 470 190 Z', p['main']))
    o.append(P('M 604 224 C 640 210 660 216 668 226 C 656 240 630 244 612 238 Z', '#4e9a52'))
    o.append(P('M 470 190 C 480 160 500 148 512 148 C 508 172 492 186 470 190 Z', '#4e9a52'))
    o.append(C(536, 250, 26, p['bg1'], opacity=0.55))
    o.append(person(220, GY, 0.85, body=p['accent'], dark='#b25f1c', arms='front', hair='#3b2f28'))
    o.append(person(760, GY, 0.85, body=p['soft'], dark=p['main'], arms='front'))
    for x, y, s in ((700, 160, 0.8), (200, 170, 0.6), (800, 240, 0.5)):
        o.append(star(x, y, 20 * s, p['accent']))
    return '\n'.join(o)


def sc_oldman(p, v):
    o = [person(380, GY, 1.15, body=p['main'], dark=p['dark'], arms='front', hair='#dcd6cf')]
    # 胡子
    o.append(P('M 340 300 q 40 46 80 0 q -40 22 -80 0 Z', '#dcd6cf'))
    o.append(C(356, 282, 8, '#3b2f28'))
    o.append(C(404, 282, 8, '#3b2f28'))
    o.append(P('M 356 296 q 24 18 48 0', 'none', stroke='#3b2f28', stroke_width=4))
    # 花盆 / 花
    o.append(R(600, 356, 90, 72, p['accent'], 8))
    o.append(P('M 645 356 L 645 290', 'none', stroke='#4e9a52', stroke_width=7))
    o.append(C(645, 276, 20, '#e05a5a'))
    o.append(C(645, 276, 8, '#f3e6b8'))
    o.append(P('M 645 320 q -30 -16 -34 -44', 'none', stroke='#4e9a52', stroke_width=6))
    o.append(C(608, 268, 13, p['accent']))
    # 鸟
    for x, y, s in ((760, 190, 1.0), (830, 240, 0.7)):
        o.append(P('M %d %d q 18 -18 36 0 q 18 -18 36 0' % (x, y), 'none', stroke=p['dark'], stroke_width=5 * s))
    o.append(heart(250, 190, 0.55, '#e05a5a'))
    o.append(tree(150, GY, 0.7, '#a9744f', p['soft']))
    return '\n'.join(o)


def sc_billboard(p, v):
    o = []
    o.append(R(300, 160, 380, 180, '#ffffff', 8, stroke=p['main'], stroke_width=6))
    o.append(R(320, 180, 340, 60, p['main'], 6))
    o.append(R(336, 196, 180, 12, '#ffffff', 6, opacity=0.85))
    o.append(R(336, 218, 120, 10, '#ffffff', 5, opacity=0.7))
    o.append(C(600, 216, 30, p['accent']))
    o.append(R(320, 264, 200, 12, p['soft'], 6))
    o.append(R(320, 292, 260, 12, p['soft'], 6))
    o.append(R(320, 318, 150, 12, p['soft'], 6))
    o.append(R(400, 340, 14, 90, p['dark'], 5))
    o.append(R(566, 340, 14, 90, p['dark'], 5))
    o.append(person(200, GY, 0.72, body=p['soft'], dark=p['main'], arms='down'))
    o.append(person(750, GY, 0.78, body=p['accent'], dark='#b25f1c', arms='down'))
    o.append(R(120, 424, 720, 12, p['dark'], 6))
    return '\n'.join(o)


SCENES = {
    'speech': sc_speech, 'book': sc_book, 'office': sc_office, 'crowd': sc_crowd,
    'stairs': sc_stairs, 'car': sc_car, 'two': sc_two, 'date': sc_date,
    'baby': sc_baby, 'calendar': sc_calendar, 'mirror': sc_mirror, 'stress': sc_stress,
    'think': sc_person_think, 'smile': sc_smile, 'money': sc_money, 'chart': sc_chart,
    'sprout': sc_sprout, 'signpost': sc_signpost, 'town': sc_town, 'internet': sc_internet,
    'laptop': sc_laptop, 'tv': sc_tv, 'email': sc_email, 'shield': sc_shield,
    'dog': sc_dog, 'carrot': sc_carrot, 'milk': sc_milk, 'clock': sc_clock,
    'noarms': sc_noarms, 'photo': sc_photo, 'violin': sc_violin, 'rocket': sc_rocket,
    'columns': sc_columns, 'apple': sc_apple, 'oldman': sc_oldman, 'billboard': sc_billboard,
}

# ---------------- 篇目 → 插画配置 ----------------
# (场景, 调色板, 变体)
MAP = {
    'Y01': ('speech', 'mint', ''),
    'Y02': ('book', 'blue', 'open'),
    'Y03': ('speech', 'teal', ''),
    'Y04': ('office', 'blue', 'desk'),
    'Y05': ('crowd', 'violet', ''),
    'Y06': ('stairs', 'warm', 'up'),
    'Y07': ('stairs', 'mint', 'fall'),
    'Y08': ('stairs', 'blue', 'up'),
    'Y09': ('car', 'warm', 'car'),
    'Y10': ('two', 'mint', 'heart'),
    'Y11': ('two', 'warm', 'gloves'),
    'Y12': ('two', 'blue', 'heart'),
    'Y13': ('baby', 'warm', ''),
    'Y14': ('calendar', 'blue', ''),
    'Y15': ('office', 'warm', 'heart'),
    'Y16': ('signpost', 'violet', 'choice'),
    'Y17': ('date', 'warm', ''),
    'Y18': ('signpost', 'mint', 'purpose'),
    'Y19': ('oldman', 'mint', ''),
    'Y20': ('rocket', 'violet', 'castle'),
    'Y21': ('money', 'mint', 'coins'),
    'Y22': ('money', 'warm', 'child'),
    'Y23': ('book', 'teal', 'stack'),
    'Y24': ('money', 'violet', 'scales'),
    'Y25': ('speech', 'warm', ''),
    'Y26': ('think', 'violet', 'voice'),
    'Y27': ('smile', 'warm', ''),
    'Y28': ('chart', 'blue', 'bar'),
    'Y29': ('sprout', 'mint', 'seed'),
    'Y30': ('think', 'violet', 'star'),
    'Y31': ('columns', 'violet', ''),
    'Y32': ('apple', 'blue', ''),
    'Y33': ('email', 'blue', ''),
    'Y34': ('carrot', 'warm', ''),
    'Y35': ('office', 'violet', 'shadow'),
    'Y36': ('stairs', 'warm', 'heavy'),
    'Y37': ('shield', 'blue', ''),
    'Y38': ('car', 'mint', 'green'),
    'Y39': ('car', 'teal', 'compare'),
    'Y40': ('town', 'warm', ''),
    'Y41': ('money', 'mint', 'piggy'),
    'Y42': ('billboard', 'warm', ''),
    'Y43': ('internet', 'violet', 'globe'),
    'Y44': ('internet', 'warm', 'hearts'),
    'Y45': ('laptop', 'teal', 'elder'),
    'Y46': ('tv', 'blue', ''),
    'Y47': ('town', 'mint', ''),
    'Y48': ('stress', 'violet', ''),
    'Y49': ('mirror', 'blue', 'compare'),
    'Y50': ('mirror', 'teal', 'self'),
    'Y51': ('dog', 'warm', ''),
    'B一A': ('book', 'mint', 'magnifier'),
    'B一B': ('speech', 'violet', ''),
    'B二A': ('milk', 'warm', ''),
    'B二B': ('clock', 'violet', ''),
    'B三A': ('two', 'mint', 'shield'),
    'B三B': ('two', 'warm', 'back'),
    'B四A': ('office', 'warm', 'heart'),
    'B四B': ('rocket', 'mint', 'rocket'),
    'B五A': ('stairs', 'blue', 'heavy'),
    'B五B': ('sprout', 'warm', 'sunrise'),
    'B六A': ('money', 'mint', 'child'),
    'B六B': ('money', 'blue', 'scales'),
    'B七A': ('think', 'teal', 'voice'),
    'B七B': ('two', 'violet', 'handshake'),
    'B八A': ('noarms', 'mint', ''),
    'B八B': ('apple', 'violet', ''),
    'B九A': ('photo', 'warm', ''),
    'B九B': ('violin', 'violet', ''),
    'B十A': ('car', 'mint', 'bus'),
    'B十B': ('car', 'teal', 'bus'),
    'B十一A': ('internet', 'warm', 'hearts'),
    'B十一B': ('internet', 'blue', 'people'),
    'B十二A': ('calendar', 'warm', ''),
    'B十二B': ('mirror', 'violet', 'body'),
}


def build(pid, scene, pal, variant, title):
    title = (title.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))
    p = PALETTES[pal]
    seed = sum(ord(c) for c in pid)
    rnd = random.Random(seed)
    g = []
    g.append('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
             '</linearGradient></defs>' % (p['bg1'], p['bg2']))
    g.append('<rect width="%d" height="%d" fill="url(#bg)"/>' % (W, H))
    # 装饰圆
    g.append(C(rnd.randint(700, 880), rnd.randint(90, 160), rnd.randint(28, 52), p['soft'], opacity=0.55))
    g.append(C(rnd.randint(80, 200), rnd.randint(110, 200), rnd.randint(20, 40), p['soft'], opacity=0.45))
    g.append(C(rnd.randint(780, 900), rnd.randint(330, 400), rnd.randint(16, 30), p['accent'], opacity=0.28))
    # 云
    g.append(cloud(rnd.randint(180, 300), rnd.randint(96, 130), rnd.uniform(0.8, 1.1), '#ffffff', 0.85))
    g.append(cloud(rnd.randint(620, 780), rnd.randint(110, 150), rnd.uniform(0.7, 0.95), '#ffffff', 0.8))
    # 地面
    g.append(P('M 0 434 C 220 410 380 448 560 430 C 720 414 840 442 960 424 L 960 540 L 0 540 Z',
               p['soft'], opacity=0.75))
    g.append(P('M 0 434 C 220 410 380 448 560 430 C 720 414 840 442 960 424', 'none',
               stroke=p['main'], stroke_width=3, opacity=0.35))
    # 主体
    g.append(SCENES[scene](p, variant))
    # 前景草丛
    for _ in range(3):
        x = rnd.randint(60, 900)
        g.append(P('M %d 540 q 10 -26 22 -4 q 12 -30 24 4' % x, 'none',
                   stroke=p['main'], stroke_width=5, opacity=0.35, stroke_linecap='round'))
    inner = '\n'.join(g)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s">\n<title>%s</title>\n%s\n</svg>\n'
            % (W, H, W, H, title, title, inner))


def main():
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    ids = args if args else list(MAP.keys())
    n = 0
    for pid in ids:
        if pid not in MAP:
            print('跳过（无配置）:', pid)
            continue
        scene, pal, var = MAP[pid]
        title = TITLES.get(pid, pid)
        svg = build(pid, scene, pal, var, title)
        with open(os.path.join(OUT, pid + '.svg'), 'w', encoding='utf-8') as f:
            f.write(svg)
        n += 1
    print('生成插图 %d 张 → %s' % (n, OUT))

    # 写回 passages.json
    d = json.load(open(DATA, encoding='utf-8'))
    for psg in d['passages']:
        pid = psg['id']
        if os.path.exists(os.path.join(OUT, pid + '.svg')):
            psg['img'] = 'assets/img/%s.svg' % pid
    json.dump(d, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False)
    miss = [p['id'] for p in d['passages'] if 'img' not in p]
    print('passages.json 已写入 img 字段；缺图篇目：', miss or '无')


# 篇目中文主题（用于 SVG title / alt）
TITLES = {}


def load_titles():
    d = json.load(open(DATA, encoding='utf-8'))
    for p in d['passages']:
        TITLES[p['id']] = p.get('topic') or p.get('title') or p['id']


if __name__ == '__main__':
    load_titles()
    main()
