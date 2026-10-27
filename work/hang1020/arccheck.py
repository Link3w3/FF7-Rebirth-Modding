"""Check every package of some mod containers: export bundles well formed, the graph's arcs inside the bundle counts of
this package and of the packages they come from (mod containers' own store entries, retail headers where known), the
graph's imported packages the same as the store entry's."""
import struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/weap1012/tools',
                '/work/vincentfix', '/work/evil1013/tools']
from iostore import Toc
from hdr import parse_header
from zen import Zen

def graph(data, z):
    g = z.graph_off
    n = struct.unpack_from('<i', data, g)[0]; g += 4
    out = []
    for k in range(n):
        pid, arcs = struct.unpack_from('<Qi', data, g); g += 12
        out.append((pid, [struct.unpack_from('<ii', data, g + 8 * a) for a in range(arcs)])); g += 8 * arcs
    return out

def bundles(data, z, count):
    p = z.eb_off
    heads = [struct.unpack_from('<II', data, p + 8 * k) for k in range(count)]
    total = 2 * len(z.exports)
    ents = [struct.unpack_from('<II', data, p + 8 * count + 8 * k) for k in range(total)]
    return heads, ents

def main(utocs):
    stores, tocs = {}, []
    for u in utocs:
        t = Toc(u)
        heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
        _, st = parse_header(t.read(heads[0]))
        tocs.append((u, t, st))
        for pid, e in st.items():
            stores.setdefault(pid, []).append((u.rsplit('/', 1)[-1], e))
    retail = {}
    for h in ('/work/retailhdr/pakchunk4_header.bin', '/work/retailhdr/pakchunk10_header.bin'):
        try:
            _, st = parse_header(open(h, 'rb').read())
            retail.update(st)
        except Exception as ex:
            print('header', h, ex)
    bad = 0
    for u, t, st in tocs:
        for i in range(t.entries):
            if t.chunk_type(i) != 2:
                continue
            pid = t.chunk_id64(i)
            e = st[pid]
            data = t.read(i)
            z = Zen(data)
            name = t.files.get(i, '%016x' % pid)
            probs = []
            if e['export_count'] != len(z.exports):
                probs.append('store export_count %d, package %d' % (e['export_count'], len(z.exports)))
            nb = e['export_bundle_count']
            heads, ents = bundles(data, z, nb)
            if sum(c for f, c in heads) != 2 * len(z.exports):
                probs.append('bundle entries %d != 2 x %d exports' % (sum(c for f, c in heads), len(z.exports)))
            seen = {}
            for k, (f, c) in enumerate(heads):
                for idx, cmd in ents[f:f + c]:
                    seen.setdefault(idx, []).append((cmd, k))
            for idx in range(len(z.exports)):
                cmds = seen.get(idx, [])
                if sorted(c for c, k in cmds) != [0, 1]:
                    probs.append('export %d commands %s' % (idx, cmds))
                elif [k for c, k in cmds if c == 0][0] > [k for c, k in cmds if c == 1][0]:
                    probs.append('export %d serialized before created' % idx)
            gr = graph(data, z)
            gids = [g for g, a in gr]
            if sorted(gids) != sorted(e['imports']):
                probs.append('graph packages %d vs store imports %d (graph-only %s, store-only %s)' % (
                    len(gids), len(e['imports']), ['%016x' % x for x in set(gids) - set(e['imports'])][:4], ['%016x' % x for x in set(e['imports']) - set(gids)][:4]))
            for g, arcs in gr:
                if g in stores:
                    their = max(se['export_bundle_count'] for _, se in stores[g])
                    where = stores[g][0][0]
                elif g in retail:
                    their = retail[g]['export_bundle_count']; where = 'retail'
                else:
                    their = None; where = '?'
                for fr, to in arcs:
                    if not (0 <= to < nb):
                        probs.append('arc to bundle %d of %d' % (to, nb))
                    if fr != -1:
                        if their is None:
                            if fr != 0:
                                probs.append('arc from bundle %d of %016x (unknown package)' % (fr, g))
                        elif not (0 <= fr < their):
                            probs.append('arc from bundle %d of %016x (%s has %d)' % (fr, g, where, their))
            dup = [w for w, _ in stores[pid] if w != u.rsplit('/', 1)[-1]]
            if dup:
                probs.append('also in ' + ', '.join(dup))
            if pid in retail:
                r = retail[pid]
                if (r['export_count'], r['export_bundle_count']) != (e['export_count'], nb):
                    probs.append('replaces a retail package with exports/bundles %d/%d (here %d/%d)' % (r['export_count'], r['export_bundle_count'], e['export_count'], nb))
            if probs:
                bad += 1
                print('%s: %s' % (name.replace('../../../End/Content/', ''), '; '.join(probs)))
    print('checked', sum(1 for u, t, st in tocs for i in range(t.entries) if t.chunk_type(i) == 2), 'packages,', bad, 'with notes')

if __name__ == '__main__':
    main(sys.argv[1:])
