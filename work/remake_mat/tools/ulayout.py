"""A permutation's Material uniform buffer as the game's shader reads it: each row (cbN[i]) and component with the
uniform expression it holds, written compactly - for reading a shader's cb references.
    ulayout.py <permutation>"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remake_ue


def expr(e):
    op = e.get('op')
    if op == 'const':
        v = e['value'][:{1: 1, 2: 2, 4: 3, 8: 4}.get(e.get('type'), 4)]
        return '(' + ','.join('%g' % x for x in v) + ')'
    if op == 'vparam':
        return e['name']
    if op == 'sparam':
        return e['name']
    if op == 'swizzle':
        return '%s.%s' % (expr(e['x']), ''.join('xyzw'[i] if i >= 0 else '_' for i in e['index'][:e.get('n', 4)]))
    if op == 'append':
        return 'append(%s, %s)' % (expr(e['a']), expr(e['b']))
    if op == 'math':
        return '(%s %s %s)' % (expr(e['a']), e['math'], expr(e['b']))
    if op == 'clamp':
        return 'clamp(%s)' % expr(e['x'])
    if op in ('max', 'min'):
        return '%s(%s, %s)' % (op, expr(e['a']), expr(e['b']))
    if op in ('frac', 'squareroot'):
        return '%s(%s)' % (op, expr(e['x']))
    if op == 'texprop':
        return 'size(%s)' % e['texture']['name']
    return '<%s>' % op


def layout(perm):
    u = remake_ue.uniform_sets()[perm]
    rows = []
    for v in u['vectors']:
        rows.append([expr(v)])
    sc = [expr(s) for s in u['scalars']]
    for j in range(0, len(sc), 4):
        rows.append(sc[j:j + 4])
    return rows


def main():
    for i, r in enumerate(layout(sys.argv[1])):
        if len(r) == 1:
            print('[%d] %s' % (i, r[0]))
        else:
            print('[%d] %s' % (i, '  |  '.join('%s=%s' % ('xyzw'[k], x) for k, x in enumerate(r))))


if __name__ == '__main__':
    main()
