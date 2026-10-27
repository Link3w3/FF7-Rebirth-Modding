"""Extract and disassemble more of a package's shaders than dis_all.py's base pass set - other shader types (the distortion,
the velocity passes) or another vertex factory's - next to the others in dis/<package>/, merged into dis/index.json.
    dis_extra.py --types T1,T2 [--vf VF] [--suffix S] <name filter>...
A shader of another vertex factory than the package's own is stored under its key with the suffix (e.g. __Sprite)."""
import json
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shadermap418
import dis_all

R = dis_all.R
OUT = dis_all.OUT


def main():
    args = sys.argv[1:]
    types, vf_want, suffix = None, None, ''
    if '--types' in args:
        i = args.index('--types'); types = args[i + 1].split(','); del args[i:i + 2]
    if '--vf' in args:
        i = args.index('--vf'); vf_want = args[i + 1]; del args[i:i + 2]
    if '--suffix' in args:
        i = args.index('--suffix'); suffix = args[i + 1]; del args[i:i + 2]
    flts = args
    index_path = os.path.join(OUT, 'index.json')
    index = json.load(open(index_path))
    lines, touched = [], []
    for name, entry in sorted(index.items()):
        if flts and not any(f in name for f in flts):
            continue
        sub = 'Material' if name.startswith('EndMaterial_') else 'MaterialInstance'
        path = os.path.join(R, sub, name + '.uasset')
        if not os.path.exists(path):
            continue
        pk, sh = shadermap418.shaders(path)
        vf = vf_want or entry['vf']
        d = os.path.join(OUT, name)
        added = {}
        for s in sh:
            if s['vf'] != vf or (types and s['type'] not in types):
                continue
            key = s['type'].replace('<', '_').replace('>', '_') + suffix
            if key in added:
                key += '_%d' % len([k for k in added if k.startswith(key)])
            f = os.path.join(d, key + '.dxbc')
            open(f, 'wb').write(s['dxbc'])
            added[key] = {'type': s['type'], 'freq': s['freq'], 'instructions': s['instructions'], 'hash': s['hash'], 'asm': f[:-5] + '.asm',
                          'vf': vf}
            lines.append('%s|%s' % (dis_all.winpath(f), dis_all.winpath(f[:-5] + '.asm')))
        if added:
            entry['shaders'].update(added)
            touched.append(name)
    if not lines:
        print('no shaders')
        return
    lst = os.path.join(OUT, 'list_extra.txt')
    open(lst, 'w').write('\r\n'.join(lines) + '\r\n')
    env = dict(os.environ, WINEPREFIX='/tmp/wpfx', WINEDEBUG='-all', WINEDLLOVERRIDES='d3dcompiler_47=n')
    p = subprocess.run(['/usr/lib/wine/wine64', '/work/fxcw/fxcw.exe', 'Z:\\work\\fxcw\\d3dcompiler_47.dll',
                        '--list', dis_all.winpath(lst)], capture_output=True, text=True, env=env)
    print(p.stdout.strip()[-300:], p.stderr.strip()[-300:])
    json.dump(index, open(index_path, 'w'), indent=1)
    print(len(touched), 'packages,', len(lines), 'shaders')


if __name__ == '__main__':
    main()
