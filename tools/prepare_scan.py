# -*- coding: utf-8 -*-
"""
LAZZA — подготовка отсканированного блюда для сайта.

Вы сняли настоящее блюдо на телефон (Scaniverse, RealityScan, KIRI)
и выгрузили модель. Принимаются .obj (с .mtl и картинкой рядом) и .glb —
из приложения надёжнее выгружать OBJ, его отдают все сканеры.

Файл из приложения к сайту не готов: не того размера, висит в стороне
от центра, лежит не на «полу» и весит десятки мегабайт.

Эта команда всё чинит:

    python tools/prepare_scan.py C:\\путь\\burger.glb burger-classic

  * чистит скан: выбрасывает стол, обрывки в воздухе и мелкий мусор —
    ровно ту грязь, из-за которой скан выглядит кривым;
  * ставит блюдо на «пол», центрует и масштабирует до натуральной величины
    (по умолчанию — под размер той модели, что уже лежит в models/);
  * уменьшает текстуры до разумных для телефона;
  * кладёт результат в models/burger-classic.glb — сайт подхватит сам;
  * говорит, сколько получилось, и ругается, если файл всё ещё тяжёлый.

Полезные ключи:
    --size 12       натуральная ширина блюда в сантиметрах
    --tex 2048      максимальная сторона текстуры (по умолчанию 2048)
    --rot-y 90      довернуть блюдо вокруг вертикали, градусы
    --rot-x -8      поправить наклон, если блюдо «падает»
    --zup           скан сделан в системе «Z вверх» и лежит на боку
    --floor off     не срезать стол (по умолчанию ищется сам)
    --radius 70     оставить только центр: проценты от ширины
    --dirty         не чистить вообще, посмотреть скан как есть
    --keep          не трогать текстуры
    --dry           только показать, что получится, ничего не записывать
"""
import argparse, io, json, math, os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meshkit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, 'models')

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

WARN_TRIS = 150000
WARN_BYTES = 6 * 1024 * 1024

# ============================================================
#   ЧТЕНИЕ И ЗАПИСЬ GLB
# ============================================================

def read_glb(path):
    raw = open(path, 'rb').read()
    if len(raw) < 12:
        die('файл слишком мал, это не .glb')
    magic, ver, total = struct.unpack('<III', raw[:12])
    if magic != GLB_MAGIC:
        die('это не .glb. Выгрузите из приложения именно GLB (не USDZ, не OBJ)')
    if ver != 2:
        die('версия glTF %d не поддерживается, нужна 2' % ver)

    gltf = None
    blob = b''
    off = 12
    while off + 8 <= len(raw):
        ln, kind = struct.unpack('<II', raw[off:off + 8])
        data = raw[off + 8:off + 8 + ln]
        if kind == CHUNK_JSON:
            gltf = json.loads(data.decode('utf-8'))
        elif kind == CHUNK_BIN:
            blob = data
        off += 8 + ln
    if gltf is None:
        die('в файле нет описания сцены')
    return gltf, blob

def write_glb(gltf, blob, path):
    js = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    js += b' ' * ((-len(js)) % 4)
    blob = bytes(blob) + b'\x00' * ((-len(blob)) % 4)
    total = 12 + 8 + len(js) + (8 + len(blob) if blob else 0)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', GLB_MAGIC, 2, total))
        f.write(struct.pack('<II', len(js), CHUNK_JSON))
        f.write(js)
        if blob:
            f.write(struct.pack('<II', len(blob), CHUNK_BIN))
            f.write(blob)
    return total

def die(msg):
    print('\n  Не получилось: %s\n' % msg)
    sys.exit(1)

# ============================================================
#   ГЕОМЕТРИЯ СЦЕНЫ
# ============================================================

def mat_mul(a, b):
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4))
    return out

def mat_from_trs(node):
    if 'matrix' in node:
        return list(node['matrix'])
    t = node.get('translation', [0, 0, 0])
    r = node.get('rotation', [0, 0, 0, 1])
    s = node.get('scale', [1, 1, 1])
    x, y, z, w = r
    rot = [
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
        2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
        0, 0, 0, 1,
    ]
    for c in range(3):
        for r_ in range(3):
            rot[c * 4 + r_] *= s[c]
    rot[12], rot[13], rot[14] = t[0], t[1], t[2]
    return rot

def apply(m, p):
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])

IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

def scene_bounds(gltf, extra=None):
    """Габариты сцены в мировых координатах + число треугольников.
       extra — матрица, которую мысленно накладываем сверху (поворот)."""
    nodes = gltf.get('nodes', [])
    meshes = gltf.get('meshes', [])
    accessors = gltf.get('accessors', [])
    lo = [1e30] * 3
    hi = [-1e30] * 3
    tris = 0

    def walk(idx, parent):
        nonlocal tris
        node = nodes[idx]
        m = mat_mul(parent, mat_from_trs(node))
        if 'mesh' in node:
            for prim in meshes[node['mesh']].get('primitives', []):
                if prim.get('mode', 4) != 4:
                    continue
                pos = prim.get('attributes', {}).get('POSITION')
                if pos is None:
                    continue
                acc = accessors[pos]
                if 'indices' in prim:
                    tris += accessors[prim['indices']]['count'] // 3
                else:
                    tris += acc['count'] // 3
                mn, mx = acc.get('min'), acc.get('max')
                if not mn or not mx:
                    continue
                for i in range(8):
                    corner = (mx[0] if i & 1 else mn[0],
                              mx[1] if i & 2 else mn[1],
                              mx[2] if i & 4 else mn[2])
                    w = apply(m, corner)
                    for k in range(3):
                        lo[k] = min(lo[k], w[k])
                        hi[k] = max(hi[k], w[k])
        for kid in node.get('children', []):
            walk(kid, m)

    base = extra or IDENTITY
    scenes = gltf.get('scenes', [])
    roots = scenes[gltf.get('scene', 0)].get('nodes', []) if scenes else range(len(nodes))
    for r in roots:
        walk(r, base)

    if lo[0] > hi[0]:
        die('в сцене не нашлось геометрии с габаритами')
    return lo, hi, tris

def rot3(rx, ry):
    """Поворот вокруг X и Y, в градусах."""
    import numpy as np
    cx, sx = math.cos(math.radians(rx)), math.sin(math.radians(rx))
    cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    return my @ mx

def fmt(n):
    return format(int(n), ',d').replace(',', ' ')

# ============================================================
#   ТЕКСТУРЫ
# ============================================================

def shrink_textures(gltf, blob, max_side, quality):
    """Уменьшает картинки внутри файла и заново собирает двоичный блок."""
    try:
        from PIL import Image
    except ImportError:
        print('  · Pillow не установлен — текстуры оставлены как есть')
        print('    (поставить: pip install pillow)')
        return blob, []

    views = gltf.get('bufferViews', [])
    images = gltf.get('images', [])
    if not views:
        return blob, []

    def view_bytes(i):
        v = views[i]
        off = v.get('byteOffset', 0)
        return blob[off:off + v['byteLength']]

    replaced = {}
    report = []
    for img in images:
        if 'bufferView' not in img:
            if 'uri' in img:
                report.append(('external', img.get('uri', '')[:40], 0, 0))
            continue
        vi = img['bufferView']
        data = view_bytes(vi)
        try:
            pic = Image.open(io.BytesIO(data))
            pic.load()
        except Exception:
            continue

        was = (pic.width, pic.height, len(data))
        if max(pic.size) > max_side:
            k = max_side / float(max(pic.size))
            pic = pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))),
                             Image.LANCZOS)

        has_alpha = pic.mode in ('RGBA', 'LA') and pic.getchannel('A').getextrema()[0] < 255
        out = io.BytesIO()
        if has_alpha:
            pic.convert('RGBA').save(out, 'PNG', optimize=True)
            mime = 'image/png'
        else:
            pic.convert('RGB').save(out, 'JPEG', quality=quality, optimize=True,
                                    progressive=True)
            mime = 'image/jpeg'

        new = out.getvalue()
        if len(new) < len(data):
            replaced[vi] = new
            img['mimeType'] = mime
            report.append(('shrunk', '%dx%d -> %dx%d' % (was[0], was[1], pic.width, pic.height),
                           was[2], len(new)))
        else:
            report.append(('kept', '%dx%d' % (was[0], was[1]), was[2], was[2]))

    if not replaced:
        return blob, report

    # пересобираем двоичный блок: у картинок сменился размер, сдвинулись все смещения
    out = bytearray()
    for i, v in enumerate(views):
        data = replaced.get(i)
        if data is None:
            data = view_bytes(i)
        pad = (-len(out)) % 4
        out.extend(b'\x00' * pad)
        v['byteOffset'] = len(out)
        v['byteLength'] = len(data)
        out.extend(data)
    gltf['buffers'][0]['byteLength'] = len(out)
    return bytes(out), report

# ============================================================
#   ГЛАВНОЕ
# ============================================================

def target_from_existing(name):
    """Ширина уже лежащей модели — чтобы скан встал ровно на её место."""
    path = os.path.join(MODELS, name + '.glb')
    if not os.path.exists(path):
        return None
    try:
        gltf, _ = read_glb(path)
        lo, hi, _ = scene_bounds(gltf)
        return max(hi[0] - lo[0], hi[2] - lo[2]) * 100.0
    except SystemExit:
        return None

def known_slugs():
    menu = os.path.join(ROOT, 'menu.js')
    if not os.path.exists(menu):
        return set()
    src = io.open(menu, encoding='utf-8').read()
    return set(re.findall(r"model: 'models/([a-z0-9-]+)\.glb'", src))

def main():
    ap = argparse.ArgumentParser(add_help=True, description='Подготовка скана блюда для сайта')
    ap.add_argument('scan', help='файл .glb с телефона')
    ap.add_argument('name', help='имя позиции, например burger-classic')
    ap.add_argument('--size', type=float, default=0.0,
                    help='натуральная ширина блюда, см (0 = как у текущей модели)')
    ap.add_argument('--tex', type=int, default=2048, help='макс. сторона текстуры')
    ap.add_argument('--quality', type=int, default=82, help='качество JPEG, 60-95')
    ap.add_argument('--rot-x', type=float, default=0.0, dest='rx')
    ap.add_argument('--rot-y', type=float, default=0.0, dest='ry')
    ap.add_argument('--zup', action='store_true',
                    help='скан в системе «Z вверх» — блюдо лежит на боку')
    ap.add_argument('--floor', default='auto',
                    help='срезать стол: auto (по умолчанию), off, либо проценты высоты')
    ap.add_argument('--radius', type=float, default=100.0,
                    help='оставить только центр: проценты от ширины, например 70')
    ap.add_argument('--speck', type=float, default=2.0,
                    help='обрывки мельче этой доли от модели, %% (по умолчанию 2)')
    ap.add_argument('--dirty', action='store_true', help='не чистить вообще')
    ap.add_argument('--keep', action='store_true', help='не трогать текстуры')
    ap.add_argument('--dry', action='store_true', help='ничего не записывать')
    a = ap.parse_args()

    if not os.path.exists(a.scan):
        die('файл не найден: %s' % a.scan)
    name = a.name.strip().lower().replace('.glb', '')

    slugs = known_slugs()
    if slugs and name not in slugs:
        print('  ! В меню нет позиции «%s».' % name)
        print('    Известные:', ', '.join(sorted(slugs)[:8]), '…')
        print('    Файл всё равно будет создан — проверьте поле model в menu.js.\n')

    src_size = os.path.getsize(a.scan)
    ext = os.path.splitext(a.scan)[1].lower()

    if ext == '.obj':
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from objkit import load_obj
            gltf, blob = load_obj(a.scan)
        except Exception as err:
            die('не удалось разобрать OBJ: %s' % err)
        print('\n  Скан: %s (OBJ, текстура вшивается внутрь)' % os.path.basename(a.scan))
    elif ext == '.glb':
        gltf, blob = read_glb(a.scan)
        print('\n  Скан: %s' % os.path.basename(a.scan))
    else:
        die('нужен .obj или .glb, а не «%s». В приложении при выгрузке\n'
            '     выбирайте OBJ — этот формат отдают все сканеры' % (ext or '?'))

    bufs = gltf.get('buffers', [])
    if len(bufs) != 1 or 'uri' in bufs[0]:
        die('файл ссылается на внешние данные. Выгрузите модель одним файлом')

    print('  Размер исходника: %.1f МБ' % (src_size / 1048576.0))

    # --- габариты и поворот ---
    prims = meshkit.decode(gltf, blob)
    if not prims:
        die('в файле нет треугольников')
    source = meshkit.take_source(gltf, blob, os.path.dirname(os.path.abspath(a.scan)))

    rx = a.rx - 90.0 if a.zup else a.rx
    if rx or a.ry:
        meshkit.transform(prims, rot=rot3(rx, a.ry))

    tris_before = meshkit.tri_count(prims)
    lo, hi = meshkit.bounds(prims)
    print('  Треугольников: %s' % fmt(tris_before))
    print('  Габариты в файле: %.3f x %.3f x %.3f' % tuple(hi - lo))

    # --- чистка: то, что у профи доводит художник руками ---
    if not a.dirty:
        prims, gone = meshkit.drop_specks(prims, a.speck / 100.0)
        if gone:
            print('  Обрывков в воздухе убрано: %s треугольников' % fmt(gone))

        cut = None
        if a.floor == 'auto':
            cut = meshkit.guess_floor(prims)
            if cut is not None:
                lo2, hi2 = meshkit.bounds(prims)
                share = (cut - lo2[1]) / max(1e-9, hi2[1] - lo2[1]) * 100
                print('  Похоже на стол внизу — срезаю нижние %.0f%% высоты' % share)
        elif a.floor != 'off':
            try:
                pct = float(a.floor)
            except ValueError:
                die('--floor принимает auto, off или число процентов')
            lo2, hi2 = meshkit.bounds(prims)
            cut = lo2[1] + (hi2[1] - lo2[1]) * pct / 100.0
        if cut is not None:
            prims = meshkit.cut_below(prims, cut)
            if not prims:
                die('после среза стола ничего не осталось, попробуйте --floor off')

        if a.radius < 100:
            lo2, hi2 = meshkit.bounds(prims)
            centre = ((lo2[0] + hi2[0]) / 2.0, (lo2[2] + hi2[2]) / 2.0)
            half = max(hi2[0] - lo2[0], hi2[2] - lo2[2]) / 2.0
            prims = meshkit.cut_outside(prims, half * a.radius / 100.0, centre)
            if not prims:
                die('обрезка по радиусу забрала всё, увеличьте --radius')

        prims, _ = meshkit.drop_specks(prims, a.speck / 100.0)
        if not prims:
            die('чистка забрала всё. Посмотрите, что в файле: --dirty')
        after = meshkit.tri_count(prims)
        if after != tris_before:
            print('  Осталось от блюда: %s треугольников' % fmt(after))

    # --- масштаб и посадка на пол ---
    lo, hi = meshkit.bounds(prims)
    dims = hi - lo
    target_cm = a.size or target_from_existing(name) or 12.0
    footprint = max(dims[0], dims[2])
    if footprint <= 1e-9:
        die('нулевые габариты — похоже, скан пустой')
    scale = (target_cm / 100.0) / footprint
    print('  Ставим ширину: %.1f см%s' % (target_cm, '' if a.size else ' (как у текущей модели)'))

    meshkit.transform(prims, scale=scale,
                      offset=(-(lo[0] + hi[0]) / 2.0 * scale,
                              -lo[1] * scale,
                              -(lo[2] + hi[2]) / 2.0 * scale))

    tris = meshkit.tri_count(prims)
    gltf, blob = meshkit.encode(prims, source)

    # --- текстуры ---
    if not a.keep:
        blob, report = shrink_textures(gltf, blob, a.tex, a.quality)
        for kind, what, was, now in report:
            if kind == 'shrunk':
                print('  Текстура %s: %.1f МБ -> %.1f МБ' % (what, was / 1048576.0, now / 1048576.0))
            elif kind == 'external':
                print('  ! Текстура лежит отдельным файлом (%s) — она потеряется.' % what)
                print('    Выгрузите из приложения GLB со встроенными текстурами.')

    # --- запись ---
    dest = os.path.join(MODELS, name + '.glb')
    if a.dry:
        print('\n  Пробный запуск: файл не записан.\n')
        return

    if os.path.exists(dest):
        backup = dest + '.bak'
        if not os.path.exists(backup):
            os.replace(dest, backup)
            print('  Прежняя модель сохранена как %s' % os.path.basename(backup))

    os.makedirs(MODELS, exist_ok=True)
    out_size = write_glb(gltf, blob, dest)

    check_gltf, _ = read_glb(dest)
    lo2, hi2, _ = scene_bounds(check_gltf)
    print('\n  Готово: models/%s.glb' % name)
    print('  Размер: %.1f МБ (исходник %.1f МБ)' % (out_size / 1048576.0, src_size / 1048576.0))
    print('  На столе займёт: %.1f x %.1f см, высота %.1f см'
          % ((hi2[0] - lo2[0]) * 100, (hi2[2] - lo2[2]) * 100, (hi2[1] - lo2[1]) * 100))

    if tris > WARN_TRIS:
        print('\n  ! Треугольников многовато (%s).' % format(tris, ',d').replace(',', ' '))
        print('    Телефон потянет, но грузиться будет долго. Выгрузите скан')
        print('    из приложения ещё раз, выбрав среднюю или низкую детализацию.')
    if out_size > WARN_BYTES:
        print('\n  ! Файл тяжёлый (%.1f МБ). Гостю на мобильном интернете это' % (out_size / 1048576.0))
        print('    заметно. Попробуйте --tex 1024, либо пересоберите скан полегче.')

    print('\n  Проверьте: python tools/preview.py %s\n' % name)

if __name__ == '__main__':
    main()
