"""Summarize editor-saved UE4.26 packages: folder, imports, exports, and key object references of the main export."""
import sys, struct, os
sys.path.insert(0, '/work/run1013/tools')
from pkg426 import Pkg, read_props

def cls_name(P, idx):
    if idx < 0: return P.imports[-idx - 1][3]
    if idx > 0: return P.exports[idx - 1]['name']
    return 'Class'

def ref(P, idx):
    if idx < 0: return P.import_path(idx)
    if idx > 0: return 'export:' + P.exports[idx - 1]['name']
    return 'None'

for path in sys.argv[1:]:
    data = open(path, 'rb').read()
    P = Pkg(data)
    print('=' * 100)
    print(os.path.relpath(path), 'bytes=%d ue4=%d lic=%d editor=%s folder=%r names=%d' % (len(data), P.ue4, P.lic, P.editor, P.folder, len(P.names)))
    pk = sorted({P.import_path(-(i + 1)).split('.')[0] for i, im in enumerate(P.imports) if im[2] == 0})
    print('  import packages (%d):' % len(pk))
    for p in pk: print('    ', p)
    print('  exports (%d):' % len(P.exports))
    for i, e in enumerate(P.exports[:40]):
        print('    %3d %-28s %-40s size=%d outer=%d' % (i + 1, cls_name(P, e['cls']), e['name'], e['size'], e['outer']))
    if len(P.exports) > 40: print('    ...')
    # main export props
    main = [e for e in P.exports if e['outer'] == 0]
    for e in main[:3]:
        props = []
        try:
            read_props(P, data, e['offset'], e['offset'] + e['size'], 0, props)
        except Exception as ex:
            print('  props error', ex)
        print('  props of %s (%s):' % (e['name'], cls_name(P, e['cls'])))
        for (depth, name, typ, extra, aidx, vp, size) in [x for x in props if x[0] == 0]:
            val = ''
            if typ in ('ObjectProperty', 'SoftObjectProperty') and size >= 4 and typ == 'ObjectProperty':
                val = ref(P, struct.unpack_from('<i', data, vp)[0])
            elif typ == 'IntProperty': val = struct.unpack_from('<i', data, vp)[0]
            elif typ == 'FloatProperty': val = struct.unpack_from('<f', data, vp)[0]
            elif typ == 'NameProperty': val = P.n(*struct.unpack_from('<ii', data, vp))
            elif typ == 'BoolProperty': val = extra
            elif typ == 'ArrayProperty' and extra == 'ObjectProperty':
                n = struct.unpack_from('<i', data, vp)[0]
                val = [ref(P, struct.unpack_from('<i', data, vp + 4 + 4 * k)[0]) for k in range(min(n, 12))]
            print('    ' + '  ' * depth + '%s : %s %s %s' % (name, typ, extra if typ not in ('BoolProperty',) else '', val))
