"""Scan Rebirth's effects (rbtpl) for renderer material bindings: per material parameter name, the NiagaraVariable type
(vfx1 hash, utype) its bindings use, whether it is a texture, and example constant values. -> bindtypes.json"""
import glob, json, sys, collections
sys.path[:0] = ['/work/nconv/tools', '/work/fx1018/editor/Python', '/work/iostore',
                '/work/cs']
import nio, scriptobjs
from zen import Zen

sp, _ = scriptobjs.load()
types = {}
counts = collections.Counter()
for path in sorted(glob.glob('/work/remakefx/rbtpl/End/Content/**/*.uasset', recursive=True)):
    try:
        z = Zen(open(path, 'rb').read())
    except Exception:
        continue
    for i in range(len(z.exports)):
        try:
            cls = nio.class_name(z, i, sp) if hasattr(nio, 'class_name') else None
        except Exception:
            cls = None
        try:
            c, v, extra, data = nio.read_export(z, i, sp)
        except Exception:
            continue
        if c not in ('NiagaraSpriteRendererProperties', 'NiagaraMeshRendererProperties', 'NiagaraRibbonRendererProperties'):
            continue
        mpb = v.value.get('MaterialParameterBindings')
        if mpb is None or mpb.zero:
            continue
        for b in mpb.value:
            bv = b.value
            nm = bv['MaterialParameterName'].value
            td = bv['NiagaraVariable'].value['td']['vfx1']
            key = (td['hash'], td['utype'])
            ent = types.setdefault(nm, {'types': {}, 'texture': False, 'dynamic': 0, 'static': 0})
            ent['types']['%d:%d' % key] = ent['types'].get('%d:%d' % key, 0) + 1
            if bv['m_bIsTexture'].value:
                ent['texture'] = True
            if bv['m_bIsDynamic'].value:
                ent['dynamic'] += 1
            else:
                ent['static'] += 1
            counts[nm] += 1
json.dump(types, open('bindtypes.json', 'w'), indent=1, sort_keys=True)
print(len(types), 'parameter names')
for nm, n in counts.most_common():
    e = types[nm]
    print('%5d %-48s %s %s' % (n, nm, e['types'], 'TEX' if e['texture'] else ''))
