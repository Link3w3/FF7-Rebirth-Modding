"""Undefined UE4SS (RC::) symbols of an object that UE4SS.dll does not export: defcheck.py <obj> [<obj>...]"""
import subprocess, sys
D = '/data/uploads/rebirth-materials/ue4ss-stage/existing-loader-c0a8d4c/native-sdk-imports/UE4SS.def'
ex = set()
for line in open(D, encoding='utf-8', errors='replace'):
    t = line.split()
    if t and t[0] not in ('EXPORTS', 'LIBRARY') and not t[0].startswith(';'):
        ex.add(t[0].split('=')[0])
for obj in sys.argv[1:]:
    out = subprocess.run(['llvm-nm', '--undefined-only', obj], capture_output=True, text=True).stdout.split('\n')
    und = sorted({l.split()[-1] for l in out if l.strip() and '@RC@@' in l})
    miss = [u for u in und if (u[6:] if u.startswith('__imp_') else u) not in ex]
    print('%s: %d undefined UE4SS symbols, %d not exported by UE4SS.dll' % (obj, len(und), len(miss)))
    for m in miss:
        print('   ', m)
