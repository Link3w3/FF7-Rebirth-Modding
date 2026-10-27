import sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/weap1012/tools', '/work/vincentfix', '/work/charaspecmod']
import charaspec_patch as cp
def text(v):
    if isinstance(v, bytes):
        try: return v.decode('utf-16-le').rstrip('\x00')
        except Exception: return repr(v)
    if isinstance(v, list): return '[' + ', '.join(text(x) for x in v) + ']'
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str): return v[0] if v[1] == 0 else '%s_%d' % (v[0], v[1] - 1)
    return str(v)
def load(path):
    z, e, m, d = cp.decode(open(path, 'rb').read())
    fields = [f[0][0] for f in d.fields]
    rows = {k[0][0] if k[0][1] == 0 else '%s_%d' % (k[0][0], k[0][1] - 1): r for k, r in zip(d.keys, d.rows)}
    return fields, rows
def diff(name, van, mod, only=None, limit=60):
    fv, rv = load(van); fm, rm = load(mod)
    print('=====', name, 'fields', len(fv), 'rows', len(rv), '->', len(rm), 'same fields' if fv == fm else 'FIELDS DIFFER')
    if fv != fm:
        print('   van', fv); print('   mod', fm); return
    added = sorted(set(rm) - set(rv)); removed = sorted(set(rv) - set(rm))
    print('   added %d: %s' % (len(added), added[:30]))
    print('   removed %d: %s' % (len(removed), removed[:30]))
    changed = [k for k in rv if k in rm and rv[k] != rm[k]]
    print('   changed %d: %s' % (len(changed), changed[:80]))
    n = 0
    for k in changed:
        if only and not any(o in k for o in only): continue
        n += 1
        if n > limit: break
        print('   --', k)
        for f, a, b in zip(fv, rv[k], rm[k]):
            if a != b: print('      %-32s %s -> %s' % (f, text(a)[:160], text(b)[:160]))
if __name__ == '__main__':
    name = sys.argv[1]
    only = sys.argv[2:] or None
    diff(name, 'gx/van3/pkgs/DataObject__Resident__%s.uasset' % name, 'gx/fpys/pkgs/DataObject__Resident__%s.uasset' % name, only)
