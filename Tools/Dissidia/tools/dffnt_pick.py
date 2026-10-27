"""Picks the Dissidia NT entries for the Sephiroth (p_sev200) work from dffnt_entries.csv and copies their files (and the
package table) into a small game folder for Cethleann's DataExporter.
    dffnt_pick.py <entries csv> <game dir> <out game dir> <list out>"""
import csv, os, shutil, sys

KEEP_PREFIX = ('character/p_sev200', 'item/w_sev200', 'effect/e_sev200', 'player/obj/p_sev200', 'shader/', 'commontexture/',
               'posteffect/', 'cloth/')
KEEP_SUB = ('p_sev200',)
KEEP_TOP = ('rtm', 'ecb', 'scene')
TABLE = 'COMMON/dafb4dd62a79856ae4a02584d9f642a10208bcc3d3de61210a73a75bfb218bc0'


def keep(o):
    if o.startswith(KEEP_PREFIX):
        return True
    top = o.split('/')[0]
    return top in KEEP_TOP and any(s in o for s in KEEP_SUB)


def main(entries, game, out, listing):
    rows = [r for r in csv.DictReader(open(entries)) if keep(r['original'].replace('\\', '/'))]
    os.makedirs(os.path.join(out, 'COMMON'), exist_ok=True)
    shutil.copyfile(os.path.join(game, TABLE), os.path.join(out, TABLE))
    total = 0
    with open(listing, 'w') as f:
        for r in rows:
            src = os.path.join(game, r['path'])
            dst = os.path.join(out, r['path'])
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copyfile(src, dst)
            total += int(r['dsize'])
            f.write('%s\t%s\t%s\n' % (r['original'], r['path'], r['dsize']))
    print('%d entries copied, %.1f MB packed, %.1f MB unpacked' % (len(rows), sum(int(r['csize']) for r in rows) / 1e6, total / 1e6))


if __name__ == '__main__':
    main(*sys.argv[1:5])
