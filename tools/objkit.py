# -*- coding: utf-8 -*-
"""
OBJ -> glTF.

Сканеры почти всегда умеют выгрузить OBJ — это самый надёжный формат
(GLB отдают не все и не всегда). Здесь OBJ вместе с .mtl и текстурой
превращается в те же структуры, с которыми работает prepare_scan.py.

Отдельно не запускается, используется из prepare_scan.py.
"""
import json, math, os, struct

MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}

def _srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _find(name, folders):
    """Ищет файл текстуры рядом с obj и mtl, не обращая внимания на регистр."""
    base = os.path.basename(name.replace('\\', '/'))
    for folder in folders:
        direct = os.path.join(folder, base)
        if os.path.exists(direct):
            return direct
        try:
            for entry in os.listdir(folder):
                if entry.lower() == base.lower():
                    return os.path.join(folder, entry)
        except OSError:
            pass
    return None

def read_mtl(path, folders):
    """{имя материала: {'kd': (r,g,b), 'tex': путь к картинке}}"""
    mats = {}
    cur = None
    try:
        lines = open(path, 'r', encoding='utf-8', errors='replace').read().split('\n')
    except OSError:
        return mats
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        key = parts[0].lower()
        if key == 'newmtl':
            cur = ' '.join(parts[1:])
            mats[cur] = {'kd': (0.8, 0.8, 0.8), 'tex': None}
        elif cur is None:
            continue
        elif key == 'kd' and len(parts) >= 4:
            try:
                mats[cur]['kd'] = tuple(float(v) for v in parts[1:4])
            except ValueError:
                pass
        elif key in ('map_kd', 'map_ka'):
            # у map_Kd бывают ключи вида «-s 1 1 1 file.jpg» — имя всегда последнее
            found = _find(parts[-1], folders)
            if found and not mats[cur]['tex']:
                mats[cur]['tex'] = found
    return mats

def load_obj(path):
    """OBJ -> (gltf, blob). Треугольники, нормали, UV, цвета вершин, текстура."""
    folder = os.path.dirname(os.path.abspath(path)) or '.'
    pos, uv, nrm, col = [], [], [], []
    groups = {}          # имя материала -> список (vi, ti, ni)
    cur = ''
    groups[cur] = []
    mtl_files = []

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line or line[0] == '#':
                continue
            parts = line.split()
            if not parts:
                continue
            tag = parts[0]

            if tag == 'v':
                try:
                    pos.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except (IndexError, ValueError):
                    continue
                if len(parts) >= 7:      # v x y z r g b — цвет прямо в вершине
                    try:
                        col.append(tuple(_srgb2lin(min(1.0, max(0.0, float(parts[i]))))
                                         for i in (4, 5, 6)))
                    except ValueError:
                        col.append((1.0, 1.0, 1.0))
            elif tag == 'vt':
                try:
                    u = float(parts[1])
                    v = float(parts[2]) if len(parts) > 2 else 0.0
                except (IndexError, ValueError):
                    continue
                uv.append((u, 1.0 - v))   # OBJ считает V снизу, glTF — сверху
            elif tag == 'vn':
                try:
                    nrm.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except (IndexError, ValueError):
                    continue
            elif tag == 'f':
                face = []
                for chunk in parts[1:]:
                    bits = chunk.split('/')
                    def at(i, total):
                        if i >= len(bits) or bits[i] == '':
                            return None
                        n = int(bits[i])
                        return n - 1 if n > 0 else total + n
                    face.append((at(0, len(pos)), at(1, len(uv)), at(2, len(nrm))))
                for i in range(1, len(face) - 1):     # веером в треугольники
                    groups[cur].append(face[0])
                    groups[cur].append(face[i])
                    groups[cur].append(face[i + 1])
            elif tag == 'usemtl':
                cur = ' '.join(parts[1:])
                groups.setdefault(cur, [])
            elif tag == 'mtllib':
                for nm in parts[1:]:
                    found = _find(nm, [folder])
                    if found:
                        mtl_files.append(found)

    if not pos:
        raise ValueError('в OBJ нет вершин')

    mats = {}
    for mf in mtl_files:
        mats.update(read_mtl(mf, [os.path.dirname(mf), folder]))

    have_uv = bool(uv)
    have_col = len(col) == len(pos)

    # ---- вершины по материалам ----
    prims = []
    textures = {}        # путь -> индекс image
    images = []

    for name, tri in groups.items():
        if not tri:
            continue
        seen = {}
        vp, vt, vn, vc, idx = [], [], [], [], []
        for key in tri:
            slot = seen.get(key)
            if slot is None:
                slot = len(vp)
                seen[key] = slot
                vi, ti, ni = key
                vp.append(pos[vi] if vi is not None and vi < len(pos) else (0.0, 0.0, 0.0))
                if have_uv:
                    vt.append(uv[ti] if ti is not None and ti < len(uv) else (0.0, 0.0))
                if nrm:
                    vn.append(nrm[ni] if ni is not None and ni < len(nrm) else (0.0, 1.0, 0.0))
                if have_col:
                    vc.append(col[vi] if vi is not None and vi < len(col) else (1.0, 1.0, 1.0))
            idx.append(slot)

        if not nrm:
            vn = _smooth_normals(vp, idx)

        mat = mats.get(name, {'kd': (0.8, 0.8, 0.8), 'tex': None})
        tex_index = None
        if mat.get('tex'):
            if mat['tex'] not in textures:
                ext = os.path.splitext(mat['tex'])[1].lower()
                textures[mat['tex']] = len(images)
                images.append((mat['tex'], MIME.get(ext, 'image/jpeg')))
            tex_index = textures[mat['tex']]

        prims.append({'p': vp, 'n': vn, 't': vt if have_uv else None,
                      'c': vc if have_col else None, 'i': idx,
                      'kd': mat.get('kd', (0.8, 0.8, 0.8)), 'tex': tex_index})

    if not prims:
        raise ValueError('в OBJ нет граней')

    return _assemble(prims, images)

def _smooth_normals(vp, idx):
    acc = [[0.0, 0.0, 0.0] for _ in vp]
    for k in range(0, len(idx) - 2, 3):
        a, b, c = vp[idx[k]], vp[idx[k + 1]], vp[idx[k + 2]]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        n = (uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx)
        for slot in (idx[k], idx[k + 1], idx[k + 2]):
            acc[slot][0] += n[0]
            acc[slot][1] += n[1]
            acc[slot][2] += n[2]
    out = []
    for n in acc:
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        out.append((n[0] / ln, n[1] / ln, n[2] / ln) if ln > 1e-12 else (0.0, 1.0, 0.0))
    return out

def _assemble(prims, images):
    blob = bytearray()
    views, accs, mats, gl_prims = [], [], [], []

    def put(data, target=None):
        blob.extend(b'\x00' * ((-len(blob)) % 4))
        view = {'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)}
        if target:
            view['target'] = target
        views.append(view)
        blob.extend(data)
        return len(views) - 1

    def vec(seq, dim, minmax=False):
        flat = [c for v in seq for c in v]
        acc = {'bufferView': put(struct.pack('<%df' % len(flat), *flat), 34962),
               'componentType': 5126, 'count': len(seq),
               'type': {2: 'VEC2', 3: 'VEC3'}[dim]}
        if minmax:
            acc['min'] = [min(v[i] for v in seq) for i in range(dim)]
            acc['max'] = [max(v[i] for v in seq) for i in range(dim)]
        accs.append(acc)
        return len(accs) - 1

    for pr in prims:
        attrs = {'POSITION': vec(pr['p'], 3, True), 'NORMAL': vec(pr['n'], 3)}
        if pr['t']:
            attrs['TEXCOORD_0'] = vec(pr['t'], 2)
        if pr['c']:
            attrs['COLOR_0'] = vec(pr['c'], 3)

        small = len(pr['p']) < 65535
        fmt = ('<%dH' if small else '<%dI') % len(pr['i'])
        accs.append({'bufferView': put(struct.pack(fmt, *pr['i']), 34963),
                     'componentType': 5123 if small else 5125,
                     'count': len(pr['i']), 'type': 'SCALAR'})

        kd = pr['kd']
        pbr = {'baseColorFactor': [_srgb2lin(kd[0]), _srgb2lin(kd[1]), _srgb2lin(kd[2]), 1.0],
               'metallicFactor': 0.0, 'roughnessFactor': 0.9}
        if pr['tex'] is not None:
            pbr['baseColorFactor'] = [1.0, 1.0, 1.0, 1.0]
            pbr['baseColorTexture'] = {'index': pr['tex']}
        mats.append({'pbrMetallicRoughness': pbr, 'doubleSided': True})

        gl_prims.append({'attributes': attrs, 'indices': len(accs) - 1,
                         'material': len(mats) - 1})

    gltf_images, gltf_textures, samplers = [], [], []
    if images:
        samplers = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
    for path, mime in images:
        data = open(path, 'rb').read()
        gltf_images.append({'bufferView': put(data), 'mimeType': mime})
        gltf_textures.append({'source': len(gltf_images) - 1, 'sampler': 0})

    gltf = {
        'asset': {'version': '2.0', 'generator': 'Lazza obj import'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': 'scan'}],
        'meshes': [{'primitives': gl_prims}],
        'materials': mats,
        'accessors': accs,
        'bufferViews': views,
        'buffers': [{'byteLength': len(blob)}],
    }
    if gltf_images:
        gltf['images'] = gltf_images
        gltf['textures'] = gltf_textures
        gltf['samplers'] = samplers
    return gltf, bytes(blob)
