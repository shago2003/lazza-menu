# -*- coding: utf-8 -*-
"""
LAZZA — генератор 3D-моделей (.glb) для AR-меню.

Запуск:  python tools/make_models.py
Результат: models/<файл>.glb — по одной модели на позицию меню.

Модели стилизованные, low-poly, собираются из примитивов.
Размеры — в метрах, как в жизни: AR ставит блюдо на стол в натуральную величину.
Ось Y — вверх, низ модели на y=0.

Хотите настоящую фотомодель вместо стилизованной — положите свой .glb
с тем же именем в папку models/. Код менять не нужно.
"""
import json, math, os, random, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'models')
TAU = math.pi * 2
RND = random.Random(20250903)

# ============================================================
#   МАТЕРИАЛЫ
# ============================================================

def _s2l(c):
    """sRGB -> linear: glTF хранит цвет линейным, иначе всё выглядит выцветшим."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def M(hexcolor, rough=0.72, metal=0.0, alpha=1.0, double=False, emis=0.0):
    """Материал: цвет в привычном hex, остальное — параметры PBR."""
    h = hexcolor.lstrip('#')
    rgb = tuple(_s2l(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))
    return (rgb, round(rough, 3), round(metal, 3), round(alpha, 3), bool(double), round(emis, 3))

# ============================================================
#   ЧАСТЬ МОДЕЛИ
# ============================================================

class P:
    """Кусок геометрии с одним материалом. g — группа сглаживания вершины."""
    __slots__ = ('v', 't', 'g', 'mat', 'smooth')

    def __init__(self, v, t, g, mat, smooth):
        self.v = v
        self.t = t
        self.g = g
        self.mat = mat
        self.smooth = smooth

# ---------- трансформации (работают со списком частей) ----------

def _apply(parts, fn):
    for p in parts:
        p.v = [fn(x, y, z) for (x, y, z) in p.v]
    return parts

def mv(parts, dx=0.0, dy=0.0, dz=0.0):
    return _apply(parts, lambda x, y, z: (x + dx, y + dy, z + dz))

def sc(parts, sx, sy=None, sz=None):
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    return _apply(parts, lambda x, y, z: (x * sx, y * sy, z * sz))

def roty(parts, a):
    c, s = math.cos(a), math.sin(a)
    return _apply(parts, lambda x, y, z: (x * c + z * s, y, -x * s + z * c))

def rotx(parts, a):
    c, s = math.cos(a), math.sin(a)
    return _apply(parts, lambda x, y, z: (x, y * c - z * s, y * s + z * c))

def rotz(parts, a):
    c, s = math.cos(a), math.sin(a)
    return _apply(parts, lambda x, y, z: (x * c - y * s, x * s + y * c, z))

def copy(parts):
    return [P(list(p.v), list(p.t), list(p.g), p.mat, p.smooth) for p in parts]

# ============================================================
#   ПРИМИТИВЫ
# ============================================================

def lathe(profile, mat, seg=30, smooth=True, cap_bottom=True, cap_top=True):
    """Тело вращения по профилю [(радиус, высота), ...] снизу вверх."""
    v = []
    t = []
    g = []
    rings = []
    for (r, y) in profile:
        if abs(r) < 1e-9:
            rings.append(('pt', len(v)))
            v.append((0.0, y, 0.0))
            g.append(0)
        else:
            rings.append(('ring', len(v)))
            for i in range(seg):
                a = TAU * i / seg
                v.append((r * math.cos(a), y, r * math.sin(a)))
                g.append(0)
    for k in range(len(rings) - 1):
        k0, i0 = rings[k]
        k1, i1 = rings[k + 1]
        if k0 == 'ring' and k1 == 'ring':
            for i in range(seg):
                j = (i + 1) % seg
                a, b, c, d = i0 + i, i0 + j, i1 + j, i1 + i
                t.append((a, d, c))
                t.append((a, c, b))
        elif k0 == 'pt':
            for i in range(seg):
                j = (i + 1) % seg
                t.append((i0, i1 + i, i1 + j))
        else:
            for i in range(seg):
                j = (i + 1) % seg
                t.append((i0 + i, i1, i0 + j))
    parts = [P(v, t, g, mat, smooth)]
    # крышки — отдельной группой сглаживания, чтобы рёбра остались чёткими
    caps = ((cap_bottom, rings[0], profile[0][1], True),
            (cap_top, rings[-1], profile[-1][1], False))
    for need, ring, y, down in caps:
        if not need or ring[0] != 'ring':
            continue
        base = ring[1]
        cv = [v[base + i] for i in range(seg)] + [(0.0, y, 0.0)]
        ct = []
        for i in range(seg):
            j = (i + 1) % seg
            ct.append((seg, i, j) if down else (seg, j, i))
        parts.append(P(cv, ct, [1] * (seg + 1), mat, False))
    return parts

def cyl(r, h, mat, seg=28, r_top=None, smooth=True):
    return lathe([(r, 0.0), (r if r_top is None else r_top, h)], mat, seg, smooth)

def sphere(r, mat, seg=24, rings=13, smooth=True):
    prof = [(r * math.sin(math.pi * k / rings), -r * math.cos(math.pi * k / rings))
            for k in range(rings + 1)]
    return mv(lathe(prof, mat, seg, smooth), 0, r, 0)

def dome(r, h, mat, seg=26, rings=8, smooth=True, cap=True):
    """Полусфера-купол: булка, шапка мороженого, крышка стакана."""
    prof = [(r * math.cos(math.pi / 2 * k / rings), h * math.sin(math.pi / 2 * k / rings))
            for k in range(rings + 1)]
    return lathe(prof, mat, seg, smooth, cap_bottom=cap)

def box(w, h, d, mat, smooth=False):
    a, b = w / 2.0, d / 2.0
    v = [(-a, 0, -b), (a, 0, -b), (a, 0, b), (-a, 0, b),
         (-a, h, -b), (a, h, -b), (a, h, b), (-a, h, b)]
    t = [(0, 1, 2), (0, 2, 3), (4, 7, 6), (4, 6, 5),
         (3, 2, 6), (3, 6, 7), (1, 0, 4), (1, 4, 5),
         (2, 1, 5), (2, 5, 6), (0, 3, 7), (0, 7, 4)]
    return [P(v, t, [0] * 8, mat, smooth)]

def torus(R, r, mat, seg=26, seg2=12, smooth=True):
    v = []
    t = []
    for i in range(seg):
        u = TAU * i / seg
        for k in range(seg2):
            w = TAU * k / seg2
            rr = R + r * math.cos(w)
            v.append((rr * math.cos(u), r * math.sin(w), rr * math.sin(u)))
    for i in range(seg):
        i2 = (i + 1) % seg
        for k in range(seg2):
            k2 = (k + 1) % seg2
            a = i * seg2 + k
            b = i2 * seg2 + k
            c = i2 * seg2 + k2
            d = i * seg2 + k2
            t.append((a, d, c))
            t.append((a, c, b))
    return mv([P(v, t, [0] * len(v), mat, smooth)], 0, r, 0)

def leaf(r, mat, seg=44, rings=4, amp=0.010, freq=9, tilt=1.5):
    """Волнистый лист — салат, руккола. Материал двусторонний."""
    v = [(0.0, 0.0, 0.0)]
    t = []
    for k in range(1, rings + 1):
        f = k / rings
        for i in range(seg):
            a = TAU * i / seg
            rr = r * f * (1.0 + 0.09 * math.sin(freq * a))
            y = amp * math.sin(freq * a) * (f ** tilt)
            v.append((rr * math.cos(a), y, rr * math.sin(a)))
    for i in range(seg):
        j = (i + 1) % seg
        t.append((0, 1 + i, 1 + j))
    for k in range(rings - 1):
        b0 = 1 + k * seg
        b1 = b0 + seg
        for i in range(seg):
            j = (i + 1) % seg
            t.append((b0 + i, b1 + i, b1 + j))
            t.append((b0 + i, b1 + j, b0 + j))
    return [P(v, t, [0] * len(v), mat, True)]

def slab(w, d, mat, th=0.0022, droop=0.011, seg=5):
    """Квадратный ломтик с обвисшими краями — сыр, ветчина."""
    parts = []
    for top, off in ((True, th), (False, 0.0)):
        v = []
        t = []
        for iz in range(seg):
            fz = iz / (seg - 1.0) - 0.5
            for ix in range(seg):
                fx = ix / (seg - 1.0) - 0.5
                edge = max(abs(fx), abs(fz)) * 2.0
                y = off - droop * max(0.0, edge - 0.62) / 0.38
                v.append((fx * w, y, fz * d))
        for iz in range(seg - 1):
            for ix in range(seg - 1):
                a = iz * seg + ix
                b = a + 1
                c = a + seg + 1
                d2 = a + seg
                if top:
                    t.append((a, d2, c))
                    t.append((a, c, b))
                else:
                    t.append((a, b, c))
                    t.append((a, c, d2))
        parts.append(P(v, t, [0] * len(v), mat, True))
    return parts

def wedge(r, h, ang, mat, seg=14):
    """Кусок торта: сектор круга высотой h."""
    v = []
    t = []
    a0 = -ang / 2.0
    for i in range(seg + 1):
        a = a0 + ang * i / seg
        x, z = r * math.cos(a), r * math.sin(a)
        v.append((x, 0.0, z))
        v.append((x, h, z))
    c0 = len(v)
    v.append((0.0, 0.0, 0.0))
    v.append((0.0, h, 0.0))
    for i in range(seg):
        a, b = 2 * i, 2 * i + 1
        c, d = 2 * (i + 1), 2 * (i + 1) + 1
        t.append((a, b, d))
        t.append((a, d, c))
        t.append((c0 + 1, d, b))
        t.append((c0, a, c))
    t.append((c0, 1, 0))
    t.append((c0, c0 + 1, 1))
    e = 2 * seg
    t.append((c0, e + 1, c0 + 1))
    t.append((c0, e, e + 1))
    return [P(v, t, [0] * len(v), mat, False)]

def helix(r0, r1, h, mat, turns=2.6, seg=54, thick=0.011):
    """Спираль взбитых сливок."""
    v = []
    t = []
    ring = 8
    for i in range(seg + 1):
        f = i / float(seg)
        a = TAU * turns * f
        rad = r0 + (r1 - r0) * f
        cx, cy, cz = rad * math.cos(a), h * f, rad * math.sin(a)
        th = thick * (1.0 - 0.72 * f)
        for k in range(ring):
            w = TAU * k / ring
            v.append((cx + th * math.cos(w) * math.cos(a),
                      cy + th * math.sin(w),
                      cz + th * math.cos(w) * math.sin(a)))
    for i in range(seg):
        for k in range(ring):
            k2 = (k + 1) % ring
            a = i * ring + k
            b = (i + 1) * ring + k
            c = (i + 1) * ring + k2
            d = i * ring + k2
            t.append((a, d, c))
            t.append((a, c, b))
    return [P(v, t, [0] * len(v), mat, True)]

# ============================================================
#   ЗАПИСЬ GLB
# ============================================================

def _cross(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)

def _finalize(p):
    """Часть -> позиции, нормали, индексы. Плоские грани или сглаженные."""
    V, T = p.v, p.t
    if not p.smooth:
        pos = []
        nor = []
        idx = []
        for (a, b, c) in T:
            A, B, C = V[a], V[b], V[c]
            n = _cross(A, B, C)
            L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            n = (n[0] / L, n[1] / L, n[2] / L)
            i = len(pos)
            pos += [A, B, C]
            nor += [n, n, n]
            idx += [i, i + 1, i + 2]
        return pos, nor, idx
    key = {}
    remap = []
    pos = []
    for i, (x, y, z) in enumerate(V):
        k = (p.g[i], round(x, 6), round(y, 6), round(z, 6))
        if k not in key:
            key[k] = len(pos)
            pos.append((x, y, z))
        remap.append(key[k])
    nor = [[0.0, 0.0, 0.0] for _ in pos]
    idx = []
    for (a, b, c) in T:
        ra, rb, rc = remap[a], remap[b], remap[c]
        if ra == rb or rb == rc or ra == rc:
            continue
        n = _cross(pos[ra], pos[rb], pos[rc])
        for r in (ra, rb, rc):
            nor[r][0] += n[0]
            nor[r][1] += n[1]
            nor[r][2] += n[2]
        idx += [ra, rb, rc]
    out = []
    for n in nor:
        L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        out.append((n[0] / L, n[1] / L, n[2] / L) if L > 1e-12 else (0.0, 1.0, 0.0))
    return pos, out, idx

def save(parts, path):
    """Собирает части в один .glb (glTF 2.0 binary)."""
    merged = {}
    order = []
    for p in parts:
        pos, nor, idx = _finalize(p)
        if not idx:
            continue
        if p.mat not in merged:
            merged[p.mat] = ([], [], [])
            order.append(p.mat)
        m = merged[p.mat]
        off = len(m[0])
        m[0].extend(pos)
        m[1].extend(nor)
        m[2].extend(i + off for i in idx)

    mats = []
    prims = []
    accs = []
    views = []
    blob = bytearray()

    def push(data, target):
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target}
        views.append(view)
        blob.extend(data)
        blob.extend(b'\x00' * ((-len(data)) % 4))
        return len(views) - 1

    for mat in order:
        pos, nor, idx = merged[mat]
        rgb, rough, metal, alpha, double, emis = mat
        m = {"pbrMetallicRoughness": {"baseColorFactor": [rgb[0], rgb[1], rgb[2], alpha],
                                      "metallicFactor": metal,
                                      "roughnessFactor": rough},
             "doubleSided": double}
        if alpha < 1.0:
            m["alphaMode"] = "BLEND"
        if emis:
            m["emissiveFactor"] = [rgb[0] * emis, rgb[1] * emis, rgb[2] * emis]
        mats.append(m)

        flat = [c for v in pos for c in v]
        accs.append({"bufferView": push(struct.pack('<%df' % len(flat), *flat), 34962),
                     "componentType": 5126, "count": len(pos), "type": "VEC3",
                     "min": [min(v[i] for v in pos) for i in range(3)],
                     "max": [max(v[i] for v in pos) for i in range(3)]})
        a_pos = len(accs) - 1

        flat = [c for v in nor for c in v]
        accs.append({"bufferView": push(struct.pack('<%df' % len(flat), *flat), 34962),
                     "componentType": 5126, "count": len(nor), "type": "VEC3"})
        a_nor = len(accs) - 1

        small = len(pos) < 65535
        fmt = ('<%dH' if small else '<%dI') % len(idx)
        accs.append({"bufferView": push(struct.pack(fmt, *idx), 34963),
                     "componentType": 5123 if small else 5125,
                     "count": len(idx), "type": "SCALAR"})
        prims.append({"attributes": {"POSITION": a_pos, "NORMAL": a_nor},
                      "indices": len(accs) - 1, "material": len(mats) - 1})

    gltf = {"asset": {"version": "2.0", "generator": "Lazza model maker"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": os.path.basename(path)[:-4]}],
            "meshes": [{"primitives": prims}],
            "materials": mats,
            "accessors": accs,
            "bufferViews": views,
            "buffers": [{"byteLength": len(blob)}]}

    js = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    js += b' ' * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack('<II', len(blob), 0x004E4942))
        f.write(bytes(blob))
    return total
