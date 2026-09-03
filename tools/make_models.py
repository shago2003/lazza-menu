# -*- coding: utf-8 -*-
"""
LAZZA — сборка 3D-моделей блюд для AR-меню.

Запуск:   python tools/make_models.py
Результат: models/*.glb — по одной модели на позицию меню.

Каждое блюдо собирается из примитивов (glbkit.py) в натуральную величину,
в метрах. Хотите заменить стилизованную модель на фотоскан настоящего блюда —
положите свой .glb с тем же именем в models/, код трогать не нужно.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glbkit import (M, P, OUT, RND, TAU, box, copy, cyl, dome, helix, lathe, leaf,
                    mv, rotx, roty, rotz, save, sc, slab, sphere, torus, wedge)

D2R = math.pi / 180.0

# ============================================================
#   ПАЛИТРА ПРОДУКТОВ
# ============================================================

BUN        = M('#cf9448', 0.78)
BUN_DARK   = M('#b8763c', 0.80)
SESAME     = M('#f2e3c4', 0.65)
BEEF       = M('#5a3722', 0.85)
BEEF_CHAR  = M('#3a2213', 0.88)
CHICKEN    = M('#d99a4e', 0.82)
CHEDDAR    = M('#e8961f', 0.55)
SMOKED     = M('#e6c163', 0.58)
LETTUCE    = M('#5c9c3c', 0.62, double=True)
ROCKET     = M('#3f6d2b', 0.62, double=True)
TOMATO     = M('#d4402a', 0.55)
SUNDRIED   = M('#9c2c1b', 0.62)
PICKLE     = M('#7ea23a', 0.55)
ONION      = M('#a4608a', 0.60)
BACON      = M('#b0452c', 0.66, double=True)
SAUCE      = M('#e2b143', 0.45)
BBQ        = M('#7d2a19', 0.45)
TRUFFLE    = M('#efe3c8', 0.45)

POTATO     = M('#e8b34a', 0.72)
POTATO_TIP = M('#f3cd78', 0.70)
POTATO_SK  = M('#b9793a', 0.78)
BATTER     = M('#dda45e', 0.74)
CARTON_RED = M('#cf432b', 0.68)
CARTON_KR  = M('#c39a66', 0.76)
PAPER      = M('#f2ead8', 0.85)

CERAMIC    = M('#f6f1e8', 0.35)
CERAMIC_D  = M('#241a15', 0.35)
ESPRESSO   = M('#2a1508', 0.30)
CREMA      = M('#8a5a2b', 0.40)
FOAM       = M('#f5ece0', 0.60)
LATTE      = M('#c9a077', 0.35)
MILK       = M('#f7f1e6', 0.40)
COCOA_DUST = M('#6b3b22', 0.75)

PLASTIC    = M('#ffffff', 0.12, alpha=0.26, double=True)
GLASS      = M('#eaf4f7', 0.08, alpha=0.24, double=True)
ICE        = M('#dcf0f6', 0.10, alpha=0.45)
STRAW_R    = M('#cf432b', 0.35)
STRAW_A    = M('#e9a23b', 0.35)

COLD_BREW  = M('#38200f', 0.30)
MATCHA     = M('#7cbc5c', 0.35)
COCOA      = M('#6b3b22', 0.40)
MARSH      = M('#faf3ea', 0.70)
TEA        = M('#c06a1e', 0.25)
LEMON      = M('#f2d24a', 0.30)
LEMON_RIND = M('#f5e07a', 0.55)
BERRY_LIQ  = M('#cf4468', 0.30)
BERRY      = M('#a82a52', 0.45)
ORANGE     = M('#f0871e', 0.30)
COLA       = M('#3a1b0d', 0.20)
SMOOTHIE   = M('#e0587e', 0.40)
SHAKE      = M('#f0e2d0', 0.45)
CREAM      = M('#fffaf2', 0.50)
CHERRY     = M('#c8202a', 0.30)
MINT       = M('#4f9e46', 0.55, double=True)

CAKE       = M('#f5e6c8', 0.55)
CRUST      = M('#8a5a30', 0.78)
BROWNIE    = M('#42200f', 0.72)
BROWNIE_TOP= M('#6b3826', 0.66)
CROISSANT  = M('#dda54e', 0.70)
CROIS_DARK = M('#c07f33', 0.72)
PANCAKE    = M('#e0a95a', 0.74)
SYRUP      = M('#9c5418', 0.28)
BUTTER     = M('#f5d878', 0.50)
PLATE      = M('#f7f2e7', 0.32)
TRAY       = M('#b98f5e', 0.80)

# ============================================================
#   ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def blob(rx, ry, rz, mat, seg=14, rings=8):
    """Эллипсоид с центром в начале координат."""
    p = sphere(1.0, mat, seg, rings)
    mv(p, 0, -1.0, 0)
    return sc(p, rx, ry, rz)

def scatter(build, n, rmax, y, spread=0.0):
    """n объектов по кругу радиуса rmax на высоте y, со случайным поворотом."""
    out = []
    for i in range(n):
        a = TAU * i / n + RND.uniform(-0.3, 0.3)
        r = rmax * math.sqrt(RND.uniform(0.05, 1.0))
        p = build(i)
        if spread:
            rotx(p, RND.uniform(-spread, spread))
            rotz(p, RND.uniform(-spread, spread))
        roty(p, RND.uniform(0, TAU))
        mv(p, r * math.cos(a), y, r * math.sin(a))
        out += p
    return out

# ============================================================
#   БУРГЕРЫ
# ============================================================

def burger(patty=BEEF, patties=1, cheese=CHEDDAR, green=LETTUCE, sauce=SAUCE,
           bacon=False, tomato=None, onion=True, sesame=True, R=0.058):
    parts = []
    y = 0.0

    # нижняя булка
    parts += lathe([(R * 0.80, 0.0), (R * 0.95, 0.005), (R, 0.014), (R * 0.99, 0.024)],
                   BUN, 34)
    y = 0.024

    # соус
    parts += mv(cyl(R * 0.86, 0.003, sauce, 30), 0, y, 0)
    y += 0.003

    if onion:
        for k in range(2):
            parts += mv(torus(R * 0.62, 0.0035, ONION, 22, 8), 0, y + k * 0.002, 0)
        y += 0.006

    if green is not None:
        parts += mv(leaf(R * 1.04, green), 0, y + 0.004, 0)
        y += 0.010

    if tomato is not None:
        parts += mv(cyl(R * 0.76, 0.006, tomato, 26), 0, y, 0)
        y += 0.006

    for i in range(patties):
        parts += mv(lathe([(R * 0.86, 0.0), (R * 0.93, 0.004),
                           (R * 0.93, 0.013), (R * 0.84, 0.017)], patty, 32), 0, y, 0)
        parts += mv(lathe([(R * 0.86, 0.0), (R * 0.93, 0.0015)], BEEF_CHAR, 32), 0, y, 0)
        y += 0.017
        if cheese is not None:
            sl = slab(R * 1.52, R * 1.52, cheese, th=0.0022, droop=0.009, seg=7)
            roty(sl, 42 * D2R)
            parts += mv(sl, 0, y + 0.002, 0)
            y += 0.004

    if bacon:
        for k in range(3):
            st = slab(R * 1.55, 0.020, BACON, th=0.002, droop=0.008, seg=6)
            roty(st, (k * 34 - 34) * D2R)
            parts += mv(st, 0, y + k * 0.0015, 0)
        y += 0.008

    # верхняя булка
    top = dome(R, 0.040, BUN, 34, 10)
    parts += mv(top, 0, y, 0)
    if sesame:
        for _ in range(16):
            th = RND.uniform(0.22, 1.15)
            ph = RND.uniform(0, TAU)
            s = blob(0.0035, 0.0013, 0.0024, SESAME, 10, 6)
            roty(s, ph)
            mv(s, R * math.sin(th) * math.cos(ph) * 0.97,
               y + 0.040 * math.cos(th) + 0.0006,
               R * math.sin(th) * math.sin(ph) * 0.97)
            parts += s
    return parts

# ============================================================
#   ФРИ И ЗАКУСКИ
# ============================================================

def carton(mat, h=0.088, rb=0.048, rt=0.072):
    p = lathe([(rb, 0.0), (rb * 1.06, 0.014), (rt, h)], mat, 4, smooth=False, cap_top=False)
    return roty(p, 45 * D2R)

def fries(mat=CARTON_RED, n=24, thick=0.0075, length=0.085, skin=False, cheese=False):
    parts = carton(mat)
    for i in range(n):
        L = length * RND.uniform(0.78, 1.15)
        st = box(thick, L, thick * RND.uniform(0.9, 1.25), POTATO)
        st += mv(box(thick, 0.006, thick, POTATO_TIP), 0, L - 0.006, 0)
        if skin:
            st += mv(box(thick * 1.02, 0.004, thick * 1.02, POTATO_SK), 0, L * 0.5, 0)
        mv(st, 0, -0.02, 0)
        rotx(st, RND.uniform(-0.30, 0.30))
        rotz(st, RND.uniform(-0.30, 0.30))
        roty(st, RND.uniform(0, TAU))
        a = TAU * i / n
        r = 0.030 * math.sqrt(RND.uniform(0.02, 1.0))
        mv(st, r * math.cos(a), 0.070 + RND.uniform(0.0, 0.012), r * math.sin(a))
        parts += st
    if cheese:
        for _ in range(9):
            a = RND.uniform(0, TAU)
            r = RND.uniform(0.0, 0.030)
            parts += mv(blob(0.014, 0.005, 0.012, CHEDDAR, 12, 7),
                        r * math.cos(a), 0.128 + RND.uniform(-0.01, 0.02), r * math.sin(a))
    return parts

def tray(w=0.155, d=0.115, h=0.010, mat=PAPER):
    return lathe([(0.052, 0.0), (0.060, h)], mat, 4, smooth=False, cap_top=False) \
        if False else roty(lathe([(w * 0.40, 0.0), (w * 0.46, h)], mat, 4,
                                 smooth=False, cap_top=False), 45 * D2R)

def onion_rings():
    parts = tray(mat=CARTON_KR)
    for i in range(6):
        r = torus(0.033 - i * 0.0015, 0.0105, BATTER, 24, 10)
        if i < 3:
            mv(r, RND.uniform(-0.022, 0.022), 0.010 + i * 0.021, RND.uniform(-0.012, 0.012))
        else:
            rotx(r, 78 * D2R)
            roty(r, RND.uniform(0, TAU))
            mv(r, RND.uniform(-0.030, 0.030), 0.040, RND.uniform(-0.015, 0.015))
        parts += r
    return parts

def bites(n=6, rx=0.023, ry=0.011, rz=0.018):
    parts = tray(mat=PAPER)
    return parts + scatter(lambda i: blob(rx * RND.uniform(0.9, 1.1), ry,
                                          rz * RND.uniform(0.9, 1.1), BATTER, 14, 8),
                           n, 0.032, 0.010 + ry, spread=0.35)

# ============================================================
#   ГОРЯЧИЕ НАПИТКИ
# ============================================================

def saucer(r=0.058):
    return lathe([(0.0, 0.004), (r * 0.55, 0.0035), (r * 0.94, 0.004),
                  (r, 0.008), (r * 0.97, 0.009), (r * 0.5, 0.006), (0.0, 0.006)],
                 CERAMIC, 34, cap_bottom=False, cap_top=False)

def ceramic_cup(rt=0.041, rb=0.029, h=0.072, liquid=ESPRESSO, foam=None,
                dust=False, art=False, cup=CERAMIC, plate=True, handle=True):
    parts = saucer(rt + 0.020) if plate else []
    base = 0.008 if plate else 0.0
    wall = 0.0028
    cupp = lathe([(0.0, 0.0), (rb, 0.0), (rb * 1.04, 0.004), (rt, h), (rt - wall, h),
                  (rb * 0.90, 0.006), (0.0, 0.006)], cup, 34,
                 cap_bottom=False, cap_top=False)
    parts += mv(cupp, 0, base, 0)
    if handle:
        hd = torus(0.019, 0.0048, cup, 22, 9)
        rotx(hd, 90 * D2R)
        parts += mv(hd, rt * 0.86, base + h * 0.50, 0)
    top = h - 0.008
    liq = lathe([(rb * 0.88, 0.006), (rt - wall - 0.001, top)], liquid, 32, cap_bottom=False)
    parts += mv(liq, 0, base, 0)
    if foam is not None:
        parts += mv(dome(rt - wall - 0.001, 0.008, foam, 32, 6, cap=False), 0, base + top, 0)
        top += 0.006
    if art:
        parts += mv(cyl((rt - wall) * 0.52, 0.0012, MILK, 26), 0, base + top + 0.0005, 0)
    if dust:
        parts += mv(cyl((rt - wall) * 0.72, 0.0008, COCOA_DUST, 26), 0, base + top + 0.0018, 0)
    return parts

def mug(liquid=COCOA, marsh=True):
    parts = ceramic_cup(rt=0.043, rb=0.038, h=0.092, liquid=liquid,
                        cup=CERAMIC_D, plate=False, handle=True)
    if marsh:
        for _ in range(7):
            a = RND.uniform(0, TAU)
            r = RND.uniform(0.0, 0.026)
            parts += mv(cyl(0.007, 0.008, MARSH, 12),
                        r * math.cos(a), 0.085, r * math.sin(a))
    return parts

# ============================================================
#   ХОЛОДНЫЕ НАПИТКИ
# ============================================================

def straw(mat=STRAW_R, h=0.155, r=0.0042, tilt=13):
    s = cyl(r, h, mat, 12)
    return rotz(s, tilt * D2R)

def ice_cubes(n, rmax, y0, y1, size=0.013):
    out = []
    for _ in range(n):
        c = box(size, size, size, ICE)
        mv(c, 0, -size / 2, 0)
        rotx(c, RND.uniform(0, TAU))
        roty(c, RND.uniform(0, TAU))
        a = RND.uniform(0, TAU)
        r = RND.uniform(0.0, rmax)
        out += mv(c, r * math.cos(a), RND.uniform(y0, y1), r * math.sin(a))
    return out

def cold_cup(liquid, second=None, ice=5, straw_mat=STRAW_R, h=0.135,
             rb=0.031, rt=0.043, dome_lid=False, cream=False, cherry=False):
    parts = lathe([(rb, 0.0), (rb * 1.05, 0.006), (rt, h)], PLASTIC, 32, cap_top=False)
    fill = h * 0.86
    if second is not None:
        cut = fill * 0.52
        parts += lathe([(rb * 0.93, 0.004), (rb * 0.99 + (rt - rb) * cut / h, cut)],
                       second, 30, cap_bottom=False)
        parts += lathe([(rb * 0.99 + (rt - rb) * cut / h, cut),
                        (rb * 0.95 + (rt - rb) * fill / h, fill)], liquid, 30,
                       cap_bottom=False)
    else:
        parts += lathe([(rb * 0.93, 0.004), (rb * 0.95 + (rt - rb) * fill / h, fill)],
                       liquid, 30, cap_bottom=False)
    if ice:
        parts += ice_cubes(ice, rt * 0.62, fill * 0.35, fill - 0.012)
    if cream:
        parts += mv(helix(0.030, 0.004, 0.045, CREAM, 2.4, 56, 0.013), 0, fill - 0.004, 0)
    if cherry:
        parts += mv(sphere(0.010, CHERRY, 14, 8), 0, fill + 0.040, 0)
    if dome_lid:
        parts += mv(dome(rt, 0.030, PLASTIC, 32, 7, cap=False), 0, h, 0)
    if straw_mat is not None:
        parts += mv(straw(straw_mat, h * 1.25), 0, h * 0.30, 0)
    return parts

def glass_drink(liquid, garnish=None, h=0.125, rb=0.030, rt=0.036,
                ice=4, straw_mat=None, foam=None):
    parts = lathe([(0.0, 0.0), (rb, 0.0), (rb * 1.04, 0.006), (rt, h), (rt - 0.002, h),
                   (rb * 0.92, 0.008), (0.0, 0.008)], GLASS, 32,
                  cap_bottom=False, cap_top=False)
    fill = h * 0.84
    parts += lathe([(rb * 0.90, 0.008), (rt * 0.96, fill)], liquid, 30, cap_bottom=False)
    if ice:
        parts += ice_cubes(ice, rt * 0.55, fill * 0.4, fill - 0.010)
    if foam is not None:
        parts += mv(cyl(rt * 0.95, 0.006, foam, 30), 0, fill, 0)
    if garnish == 'lemon':
        sl = cyl(0.022, 0.004, LEMON_RIND, 20)
        rotx(sl, 88 * D2R)
        parts += mv(sl, rt * 0.86, fill + 0.012, 0)
        parts += mv(leaf(0.016, MINT), 0.004, fill + 0.004, 0.012)
    elif garnish == 'orange':
        sl = cyl(0.024, 0.004, ORANGE, 20)
        rotx(sl, 88 * D2R)
        parts += mv(sl, rt * 0.84, fill + 0.014, 0)
    elif garnish == 'berry':
        for i in range(5):
            a = TAU * i / 5
            parts += mv(sphere(0.008, BERRY, 12, 7),
                        0.018 * math.cos(a), fill - 0.004, 0.018 * math.sin(a))
        parts += mv(leaf(0.016, MINT), 0.0, fill + 0.006, 0.010)
    if straw_mat is not None:
        parts += mv(straw(straw_mat, h * 1.3), 0, h * 0.28, 0)
    return parts

def armudu():
    """Армуду — азербайджанский грушевидный стакан для чая, на блюдце."""
    prof = [(0.0, 0.0), (0.016, 0.0), (0.018, 0.004), (0.020, 0.012),
            (0.031, 0.030), (0.033, 0.044), (0.026, 0.060), (0.021, 0.070),
            (0.026, 0.084), (0.030, 0.092)]
    parts = saucer(0.052)
    outer = lathe(prof, GLASS, 30, cap_bottom=False, cap_top=False)
    parts += mv(outer, 0, 0.008, 0)
    inner = [(r * 0.90, y + 0.004) for (r, y) in prof if r > 0.001]
    parts += mv(lathe([(0.0, 0.006)] + inner[:-1], TEA, 28, cap_bottom=False,
                      cap_top=True), 0, 0.008, 0)
    return parts

def bottle(liquid=COLA, label=M('#cf432b', 0.5)):
    prof = [(0.0, 0.0), (0.031, 0.0), (0.033, 0.006), (0.033, 0.115),
            (0.030, 0.132), (0.020, 0.158), (0.0135, 0.176), (0.0135, 0.198),
            (0.0155, 0.202), (0.0155, 0.212)]
    parts = lathe(prof, GLASS, 30, cap_top=False)
    parts += lathe([(0.0305, 0.004), (0.0305, 0.140), (0.018, 0.166),
                    (0.0115, 0.190)], liquid, 28)
    parts += mv(cyl(0.0335, 0.042, label, 30), 0, 0.040, 0)
    parts += mv(cyl(0.0165, 0.012, M('#c8b06a', 0.35, metal=0.8), 24), 0, 0.202, 0)
    return parts

# ============================================================
#   ДЕСЕРТЫ
# ============================================================

def cheesecake(berries=False):
    ang = 52 * D2R
    parts = lathe([(0.0, 0.004), (0.072, 0.0035), (0.076, 0.007), (0.040, 0.005),
                   (0.0, 0.005)], PLATE, 32, cap_bottom=False, cap_top=False)
    dx = -0.030   # кусок стоит по центру тарелки, а не у края
    slice_ = mv(wedge(0.066, 0.011, ang, CRUST, 16), 0, 0.007, 0)
    slice_ += mv(wedge(0.066, 0.040, ang, CAKE, 16), 0, 0.018, 0)
    slice_ += mv(wedge(0.066, 0.003, ang, M('#f8f2e2', 0.45), 16), 0, 0.058, 0)
    if berries:
        for i in range(7):
            a = RND.uniform(-ang / 2 + 0.15, ang / 2 - 0.15)
            r = RND.uniform(0.020, 0.055)
            slice_ += mv(sphere(0.008, BERRY, 12, 7),
                         r * math.cos(a), 0.060, r * math.sin(a))
        slice_ += mv(leaf(0.014, MINT), 0.034, 0.062, 0.0)
    parts += mv(slice_, dx, 0, 0)
    return parts

def brownie():
    parts = lathe([(0.0, 0.004), (0.070, 0.0035), (0.074, 0.007), (0.040, 0.005),
                   (0.0, 0.005)], PLATE, 32, cap_bottom=False, cap_top=False)
    parts += mv(box(0.082, 0.030, 0.062, BROWNIE), 0, 0.007, 0)
    parts += mv(box(0.080, 0.004, 0.060, BROWNIE_TOP), 0, 0.036, 0)
    parts += mv(sphere(0.021, M('#f5ece0', 0.5), 18, 10), 0.020, 0.040, 0.006)
    parts += mv(blob(0.030, 0.003, 0.020, SYRUP, 16, 8), -0.020, 0.041, 0.0)
    return parts

def croissant():
    parts = lathe([(0.0, 0.004), (0.068, 0.0035), (0.072, 0.007), (0.038, 0.005),
                   (0.0, 0.005)], PLATE, 32, cap_bottom=False, cap_top=False)
    n = 7
    for i in range(n):
        f = i / (n - 1.0)
        a = (f - 0.5) * 2.1
        taper = 1.0 - 0.62 * abs(f - 0.5) * 2.0
        seg = blob(0.017 * taper + 0.004, 0.017 * taper + 0.004, 0.020, CROISSANT, 14, 8)
        roty(seg, -a)
        R = 0.040
        mv(seg, R * math.sin(a), 0.007 + 0.018 * taper + 0.004,
           R * math.cos(a) - R * 0.72)
        parts += seg
    for i in range(n - 1):
        f = (i + 0.5) / (n - 1.0)
        a = (f - 0.5) * 2.1
        taper = 1.0 - 0.62 * abs(f - 0.5) * 2.0
        gap = blob(0.004, 0.014 * taper + 0.004, 0.019, CROIS_DARK, 10, 7)
        roty(gap, -a)
        mv(gap, 0.040 * math.sin(a), 0.007 + 0.016 * taper + 0.003,
           0.040 * math.cos(a) - 0.0288)
        parts += gap
    return parts

def pancakes():
    parts = lathe([(0.0, 0.004), (0.078, 0.0035), (0.082, 0.007), (0.044, 0.005),
                   (0.0, 0.005)], PLATE, 34, cap_bottom=False, cap_top=False)
    y = 0.007
    for i, r in enumerate((0.058, 0.055, 0.051)):
        d = lathe([(r * 0.96, 0.0), (r, 0.003), (r, 0.010), (r * 0.94, 0.013)],
                  PANCAKE, 32)
        mv(d, RND.uniform(-0.003, 0.003), y, RND.uniform(-0.003, 0.003))
        parts += d
        y += 0.013
    parts += mv(dome(0.046, 0.006, SYRUP, 30, 5, cap=False), 0, y, 0)
    for i in range(5):
        a = TAU * i / 5 + 0.4
        parts += mv(blob(0.006, 0.010, 0.005, SYRUP, 10, 6),
                    0.045 * math.cos(a), y - 0.010, 0.045 * math.sin(a))
    parts += mv(box(0.020, 0.010, 0.020, BUTTER), 0, y + 0.004, 0)
    for i in range(4):
        a = TAU * i / 4 + 0.9
        parts += mv(sphere(0.008, BERRY, 12, 7),
                    0.036 * math.cos(a), y + 0.004, 0.036 * math.sin(a))
    return parts

def milkshake():
    parts = lathe([(0.0, 0.0), (0.020, 0.0), (0.022, 0.006), (0.019, 0.020),
                   (0.033, 0.062), (0.040, 0.120), (0.038, 0.120), (0.031, 0.062),
                   (0.017, 0.022), (0.0, 0.020)], GLASS, 32,
                  cap_bottom=False, cap_top=False)
    parts += lathe([(0.018, 0.020), (0.032, 0.062), (0.038, 0.112)], SHAKE, 30)
    parts += mv(helix(0.026, 0.004, 0.042, CREAM, 2.5, 56, 0.012), 0, 0.110, 0)
    parts += mv(sphere(0.009, CHERRY, 14, 8), 0.002, 0.152, 0.0)
    parts += mv(straw(STRAW_R, 0.150), 0.006, 0.086, 0.004)
    return parts

# ============================================================
#   КОМБО
# ============================================================

def combo(kind='classic'):
    parts = roty(lathe([(0.130, 0.0), (0.140, 0.012)], TRAY, 4, smooth=False,
                       cap_top=False), 45 * D2R)
    base = 0.012

    def place(p, x, z, s=1.0):
        if s != 1.0:
            sc(p, s)
        return mv(p, x, base, z)

    if kind == 'duo':
        parts += place(burger(), -0.055, -0.030, 0.92)
        parts += place(burger(patty=CHICKEN, cheese=SMOKED), 0.055, -0.030, 0.92)
        parts += place(fries(), -0.058, 0.055, 0.80)
        parts += place(fries(), 0.058, 0.055, 0.80)
    elif kind == 'shake':
        parts += place(burger(), -0.048, -0.022, 0.92)
        parts += place(fries(), 0.038, -0.030, 0.82)
        parts += place(milkshake(), 0.052, 0.058, 0.90)
    else:
        parts += place(burger(), -0.048, -0.020, 0.94)
        parts += place(fries(), 0.040, -0.028, 0.84)
        parts += place(cold_cup(COLA, ice=4), 0.052, 0.058, 0.92)
    return parts

# ============================================================
#   КАРТА МЕНЮ: файл -> как собрать
# ============================================================

DISHES = {
    # бургеры
    'burger-classic':   lambda: burger(green=LETTUCE, onion=True),
    'burger-double':    lambda: burger(patties=2, green=None, onion=True, sauce=SAUCE),
    'burger-bacon':     lambda: burger(cheese=SMOKED, bacon=True, tomato=TOMATO,
                                       green=None, sauce=BBQ),
    'burger-chicken':   lambda: burger(patty=CHICKEN, cheese=None, green=LETTUCE,
                                       tomato=TOMATO, sauce=CHEDDAR),
    'burger-cheddar':   lambda: burger(cheese=CHEDDAR, green=None, onion=False,
                                       sauce=SAUCE, tomato=PICKLE),
    'burger-craft':     lambda: burger(green=ROCKET, tomato=SUNDRIED, cheese=None,
                                       sauce=TRUFFLE, sesame=False, R=0.060),
    # фри и закуски
    'fries-classic':    lambda: fries(),
    'fries-cheese':     lambda: fries(cheese=True),
    'fries-rustic':     lambda: fries(mat=CARTON_KR, n=18, thick=0.012,
                                      length=0.070, skin=True),
    'onion-rings':      onion_rings,
    'nuggets':          lambda: bites(6, 0.023, 0.011, 0.019),
    'strips':           lambda: bites(5, 0.040, 0.011, 0.016),
    # кофе
    'espresso':         lambda: ceramic_cup(rt=0.032, rb=0.023, h=0.052,
                                            liquid=ESPRESSO, foam=CREMA),
    'americano':        lambda: ceramic_cup(rt=0.041, rb=0.029, h=0.078,
                                            liquid=ESPRESSO, foam=CREMA),
    'cappuccino':       lambda: ceramic_cup(liquid=LATTE, foam=FOAM, dust=True),
    'latte':            lambda: glass_drink(LATTE, h=0.130, rb=0.032, rt=0.038,
                                            ice=0, foam=FOAM),
    'flat-white':       lambda: ceramic_cup(rt=0.044, rb=0.031, h=0.062,
                                            liquid=LATTE, foam=FOAM, art=True),
    'raf':              lambda: ceramic_cup(rt=0.042, rb=0.030, h=0.074,
                                            liquid=M('#d8b98e', 0.35), foam=FOAM),
    'iced-latte':       lambda: cold_cup(MILK, second=COLD_BREW, ice=5,
                                         straw_mat=STRAW_A),
    'cold-brew':        lambda: cold_cup(COLD_BREW, ice=6, straw_mat=STRAW_R),
    # напитки
    'matcha':           lambda: cold_cup(MATCHA, second=MILK, ice=4,
                                         straw_mat=M('#4f9e46', 0.35)),
    'cocoa':            lambda: mug(),
    'tea':              armudu,
    'lemonade':         lambda: glass_drink(LEMON, garnish='lemon', straw_mat=STRAW_A),
    'berry-lemonade':   lambda: glass_drink(BERRY_LIQ, garnish='berry', straw_mat=STRAW_R),
    'orange-juice':     lambda: glass_drink(ORANGE, garnish='orange', ice=3),
    'cola':             bottle,
    'smoothie':         lambda: cold_cup(SMOOTHIE, ice=0, straw_mat=STRAW_R,
                                         dome_lid=True),
    'milkshake':        milkshake,
    # десерты
    'cheesecake':       lambda: cheesecake(False),
    'cheesecake-berry': lambda: cheesecake(True),
    'brownie':          brownie,
    'croissant':        croissant,
    'pancakes':         pancakes,
    # комбо
    'combo-classic':    lambda: combo('classic'),
    'combo-duo':        lambda: combo('duo'),
    'combo-shake':      lambda: combo('shake'),
}

def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for name in sorted(DISHES):
        parts = DISHES[name]()
        path = os.path.join(OUT, name + '.glb')
        size = save(parts, path)
        total += size
        tris = sum(len(p.t) for p in parts)
        print('%-20s %7.1f KB  %6d tris' % (name, size / 1024.0, tris))
    print('-' * 44)
    print('%d models, %.1f KB total' % (len(DISHES), total / 1024.0))

if __name__ == '__main__':
    main()
