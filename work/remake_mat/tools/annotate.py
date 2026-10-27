"""A permutation's shader with its Material buffer reads named (from the uniform expressions): for reading.
    annotate.py <permutation> [shader key] [first line] [last line]"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remake_ue
import ulayout

DIS = remake_ue.DIS


def main():
    perm = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else remake_ue.BASE_PS
    lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    hi = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
    asm = open(os.path.join(DIS, perm, key + '.asm'), encoding='latin-1').read().replace('\x00', '')
    bind = json.load(open(os.path.join(DIS, perm, 'bindings.json')))[key]
    cbn = bind['cb']
    rows = ulayout.layout(perm)
    mat = cbn.index('Material') if 'Material' in cbn else -1
    view = cbn.index('View') if 'View' in cbn else -1
    texs = list(remake_ue.uniform_sets()[perm]['textures2d']) + list(remake_ue.uniform_sets()[perm]['texturescube'])

    def name_cb(m):
        b, i, comps = int(m.group(1)), int(m.group(2)), m.group(3)
        if b == mat and i < len(rows):
            r = rows[i]
            if len(r) == 1:
                return '{%s}.%s' % (r[0], comps)
            return '{' + ','.join(r[ord(c) - ord('x')] if ord(c) - ord('x') < len(r) else '?' for c in comps) + '}'
        if b == view:
            return 'View[%d].%s' % (i, comps)
        return m.group(0)
    lines = [l for l in asm.splitlines() if not l.startswith('//')]
    for n, l in enumerate(lines):
        if n < lo or n > hi:
            continue
        l = re.sub(r'cb(\d+)\[(\d+)\]\.([xyzw]+)', name_cb, l)

        def name_t(m):
            t = m.group(1)
            ub, res = bind['t'].get(t, ['?', -1])
            if ub == 'Material' and res // 2 < len(texs):
                return 't%s<%s>' % (t, texs[res // 2]['name'])
            return 't%s<%s %s>' % (t, ub, res)
        l = re.sub(r'\bt(\d+)\.', lambda m: name_t(m) + '.', l)
        print('%4d %s' % (n, l))


if __name__ == '__main__':
    main()
