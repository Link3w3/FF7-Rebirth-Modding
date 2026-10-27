"""The zen packages of an IoStore container (.utoc/.ucas), written out as files (their export bundle chunks).
    container_pkg.py <container .utoc> <out folder> [name part]
Prints each package's path; with a name part, only those whose path has it."""
import os, sys
sys.path[:0] = ['/work/iostore']
from iostore import Toc

EXPORT_BUNDLE_DATA = 2   # (UE 4.26 EIoChunkType::ExportBundleData)


def main():
    utoc, out = sys.argv[1], sys.argv[2]
    part = sys.argv[3] if len(sys.argv) > 3 else ''
    t = Toc(utoc)
    os.makedirs(out, exist_ok=True)
    n = 0
    for i in range(t.entries):
        path = t.files.get(i, '')
        if t.chunk_type(i) != EXPORT_BUNDLE_DATA or (part and part not in path):
            continue
        data = t.read(i)
        name = os.path.basename(path) or ('chunk%d.uasset' % i)
        dst = os.path.join(out, name)
        open(dst, 'wb').write(data)
        print('%s -> %s (%d bytes)' % (path, dst, len(data)))
        n += 1
    print('%d package(s)' % n)


if __name__ == '__main__':
    main()
