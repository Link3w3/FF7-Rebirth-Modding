"""Dump and disassemble (Microsoft's d3dcompiler_47 under Wine, hex literals) the shaders of the Crisis Core Reunion
material permutations Sephiroth's materials use: per permutation (a master or a static-permutation instance), the
highest quality shader map's shaders for one vertex factory (GPU skin), with their types, resource bindings and
uniform expression set.
    dis427.py [name filter]       writes dis427/<permutation>/<resource>_<type>.{dxbc,asm}, index.json, bindings"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cc427
import d3d427
from shaderlib import Archive, FREQ

ROOT = '/work/ccmat'
PK = ROOT + '/pkgs/Fair'
OUT = ROOT + '/dis427'
ARCHIVE = ROOT + '/ShaderArchive-CCFF7R_Chunk0-PCD3D_SM5.ushaderbytecode'
PERMUTATIONS = {
    'M_ch_StandardSS': PK + '/00_Common/Materials/M/ch/M_ch_StandardSS.uasset',
    'M_ch_StandardSS_Masked': PK + '/00_Common/Materials/M/ch/M_ch_StandardSS_Masked.uasset',
    'MI_ch_Eye2_ad': PK + '/Character/00_Common/Materials/MI_ch_Eye2_ad.uasset',
    'MI_ch_Eyelash': PK + '/Character/00_Common/Materials/MI_ch_Eyelash.uasset',
    'MI_CH_sephiroth_hair': PK + '/Character/01_named/sephiroth/Material/MI_CH_sephiroth_hair.uasset',
    'MI_CH_sephiroth_hair_StackTranslucent': PK + '/Character/01_named/sephiroth/Material/MI_CH_sephiroth_hair_StackTranslucent.uasset',
    'MI_ch_Human_Skin': PK + '/Character/00_Common/Materials/MI_ch_Human_Skin.uasset',
    'MI_ch_Human_Mouth': PK + '/Character/00_Common/Materials/MI_ch_Human_Mouth.uasset',
}
VF = 'TGPUSkinVertexFactoryDefault'


def winpath(p):
    return 'Z:' + p.replace('/', '\\')


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ''
    a = Archive(ARCHIVE)
    lines = []
    index = {}
    for name, path in PERMUTATIONS.items():
        if flt and flt not in name:
            continue
        maps = [r for r in cc427.shader_maps(cc427.Pkg(path)) if r['valid']]
        res = next((r for r in maps if r['quality'] == 'Num'), maps[-1])
        m = a.map_index[bytes.fromhex(res['map_hash'])]
        sh = a.map_shaders(m)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        entry = {'package': path, 'map': res['map_hash'], 'quality': res['quality'], 'shaders': {}, 'uniform': res['uniform']}
        bindings = {}
        done = set()
        for s in res['shaders']:
            if s['vf'] != VF or s['resource'] in done:
                continue
            done.add(s['resource'])
            code, freq = a.code(sh[s['resource']])
            dx, at = a.dxbc(code)
            key = '%02d_%s' % (s['resource'], s['type'].replace('<', '_').replace('>', '_'))
            f = os.path.join(d, key + '.dxbc')
            open(f, 'wb').write(dx)
            open(f[:-5] + '.bin', 'wb').write(code)
            types = sorted({x['type'] for x in res['shaders'] if x['vf'] == VF and x['resource'] == s['resource']})
            entry['shaders'][key] = {'types': types, 'freq': FREQ.get(freq, freq), 'instructions': s['instructions'],
                                     'archive_index': sh[s['resource']], 'asm': f[:-5] + '.asm'}
            b = d3d427.binding(code)
            bindings[key] = {'cb': b['cb'], 't': {str(k): list(v) for k, v in b['t'].items()},
                             's': {str(k): list(v) for k, v in b['s'].items()},
                             'srv': {str(k): list(v) for k, v in b['srv'].items()}}
            if not os.path.exists(f[:-5] + '.asm'):
                lines.append('%s|%s' % (winpath(f), winpath(f[:-5] + '.asm')))
        json.dump(bindings, open(os.path.join(d, 'bindings.json'), 'w'), indent=1)
        index[name] = entry
        print('%-40s map %s: %d %s shaders' % (name, res['map_hash'][:10], len(entry['shaders']), VF))
    if lines:
        lst = os.path.join(OUT, 'list.txt')
        open(lst, 'w').write('\r\n'.join(lines) + '\r\n')
        env = dict(os.environ, WINEPREFIX='/tmp/wpfx', WINEDEBUG='-all', WINEDLLOVERRIDES='d3dcompiler_47=n')
        p = subprocess.run(['/usr/lib/wine/wine64', '/work/fxcw/fxcw.exe', 'Z:\\work\\fxcw\\d3dcompiler_47.dll',
                            '--list', winpath(lst)], capture_output=True, text=True, env=env)
        print(p.stdout.strip()[-400:], p.stderr.strip()[-300:])
    old = {}
    ip = os.path.join(OUT, 'index.json')
    if os.path.exists(ip):
        old = json.load(open(ip))
    old.update(index)
    json.dump(old, open(ip, 'w'), indent=1)


if __name__ == '__main__':
    main()
