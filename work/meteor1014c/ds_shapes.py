import sys, io, contextlib, collections
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
with contextlib.redirect_stdout(io.StringIO()):
    dm = B.Table(open(B.GAME_DAMAGE, 'rb').read())
by = collections.defaultdict(list)
for k, i in dm.at.items():
    r = dm.rows[i]
    by[dm.get(r, 'CollisionType')].append((k, dm.get(r, 'CollisionParameter_Array'), dm.get(r, 'ControlType'), dm.get(r,'CreateBasePos')))
for t in sorted(by):
    rows = by[t]
    lens = collections.Counter(len(p) for _, p, _, _ in rows)
    print('CollisionType', t, len(rows), 'rows; param counts', dict(lens))
    big = sorted(rows, key=lambda x: -(x[1][0] if x[1] else 0))[:12]
    for k, p, c, b in big:
        print('    %-45s %s control=%s base=%s' % (k, p, c, b))
