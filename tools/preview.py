# -*- coding: utf-8 -*-
"""
Быстрый предпросмотр .glb без браузера — контрольный лист всех моделей.

Запуск:  python tools/preview.py [имя ...]
Результат: tools/preview.png
"""
import json, math, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, 'models')

CT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

def load_glb(path):
    raw = open(path, 'rb').read()
    magic, ver, total = struct.unpack('<III', raw[:12])
    assert magic == 0x46546C67 and ver == 2, 'not a glb2'
    assert total == len(raw), 'length mismatch %d vs %d' % (total, len(raw))
    off = 12
    js = bin_ = None
    while off < len(raw):
        ln, ty = struct.unpack('<II', raw[off:off + 8])
        data = raw[off + 8:off + 8 + ln]
        if ty == 0x4E4F534A:
            js = json.loads(data)
        elif ty == 0x004E4942:
            bin_ = data
        off += 8 + ln
    return js, bin_

def acc(g, b, i):
    a = g['accessors'][i]
    v = g['bufferViews'][a['bufferView']]
    n = a['count'] * NC[a['type']]
    arr = np.frombuffer(b, dtype=CT[a['componentType']],
                        count=n, offset=v.get('byteOffset', 0))
    return arr.reshape(a['count'], NC[a['type']]).astype(np.float64 if a['componentType'] == 5126 else np.int64)

def face_normals(pos, idx):
    """Нормали по граням — если в файле их нет (бывает у сканов)."""
    n = np.zeros_like(pos)
    a, b, c = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
    f = np.cross(b - a, c - a)
    for k in range(3):
        np.add.at(n, idx[:, k], f)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return np.divide(n, ln, out=np.tile([0.0, 1.0, 0.0], (len(n), 1)), where=ln > 1e-12)

def prims(path):
    g, b = load_glb(path)
    out = []
    for p in g['meshes'][0]['primitives']:
        pos = acc(g, b, p['attributes']['POSITION'])
        idx = acc(g, b, p['indices']).reshape(-1, 3)
        if 'NORMAL' in p['attributes']:
            nor = acc(g, b, p['attributes']['NORMAL'])
        else:
            nor = face_normals(pos, idx)
        m = g['materials'][p['material']] if 'material' in p else {}
        pbr = m.get('pbrMetallicRoughness', {})
        # текстуры не рисуем — у сканов показываем ровный светлый тон
        base = pbr.get('baseColorFactor',
                       [0.62, 0.55, 0.46, 1.0] if 'baseColorTexture' in pbr else [0.8, 0.8, 0.8, 1.0])
        out.append((pos, nor, idx, base, m.get('doubleSided', False)))
    return out

def lin2srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

L1 = np.array([0.42, 0.80, 0.43]); L1 /= np.linalg.norm(L1)
L2 = np.array([-0.65, 0.25, -0.55]); L2 /= np.linalg.norm(L2)

def render(path, S=250, az=32.0, el=20.0):
    ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
    ce, se = math.cos(math.radians(el)), math.sin(math.radians(el))
    Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
    Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    R = Rx @ Ry

    ps = prims(path)
    allv = np.vstack([p[0] for p in ps]) @ R.T
    lo, hi = allv.min(0), allv.max(0)
    ctr = (lo + hi) / 2.0
    scale = (S * 0.84) / max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)

    col = np.zeros((S, S, 3)); col[:] = np.array([0.045, 0.032, 0.026])
    zb = np.full((S, S), -1e9)

    def draw(pos, nor, idx, base, blend):
        v = pos @ R.T
        n = nor @ R.T
        x = (v[:, 0] - ctr[0]) * scale + S / 2.0
        y = S / 2.0 - (v[:, 1] - ctr[1]) * scale
        z = v[:, 2]
        rgb = np.array(base[:3]); alpha = base[3]
        sh = (0.26 + 0.10 * n[:, 1]
              + 0.72 * np.clip(n @ L1, 0, None)
              + 0.22 * np.clip(n @ L2, 0, None))
        vc = rgb[None, :] * sh[:, None]
        tri = idx
        if blend:
            order = np.argsort(z[tri].mean(1))
            tri = tri[order]
        for t in tri:
            a, b, c = t
            x0, x1 = int(max(0, math.floor(min(x[a], x[b], x[c])))), int(min(S - 1, math.ceil(max(x[a], x[b], x[c]))))
            y0, y1 = int(max(0, math.floor(min(y[a], y[b], y[c])))), int(min(S - 1, math.ceil(max(y[a], y[b], y[c]))))
            if x1 < x0 or y1 < y0:
                continue
            d = (y[b] - y[c]) * (x[a] - x[c]) + (x[c] - x[b]) * (y[a] - y[c])
            if abs(d) < 1e-9:
                continue
            px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((y[b] - y[c]) * (px - x[c]) + (x[c] - x[b]) * (py - y[c])) / d
            w1 = ((y[c] - y[a]) * (px - x[c]) + (x[a] - x[c]) * (py - y[c])) / d
            w2 = 1.0 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any():
                continue
            zz = w0 * z[a] + w1 * z[b] + w2 * z[c]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            m &= zz > sub
            if not m.any():
                continue
            cc = (w0[..., None] * vc[a] + w1[..., None] * vc[b] + w2[..., None] * vc[c])
            tgt = col[y0:y1 + 1, x0:x1 + 1]
            if blend:
                tgt[m] = tgt[m] * (1 - alpha) + cc[m] * alpha
            else:
                tgt[m] = cc[m]
                sub[m] = zz[m]

    for pos, nor, idx, base, ds in ps:
        if base[3] >= 1.0:
            draw(pos, nor, idx, base, False)
    for pos, nor, idx, base, ds in ps:
        if base[3] < 1.0:
            draw(pos, nor, idx, base, True)

    return Image.fromarray((lin2srgb(col) * 255).astype(np.uint8))

def main():
    names = sys.argv[1:] or sorted(f[:-4] for f in os.listdir(MODELS) if f.endswith('.glb'))
    cols = 6 if len(names) > 6 else len(names)
    rows = (len(names) + cols - 1) // cols
    S, PAD = 250, 18
    sheet = Image.new('RGB', (cols * S, rows * (S + PAD)), (22, 16, 13))
    d = ImageDraw.Draw(sheet)
    for i, nm in enumerate(names):
        img = render(os.path.join(MODELS, nm + '.glb'), S)
        cx, cy = (i % cols) * S, (i // cols) * (S + PAD)
        sheet.paste(img, (cx, cy))
        d.text((cx + 6, cy + S + 3), nm, fill=(233, 162, 59))
        print('ok', nm)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview.png')
    sheet.save(out)
    print('->', out, sheet.size)

if __name__ == '__main__':
    main()
