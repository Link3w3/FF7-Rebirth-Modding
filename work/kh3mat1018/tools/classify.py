import os, sys, glob, json, collections
sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k
root = sys.argv[1]
out = {}
cnt = collections.Counter()
for p in sorted(glob.glob(os.path.join(root, '**', '*.uasset'), recursive=True)):
    try:
        pk = k.Package(open(p, 'rb').read(), open(p[:-7] + '.uexp', 'rb').read())
        tops = [e for e in pk.exports if e['outer'] == 0]
        cls = [pk.class_name(e) for e in tops]
        main = [c for c in cls if c not in ('MetaData',)]
        c = main[0] if main else cls[0]
    except Exception as e:
        c = 'ERR:' + str(e)[:60]
    rel = os.path.relpath(p, root)[:-7]
    out[rel] = c
    cnt[c] += 1
json.dump(out, open(sys.argv[2], 'w'), indent=0)
for c, n in cnt.most_common():
    print(n, c)
