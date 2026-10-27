"""The End editor's property schema for Cascade particle systems, for the Remake effect converter (rmcascade.py), as a
small JSON file (the End usmap is zstd-compressed and large; the importer runs on a plain Python).
    fxschema_gen.py <End usmap (uncompressed)> <out end_fx_schema.json>
Every class whose name starts with Particle, Distribution, EndParticle, EndEffect, Vfx (and their supers), and every
struct and enum they use, transitively."""
import json, sys
sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx.usmap import Usmap

ROOT_PREFIXES = ('Particle', 'Distribution', 'EndParticle', 'EndEffect', 'VfxParticle', 'VfxDistribution', 'InterpCurve',
                 'RawDistribution', 'EmitterDynamicParameter')


def tdesc(pt, need, enums):
    t = pt.type[:-8] if pt.type.endswith('Property') else pt.type
    if pt.type == 'StructProperty':
        need.add(pt.struct)
        return {'t': 'Struct', 's': pt.struct}
    if pt.type == 'EnumProperty':
        enums.add(pt.enum)
        inner = pt.inner.type[:-8] if pt.inner is not None else 'Byte'
        return {'t': 'Enum', 'e': pt.enum, 'u': inner}
    if pt.type in ('ArrayProperty', 'SetProperty', 'OptionalProperty'):
        return {'t': t, 'i': tdesc(pt.inner, need, enums)}
    if pt.type == 'MapProperty':
        return {'t': 'Map', 'k': tdesc(pt.inner, need, enums), 'v': tdesc(pt.value, need, enums)}
    return {'t': t}


def main(usmap_path, out):
    u = Usmap(usmap_path)
    need = set(n for n in u.structs if n.startswith(ROOT_PREFIXES))
    need |= {'ParticleSystem', 'FXSystemAsset', 'Object'}
    done, enums, out_structs = set(), set(), {}
    while need:
        n = need.pop()
        if n in done:
            continue
        done.add(n)
        s = u.structs.get(n)
        if s is None:
            continue
        if s.super:
            need.add(s.super)
        props = []
        for p in s.props:
            props.append([p.name, p.array_dim, tdesc(p.ptype, need, enums)])
        out_structs[n] = {'super': s.super, 'props': props}
    data = {'structs': out_structs, 'enums': {e: u.enums.get(e, []) for e in sorted(enums)}}
    json.dump(data, open(out, 'w'), indent=0, sort_keys=True)
    print(len(out_structs), 'structs/classes,', len(enums), 'enums ->', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
