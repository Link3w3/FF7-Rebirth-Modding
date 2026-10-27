"""The game's global shader map: sections (one per .usf), their shader types, permutations and library entries."""
import json, struct, sys
sys.path.insert(0, '/work/custmat')
from shlib import Library
import frozen
SECS = json.load(open('/work/custmat/anime/global_sections.json'))
BIN = open('/work/custmat/anime/GlobalShaderCache-PCD3D_SM6.bin', 'rb').read()
LIB = Library('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/Global_header.bin', 'Global')
NAMES = json.load(open('/work/custmat/exe_hashed_names.json'))

def name_of(h):
    return NAMES.get('%016x' % h, '%016x' % h)

def section(k):
    s = SECS[k]
    fz = BIN[s['frozen_at']:s['frozen_at'] + s['F']]
    types, perms, shaders, nl, plat = frozen.content(fz, 0)
    tnames = [name_of(struct.unpack_from('<Q', BIN, s['types_at'] + 8 * k)[0]) for k in range(s['nt'])]
    rows = []
    for perm, at in zip(perms, shaders):
        t, vf = struct.unpack_from('<QQ', fz, at + frozen.TYPE_FIELD)
        target, res = struct.unpack_from('<Ii', fz, at + frozen.TARGET_FIELD)
        rows.append((tnames[t >> 1] if t & 1 and (t >> 1) < len(tnames) else '%x' % t, perm, target & 0xff, res))
    mh = BIN[s['end'] - 20:s['end']]
    lib = LIB.shaders_of(mh) if mh in LIB.map_index else None
    return rows, lib

if __name__ == '__main__':
    for k in range(len(SECS)):
        try:
            rows, lib = section(k)
        except Exception as e:
            print(k, 'ERR', e); continue
        tn = sorted(set(r[0] for r in rows))
        print(k, len(rows), 'lib', len(lib) if lib else None, ' '.join(tn)[:200])
