"""Extract and disassemble (Microsoft's d3dcompiler_47 under Wine, hex literals) the base pass shaders of every Remake
renderer package: per package, one vertex factory (static mesh first), the base pass pixel shaders (no light map, no
sky light; with and without per-object coverage) and vertex shader, and the depth-only pixel shader.
    dis_all.py [name filter]"""
import sys, os, glob, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shadermap418

R = '/work/remake_mat/paks/GameContents/Renderer'
OUT = '/work/remake_mat/dis'
VF_ORDER = ['FLocalVertexFactory', 'TGPUSkinVertexFactoryfalse', 'FParticleSpriteVertexFactory', 'FMeshParticleVertexFactory',
            'FInstancedStaticMeshVertexFactory', 'TGPUSkinNormalDeformerVertexFactoryfalse', 'FGPUSpriteVertexFactory',
            'FParticleBeamTrailVertexFactory']
WANT = ['TBasePassPSFNoLightMapPolicyNoSkylightNoPerObjectCoverage', 'TBasePassPSFNoLightMapPolicyNoSkylightPerObjectCoverage',
        'TBasePassVSFNoLightMapPolicy', 'FDepthOnlyPS', 'TDepthOnlyVS<false>']


def winpath(p):
    return 'Z:' + p.replace('/', '\\')


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ''
    index = {}
    lines = []
    for path in sorted(glob.glob(R + '/Material/*.uasset')) + sorted(glob.glob(R + '/MaterialInstance/*.uasset')):
        name = os.path.basename(path)[:-7]
        if flt and flt not in name:
            continue
        pk, sh = shadermap418.shaders(path)
        if not sh:
            continue
        vfs = {s['vf'] for s in sh}
        vf = next((v for v in VF_ORDER if v in vfs), sorted(v for v in vfs if v)[0] if any(vfs) else None)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        entry = {'vf': vf, 'vfs': sorted(v for v in vfs if v), 'shaders': {}}
        for s in sh:
            if s['vf'] != vf or s['type'] not in WANT:
                continue
            key = s['type'].replace('<', '_').replace('>', '_')
            if key in entry['shaders']:
                key += '_%d' % len([k for k in entry['shaders'] if k.startswith(key)])
            f = os.path.join(d, key + '.dxbc')
            open(f, 'wb').write(s['dxbc'])
            entry['shaders'][key] = {'type': s['type'], 'freq': s['freq'], 'instructions': s['instructions'], 'hash': s['hash'],
                                     'asm': f[:-5] + '.asm'}
            lines.append('%s|%s' % (winpath(f), winpath(f[:-5] + '.asm')))
        index[name] = entry
    lst = os.path.join(OUT, 'list.txt')
    open(lst, 'w').write('\r\n'.join(lines) + '\r\n')
    env = dict(os.environ, WINEPREFIX='/tmp/wpfx', WINEDEBUG='-all', WINEDLLOVERRIDES='d3dcompiler_47=n')
    p = subprocess.run(['/usr/lib/wine/wine64', '/work/fxcw/fxcw.exe', 'Z:\\work\\fxcw\\d3dcompiler_47.dll',
                        '--list', winpath(lst)], capture_output=True, text=True, env=env)
    print(p.stdout.strip(), p.stderr.strip()[-300:])
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)
    print(len(index), 'packages,', len(lines), 'shaders')


if __name__ == '__main__':
    main()
