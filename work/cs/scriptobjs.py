"""The game's script objects (global.utoc, UE 4.26 IoStore): FPackageObjectIndex -> '/Script/Module.Object' path.
    scriptobjs.py [<global.utoc>]  (prints a few)"""
import os, struct, sys
sys.path[:0] = ['/work/iostore']
from iostore import Toc

GLOBAL = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Content/Paks/global.utoc'
_cache = {}


def names_from_batch(names_blob, hashes_blob):
    count = (len(hashes_blob) - 8) // 8
    out, p = [], 0
    for _ in range(count):
        h0, h1 = names_blob[p], names_blob[p + 1]
        p += 2
        wide = h0 & 0x80
        ln = ((h0 & 0x7f) << 8) | h1
        if wide:
            s = names_blob[p:p + ln * 2].decode('utf-16-le')
            p += ln * 2
        else:
            s = names_blob[p:p + ln].decode('latin-1')
            p += ln
        out.append(s)
    return out


def load(utoc=GLOBAL):
    """{index value (u64): path} for every script object, and the reverse."""
    if utoc in _cache:
        return _cache[utoc]
    t = Toc(utoc)
    by_type = {t.chunk_type(i): i for i in range(t.entries)}
    meta = t.read(by_type[7])
    names = names_from_batch(t.read(by_type[8]), t.read(by_type[9]))
    n = struct.unpack_from('<i', meta, 0)[0]
    entries = []
    for k in range(n):
        name_idx, name_num, glob, outer, cdo = struct.unpack_from('<IIQQQ', meta, 4 + 32 * k)
        idx = name_idx & 0x3fffffff
        nm = names[idx] if idx < len(names) else '?%d' % idx
        if name_num:
            nm = '%s_%d' % (nm, name_num - 1)
        entries.append((glob, outer, cdo, nm))
    by = {e[0]: e for e in entries}
    paths = {}

    def path(g, depth=0):
        if g in paths:
            return paths[g]
        e = by.get(g)
        if e is None or depth > 16:
            return None
        glob, outer, cdo, nm = e
        if outer == 0xFFFFFFFFFFFFFFFF or outer not in by:
            p = nm
        else:
            parent = path(outer, depth + 1)
            sep = '.' if parent.count('.') == 0 else ':'
            p = parent + sep + nm
        paths[g] = p
        return p

    for e in entries:
        path(e[0])
    rev = {v: k for k, v in paths.items()}
    _cache[utoc] = (paths, rev)
    return paths, rev


def name_of(value, utoc=GLOBAL):
    paths, _ = load(utoc)
    if value == 0xFFFFFFFFFFFFFFFF:
        return None
    kind = value >> 62
    if kind == 1:   # ScriptImport
        return paths.get(value, '<script %016x>' % value)
    if kind == 0:   # Export of this package
        return '<export %d>' % value
    if kind == 2:   # PackageImport
        return '<pkgimport %016x>' % value
    return '<null>'


if __name__ == '__main__':
    paths, rev = load(sys.argv[1] if len(sys.argv) > 1 else GLOBAL)
    print(len(paths), 'script objects')
    for k in ['/Script/LevelSequence.LevelSequence', '/Script/MovieScene.MovieScene', '/Script/CinematicCamera.CineCameraActor']:
        print(k, '%016x' % rev[k] if k in rev else None)


def import_hash(object_path):
    """FPackageObjectIndex of an import of another package's object ('/Game/A/B.B' or '/Game/A/B.B:Sub')."""
    from cityhash import CityHash64
    s = ''.join('/' if ch in '.:' else ch.lower() for ch in object_path)
    return (2 << 62) | (CityHash64(s.encode('utf-16-le')) & ~(3 << 62))
