"""Survey Rebirth Niagara renderers: per renderer its material, mesh, material parameter bindings and SQEX fields.
    rbrend.py <out.json> <package>..."""
import json, sys
sys.path[:0] = ['/work/nconv/tools', '/work/fx1018/editor/Python', '/work/cs',
                '/work/iostore']
import nio, scriptobjs
from zen import Zen
from rebirth_fx.matcore import resolve_imports


def plain(v):
    if v is None or not hasattr(v, 'kind'):
        return v
    if v.zero:
        return 0
    if v.kind == 'struct':
        return {k: plain(x) for k, x in v.value.items()}
    if v.kind in ('array', 'set'):
        return [plain(x) for x in v.value]
    if v.kind == 'native':
        val = v.value
        if isinstance(val, dict):
            return {k: plain(x) if hasattr(x, 'kind') else (x if not isinstance(x, (bytes, bytearray)) else x.hex()[:32]) for k, x in val.items()}
        if isinstance(val, (list, tuple)):
            return list(val)
        return val
    return v.value


def survey(path, sp):
    z = Zen(open(path, 'rb').read())
    imps = resolve_imports(z)

    def ref(i):
        if not isinstance(i, int) or i == 0:
            return i
        if i < 0:
            return imps.get(-i - 1, '?import%d' % -i)
        return 'E%d:%s' % (i - 1, z.exports[i - 1]['name'])
    rows = []
    emitter_of = {}
    for i in range(len(z.exports)):
        cls, v, extra, data = nio.read_export(z, i, sp)
        if cls == 'NiagaraEmitter':
            for r in (v.value.get('RendererProperties').value if v.value.get('RendererProperties') else []):
                emitter_of[r.value] = (str(v.value['UniqueEmitterName'].value) if v.value.get('UniqueEmitterName') else '?',
                                       bool(v.value['bLocalSpace'].value) if v.value.get('bLocalSpace') and not v.value['bLocalSpace'].zero else False,
                                       'GPU' if (v.value.get('SimTarget') and not v.value['SimTarget'].zero) else 'CPU')
    for i in range(len(z.exports)):
        cls, v, extra, data = nio.read_export(z, i, sp)
        if not cls.endswith('RendererProperties'):
            continue
        f = v.value
        row = {'pkg': path.rsplit('/', 1)[-1], 'export': i, 'cls': cls, 'emitter': emitter_of.get(i + 1)}
        if 'Material' in f:
            row['material'] = ref(plain(f['Material']))
        if 'OverrideMaterials' in f:
            row['material'] = [ref(plain(o.value['ExplicitMat'])) for o in f['OverrideMaterials'].value]
        if 'Meshes' in f:
            row['meshes'] = [ref(plain(m.value['Mesh'])) for m in f['Meshes'].value]
        binds = []
        for x in (f['MaterialParameterBindings'].value if f.get('MaterialParameterBindings') else []):
            b = x.value
            e = {'name': str(b['MaterialParameterName'].value)}
            for k in ('m_ConstantValue', 'm_Texture', 'm_bIsStatic', 'm_bIsDynamic', 'm_bIsTexture', 'm_bIsBuffer', 'm_bIsResidentResource'):
                if k in b and not b[k].zero:
                    pv = plain(b[k])
                    e[k] = ref(pv) if k == 'm_Texture' else pv
            nv = b.get('NiagaraVariable')
            if nv is not None and not nv.zero:
                nm = plain(nv).get('Name') if isinstance(plain(nv), dict) else None
                if nm and nm != 'None':
                    e['var'] = nm
            binds.append(e)
        row['binds'] = binds
        ips = {}
        for k in range(8):
            bb = f.get('VfxMaterialIndependentParameters%d_Binding' % k)
            if bb is None or bb.zero:
                continue
            pb = plain(bb)
            rv = pb.get('RootVariable') if isinstance(pb, dict) else None
            nm = rv.get('Name') if isinstance(rv, dict) else None
            if nm and nm != 'None':
                ips[k] = nm
        row['ips'] = ips
        row['sqex'] = {k: plain(x) for k, x in f.items() if k.startswith('Vfx') and 'IndependentParameters' not in k}
        for k in ('FacingMode', 'Alignment', 'SortMode', 'SubImageSize', 'bOverrideMaterials', 'SourceMode'):
            if k in f:
                row[k] = plain(f[k])
        rows.append(row)
    return rows


if __name__ == '__main__':
    sp, _ = scriptobjs.load()
    out = []
    for p in sys.argv[2:]:
        try:
            out += survey(p, sp)
        except Exception as ex:
            print('FAIL', p, ex)
    json.dump(out, open(sys.argv[1], 'w'), indent=0, default=str)
    print(len(out), 'renderers')
