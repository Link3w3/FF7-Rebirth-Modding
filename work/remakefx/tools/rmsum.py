"""Summarize Remake Cascade effects: per emitter its material, material parameters, type data, modules.
    rmsum.py <.uasset>..."""
import json, sys
sys.path[:0] = ['/work/remakefx/tools']
import rmdump, uprops


def dist_desc(d):
    """a Remake raw distribution (dict) -> short text"""
    if not isinstance(d, dict):
        return repr(d)
    t = d.get('Table') or {}
    op = t.get('Op', 0)
    if d.get('Distribution') and not isinstance(d.get('Distribution'), int):
        return 'dist %s' % d['Distribution']
    if op == 0:
        return 'const %s' % json.dumps(d.get('m_VfxValue', d.get('MinValue', 0)))
    if op == 1:
        vals = t.get('Values') or []
        n = t.get('EntryCount', 0)
        st = t.get('EntryStride', 1) or 1
        first = vals[:st]
        last = vals[(n - 1) * st:n * st] if n else []
        return 'curve n%d %s..%s' % (n, [round(x, 3) for x in first], [round(x, 3) for x in last])
    if op == 2:
        return 'random %s..%s' % (json.dumps(d.get('MinValueVec', d.get('MinValue'))), json.dumps(d.get('MaxValueVec', d.get('MaxValue'))))
    return 'op%d' % op


def matparams(mp):
    out = []
    for k, lst in (mp or {}).items():
        if not isinstance(lst, list):
            out.append('%s=%s' % (k, lst))
            continue
        for x in lst:
            if not isinstance(x, dict):
                out.append('%s:%r' % (k, x))
                continue
            nm = x.get('m_ParamName')
            if 'm_ValueXYZ' in x:
                out.append('%s = %s | w %s' % (nm, dist_desc(x['m_ValueXYZ']), dist_desc(x.get('m_ValueW'))))
            elif 'm_Value' in x:
                out.append('%s = %s' % (nm, dist_desc(x['m_Value'])))
            else:
                out.append('%s %s' % (nm, json.dumps({kk: vv for kk, vv in x.items() if kk not in ('m_ParameterId', 'm_GroupName')})))
    return out


def main(path):
    p = rmdump.load(path)
    ex = []
    for i, e in enumerate(p.exports):
        cls, v, end = uprops.read_export(rmdump.S, p, i)
        ex.append((cls, e['name'], rmdump.walk(p, v)))
    by = {'E%d:%s' % (i, n): (c, n, d) for i, (c, n, d) in enumerate(ex)}
    sysd = [d for c, n, d in ex if c == 'ParticleSystem'][0]
    print('#### %s  emitters %d  bounds %s  extra %s' % (path.rsplit('/', 1)[-1], len(sysd['Emitters']),
          json.dumps(sysd.get('FixedRelativeBoundingBox')), json.dumps(sysd.get('m_EndEffectExtraData'))))
    for em in sysd['Emitters']:
        c, n, d = by[em]
        print('== %s (%s) %s' % (d.get('EmitterName'), c, json.dumps({k: v for k, v in d.items() if k not in ('EmitterName', 'LODLevels')})))
        for lod in d.get('LODLevels', [])[:1]:
            lc, ln, ld = by[lod]
            req = by[ld['RequiredModule']][2]
            mat = req.get('Material')
            print('   material %s' % mat)
            print('   required %s' % json.dumps({k: v for k, v in req.items() if k not in ('Material', 'm_EndMaterialParam')})[:600])
            for s in matparams(req.get('m_EndMaterialParam')):
                print('      mp ' + s[:300])
            if ld.get('TypeDataModule'):
                tc, tn, td = by[ld['TypeDataModule']]
                print('   typedata %s %s' % (tc, json.dumps(td)[:300]))
            sc, sn, sd = by[ld['SpawnModule']]
            print('   spawn rate %s burst %s %s' % (dist_desc(sd.get('Rate')), sd.get('BurstList'), '' if sd.get('bEnabled', True) else 'DISABLED'))
            for m in ld.get('Modules', []):
                mc, mn, md = by[m]
                parts = []
                for k, val in md.items():
                    if k in ('LODValidity',):
                        continue
                    if isinstance(val, dict) and ('Table' in val or 'm_VfxValue' in val or 'MinValue' in val):
                        parts.append('%s=%s' % (k, dist_desc(val)))
                    else:
                        parts.append('%s=%s' % (k, json.dumps(val)[:120]))
                print('   %s%s: %s' % (mc, '' if md.get('bEnabled', True) else ' (off)', '; '.join(parts)[:500]))


if __name__ == '__main__':
    for a in sys.argv[1:]:
        main(a)
