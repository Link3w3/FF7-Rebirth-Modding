import sys
sys.path.insert(0, '/work/aura1014/tools')
import zx
for f in sys.argv[1:]:
    z = zx.load(f)
    print('==', f.split('__')[-1], 'exports:', [(e['name'], e['serial_size']) for e in z.exports], 'imports', len(z.imports))
    print('  ', ' | '.join(z.names))
