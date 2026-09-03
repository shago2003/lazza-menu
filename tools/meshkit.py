# -*- coding: utf-8 -*-
"""
Разбор и чистка меша.

У Kabaq — конторы, которая делает AR-меню для сотен ресторанов — после
фотограмметрии модель чистят «3D-скрипты», а потом художник. Здесь та
часть, которую можно посчитать: выкинуть куски стола, обрывки в воздухе
и мелкий мусор, оставив само блюдо.

Отдельно не запускается, используется из prepare_scan.py.
"""
import numpy as np

CT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}
NORM_MAX = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
VEC = {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}

# ============================================================
#   ЧТЕНИЕ
# ============================================================

def read_accessor(gltf, blob, index):
    a = gltf['accessors'][index]
    comps = NC[a['type']]
    dt = np.dtype('<' + CT[a['componentType']])
    n = a['count']

    if 'bufferView' not in a:
        arr = np.zeros((n, comps), dtype=dt)
    else:
        bv = gltf['bufferViews'][a['bufferView']]
        base = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        item = comps * dt.itemsize
        stride = bv.get('byteStride') or item
        need = stride * (n - 1) + item
        raw = np.frombuffer(blob, dtype=np.uint8, count=need, offset=base)
        view = np.lib.stride_tricks.as_strided(raw, shape=(n, item), strides=(stride, 1))
        arr = np.ascontiguousarray(view).view(dt).reshape(n, comps)

    if a.get('normalized') and a['componentType'] in NORM_MAX:
        return np.clip(arr.astype(np.float32) / NORM_MAX[a['componentType']], -1.0, 1.0)
    if a['componentType'] == 5126:
        return arr.astype(np.float32)
    return arr.astype(np.int64)

def node_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=np.float64).reshape(4, 4).T
    m = np.eye(4)
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    r = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    m[:3, :3] = r * np.array(node.get('scale', [1, 1, 1]))[None, :]
    m[:3, 3] = node.get('translation', [0, 0, 0])
    return m

def decode(gltf, blob):
    """Все треугольники сцены в мировых координатах.
       -> список {attrs: {имя: массив}, idx: (n,3), material: int}"""
    nodes = gltf.get('nodes', [])
    meshes = gltf.get('meshes', [])
    out = []

    def walk(i, parent):
        node = nodes[i]
        m = parent @ node_matrix(node)
        if 'mesh' in node:
            for prim in meshes[node['mesh']].get('primitives', []):
                if prim.get('mode', 4) != 4 or 'POSITION' not in prim.get('attributes', {}):
                    continue
                attrs = {k: read_accessor(gltf, blob, v)
                         for k, v in prim['attributes'].items()}
                if 'indices' in prim:
                    idx = read_accessor(gltf, blob, prim['indices']).reshape(-1)
                else:
                    idx = np.arange(len(attrs['POSITION']), dtype=np.int64)
                idx = idx[:len(idx) // 3 * 3].reshape(-1, 3).astype(np.int64)

                pos = attrs['POSITION']
                ones = np.ones((len(pos), 1), dtype=np.float64)
                attrs['POSITION'] = ((np.hstack([pos, ones]) @ m.T)[:, :3]).astype(np.float32)
                if 'NORMAL' in attrs:
                    rot = m[:3, :3]
                    n = attrs['NORMAL'].astype(np.float64) @ rot.T
                    ln = np.linalg.norm(n, axis=1, keepdims=True)
                    attrs['NORMAL'] = np.divide(n, ln, out=np.zeros_like(n),
                                                where=ln > 1e-12).astype(np.float32)
                out.append({'attrs': attrs, 'idx': idx,
                            'material': prim.get('material')})
        for kid in node.get('children', []):
            walk(kid, m)

    scenes = gltf.get('scenes', [])
    roots = scenes[gltf.get('scene', 0)].get('nodes', []) if scenes else range(len(nodes))
    ident = np.eye(4)
    for r in roots:
        walk(r, ident)
    return out

# ============================================================
#   ЧИСТКА
# ============================================================

def tri_count(prims):
    return int(sum(len(p['idx']) for p in prims))

def bounds(prims):
    lo = np.array([1e30] * 3)
    hi = np.array([-1e30] * 3)
    for p in prims:
        used = np.unique(p['idx'])
        if not len(used):
            continue
        v = p['attrs']['POSITION'][used]
        lo = np.minimum(lo, v.min(0))
        hi = np.maximum(hi, v.max(0))
    return lo, hi

def _keep_tris(prims, masks):
    """Оставляет только отмеченные треугольники и выбрасывает лишние вершины."""
    out = []
    for p, keep in zip(prims, masks):
        idx = p['idx'][keep]
        if not len(idx):
            continue
        used, inverse = np.unique(idx.reshape(-1), return_inverse=True)
        attrs = {k: v[used] for k, v in p['attrs'].items()}
        out.append({'attrs': attrs, 'idx': inverse.reshape(-1, 3).astype(np.int64),
                    'material': p['material']})
    return out

def drop_specks(prims, min_share=0.02):
    """Выкидывает обрывки: связные куски мельче доли от всей модели.
       Возвращает (новые части, сколько треугольников убрано)."""
    before = tri_count(prims)
    masks = []
    for p in prims:
        idx = p['idx']
        n = len(p['attrs']['POSITION'])
        parent = np.arange(n, dtype=np.int64)

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for a, b, c in idx:
            ra, rb, rc = find(a), find(b), find(c)
            if ra != rb:
                parent[rb] = ra
            if ra != rc:
                parent[rc] = ra

        roots = np.array([find(i) for i in range(n)], dtype=np.int64)
        tri_root = roots[idx[:, 0]]
        labels, counts = np.unique(tri_root, return_counts=True)
        if not len(counts):
            masks.append(np.zeros(len(idx), dtype=bool))
            continue
        limit = max(1, int(counts.max() * min_share))
        good = set(labels[counts >= limit].tolist())
        masks.append(np.array([r in good for r in tri_root], dtype=bool))

    cleaned = _keep_tris(prims, masks)
    return cleaned, before - tri_count(cleaned)

def guess_floor(prims, bins=40):
    """Ищет стол: у самого низа модель заметно шире, чем чуть выше.
       Возвращает высоту среза или None."""
    lo, hi = bounds(prims)
    height = hi[1] - lo[1]
    if height <= 1e-9:
        return None

    pts = np.vstack([p['attrs']['POSITION'][np.unique(p['idx'])] for p in prims])
    level = np.clip(((pts[:, 1] - lo[1]) / height * bins).astype(int), 0, bins - 1)

    span = np.zeros(bins)
    for b in range(bins):
        sel = pts[level == b]
        if len(sel) < 12:
            span[b] = np.nan
            continue
        c = np.nanmedian(sel[:, [0, 2]], axis=0)
        span[b] = np.nanpercentile(np.linalg.norm(sel[:, [0, 2]] - c, axis=1), 92)

    body = np.nanmedian(span[int(bins * 0.35):int(bins * 0.8)])
    if not np.isfinite(body) or body <= 0:
        return None

    cut = None
    for b in range(int(bins * 0.3)):            # стол ищем только в нижней трети
        if np.isfinite(span[b]) and span[b] > body * 1.9:
            cut = b + 1
    if cut is None:
        return None
    return lo[1] + height * (cut / bins)

def cut_below(prims, y):
    """Срезает всё ниже уровня y (треугольник уходит, если ниже весь)."""
    masks = []
    for p in prims:
        py = p['attrs']['POSITION'][:, 1]
        masks.append(~(py[p['idx']] < y).all(axis=1))
    return _keep_tris(prims, masks)

def cut_outside(prims, radius, center):
    """Срезает всё дальше radius от вертикальной оси в точке center (x, z)."""
    masks = []
    for p in prims:
        d = np.linalg.norm(p['attrs']['POSITION'][:, [0, 2]] - np.array(center), axis=1)
        masks.append(~(d[p['idx']] > radius).all(axis=1))
    return _keep_tris(prims, masks)

def transform(prims, scale=1.0, offset=(0.0, 0.0, 0.0), rot=None):
    for p in prims:
        v = p['attrs']['POSITION'].astype(np.float64)
        if rot is not None:
            v = v @ np.asarray(rot).T
            if 'NORMAL' in p['attrs']:
                p['attrs']['NORMAL'] = (p['attrs']['NORMAL'].astype(np.float64)
                                        @ np.asarray(rot).T).astype(np.float32)
        p['attrs']['POSITION'] = (v * scale + np.asarray(offset)).astype(np.float32)
    return prims

# ============================================================
#   СБОРКА ОБРАТНО
# ============================================================

def encode(prims, source):
    """Собирает glTF заново, забирая из исходника материалы и текстуры."""
    import struct
    blob = bytearray()
    views, accs = [], []

    def put(data, target=None):
        blob.extend(b'\x00' * ((-len(blob)) % 4))
        view = {'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)}
        if target:
            view['target'] = target
        views.append(view)
        blob.extend(data)
        return len(views) - 1

    def acc_float(arr, minmax=False):
        arr = np.ascontiguousarray(arr, dtype='<f4')
        comps = arr.shape[1]
        a = {'bufferView': put(arr.tobytes(), 34962), 'componentType': 5126,
             'count': int(arr.shape[0]), 'type': VEC[comps]}
        if minmax:
            a['min'] = [float(v) for v in arr.min(0)]
            a['max'] = [float(v) for v in arr.max(0)]
        accs.append(a)
        return len(accs) - 1

    gl_prims = []
    for p in prims:
        attrs = {}
        for name, arr in p['attrs'].items():
            if arr.ndim != 2 or arr.shape[1] not in VEC:
                continue
            attrs[name] = acc_float(arr, minmax=(name == 'POSITION'))
        if 'POSITION' not in attrs:
            continue

        idx = p['idx'].reshape(-1)
        small = len(p['attrs']['POSITION']) < 65535
        data = idx.astype('<u2' if small else '<u4').tobytes()
        accs.append({'bufferView': put(data, 34963),
                     'componentType': 5123 if small else 5125,
                     'count': int(len(idx)), 'type': 'SCALAR'})
        entry = {'attributes': attrs, 'indices': len(accs) - 1}
        if p['material'] is not None:
            entry['material'] = p['material']
        gl_prims.append(entry)

    gltf = {
        'asset': {'version': '2.0', 'generator': 'Lazza scan cleaner'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': 'dish'}],
        'meshes': [{'primitives': gl_prims}],
        'accessors': accs,
        'bufferViews': views,
        'buffers': [{'byteLength': 0}],
    }

    if source.get('materials'):
        gltf['materials'] = source['materials']
    for key in ('textures', 'samplers'):
        if source.get(key):
            gltf[key] = source[key]

    # картинки переносим вместе с байтами
    if source.get('images'):
        images = []
        for img, data in source['images']:
            new = dict(img)
            new.pop('uri', None)
            if data is not None:
                new['bufferView'] = put(data)
            images.append(new)
        gltf['images'] = images

    gltf['buffers'][0]['byteLength'] = len(blob)
    return gltf, bytes(blob)

def take_source(gltf, blob, folder=''):
    """Материалы, текстуры и байты картинок из исходного файла.

    Картинка бывает не внутри .glb, а отдельным файлом рядом — так
    устроены, например, бесплатные паки моделей. Такую надо найти
    и вшить внутрь, иначе на сайте модель будет белой."""
    import base64
    import os as _os
    from urllib.parse import unquote

    images = []
    for img in gltf.get('images', []):
        data = None
        if 'bufferView' in img:
            bv = gltf['bufferViews'][img['bufferView']]
            off = bv.get('byteOffset', 0)
            data = bytes(blob[off:off + bv['byteLength']])
        elif img.get('uri', '').startswith('data:'):
            data = base64.b64decode(img['uri'].split(',', 1)[1])
        elif img.get('uri'):
            path = _os.path.join(folder, unquote(img['uri']).replace('\\', '/'))
            if _os.path.exists(path):
                data = open(path, 'rb').read()
        images.append((img, data))
    return {'materials': gltf.get('materials'), 'textures': gltf.get('textures'),
            'samplers': gltf.get('samplers'), 'images': images}
