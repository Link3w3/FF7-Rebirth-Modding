"""Vincent in prologue Cloud's place too: FullyPlayableVincentAssets_P (the installed one, every other chunk byte for byte)
with the CharaSpec rows of Cloud in his SOLDIER uniform (the prologue's Nibelheim, and wherever the game puts Cloud in it:
PC0000_04_Cloud_ZackCostume, _12 Dirty, _18 Age21, _19 DirtyAge21, _23 Wet) made like Cloud's own Vincent row:
ContentsModel PC0011_00_Vincent_Standard, NoBattleCharaSpec and ReserveCharaSpec the row itself (Vincent in the field and in
reserve too; a row that has none keeps none).
    build_prologue.py <installed dir> <out dir>"""
import os, sys
sys.path[:0] = ['/work/vincentfix', '/work/iostore', '/work/cs', '/work/charaspecmod',
                '/work/swap1012/tools', '/work/sephforms/tools', '/work/shooter1016/tools']
import charaspec_patch as cp
import build_dirge_paks as P

NAME = 'FullyPlayableVincentAssets_P'
TABLE = 'DataObject/Resident/CharaSpec.uasset'
VINCENT = 'PC0011_00_Vincent_Standard'
ROWS = ['PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']


def text(v):
    if isinstance(v, list): return '[' + ', '.join(text(x) for x in v) + ']'
    if isinstance(v, (bytes, bytearray)): return v[:-2].decode('utf-16-le', 'replace')
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str): return v[0]
    return repr(v)


def main(src, out):
    chunks, store = P.read(os.path.join(src, NAME + '.utoc'))
    k = [i for i, c in enumerate(chunks) if c['path'] == TABLE]
    assert len(k) == 1
    c = chunks[k[0]]
    z, e, m, d = cp.decode(c['data'])
    fi = cp.field_index(d)
    names = [key[0][0] for key in d.keys]
    model = d.rows[names.index('PC0000_00_Cloud_Standard')][fi['ContentsModel']]
    assert text(model) == VINCENT, text(model)
    report = []
    before = [list(r) for r in d.rows]
    for row in ROWS:
        r = d.rows[names.index(row)]
        was = (text(r[fi['ContentsModel']]), text(r[fi['NoBattleCharaSpec']]), text(r[fi['ReserveCharaSpec']]))
        r[fi['ContentsModel']] = model
        self_name = (row, 0)
        if text(r[fi['NoBattleCharaSpec']]) not in ('None', ''):
            r[fi['NoBattleCharaSpec']] = self_name
        if text(r[fi['ReserveCharaSpec']]) not in ('None', ''):
            r[fi['ReserveCharaSpec']] = self_name
        report.append('%s: model %s -> %s, field %s -> %s, reserve %s -> %s' % (
            row, was[0], text(r[fi['ContentsModel']]), was[1], text(r[fi['NoBattleCharaSpec']]), was[2], text(r[fi['ReserveCharaSpec']])))
    new = cp.encode(c["data"], z, e, m, [key[0] for key in d.keys], d.fields, d.rows)
    # read back: only those rows and fields changed
    z2, e2, m2, d2 = cp.decode(new)
    for i, (a, b) in enumerate(zip(before, d2.rows)):
        n = names[i]
        diff = [f for f in fi if text(a[fi[f]]) != text(b[fi[f]])]
        if n in ROWS:
            assert set(diff) <= {'ContentsModel', 'NoBattleCharaSpec', 'ReserveCharaSpec'} and 'ContentsModel' in diff, (n, diff)
        else:
            assert not diff, (n, diff)
    c['data'] = new
    entries = [P.entry(x, store[x['id64']]) for x in chunks if x['type'] == 2]
    for en in entries:
        if en['id'] == c['id64']:
            assert en['size'] >> 60 == 0
            en['size'] = len(new)
    os.makedirs(out, exist_ok=True)
    cid, files = P.write(out, NAME, chunks, entries, os.path.join(src, NAME + '.pak'))
    report.append('container %s: %s' % (NAME, files))
    print('\n'.join(report))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
