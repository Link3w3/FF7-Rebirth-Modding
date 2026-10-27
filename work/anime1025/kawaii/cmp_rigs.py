import json, math, sys
a = json.load(open(sys.argv[1]))['bones']
b = json.load(open(sys.argv[2]))['bones']
A = {x['name']: x for x in a}; B = {x['name']: x for x in b}
print('bones', len(a), len(b), 'same order:', [x['name'] for x in a] == [x['name'] for x in b])
only_a = [n for n in A if n not in B]; only_b = [n for n in B if n not in A]
print('only in first', only_a[:20], 'only in second', only_b[:20])
par = [n for n in A if n in B and A[n]['parent'] != B[n]['parent']]
print('parent differs', par[:20])
def qang(p, q):
    d = abs(sum(x * y for x, y in zip(p, q)))
    return math.degrees(2 * math.acos(min(1.0, d)))
worst_t = []; worst_q = []; worst_lt = []; worst_lq = []; worst_s = []
for n in A:
    if n not in B: continue
    x, y = A[n], B[n]
    worst_t.append((math.dist(x['t'], y['t']), n))
    worst_q.append((qang(x['q'], y['q']), n))
    worst_lt.append((math.dist(x['local_t'], y['local_t']), n))
    worst_lq.append((qang(x['local_q'], y['local_q']), n))
    worst_s.append((max(abs(p - q) for p, q in zip(x['scale'], y['scale'])), n))
for lab, w in (('component t (cm)', worst_t), ('component q (deg)', worst_q), ('local t (cm)', worst_lt), ('local q (deg)', worst_lq), ('scale', worst_s)):
    w.sort(reverse=True)
    print(lab, 'max', ['%.4g %s' % v for v in w[:6]], 'median %.3g' % w[len(w)//2][0])
