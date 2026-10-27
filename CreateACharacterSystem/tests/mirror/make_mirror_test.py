"""Builds mirror_test.cpp: the game mod's own TableCopies code (and the frozen-table helpers it uses), cut out of
RebirthSkelCompat.cpp by markers, with stand-ins for the Windows and engine calls, and a test of it on a synthetic
frozen table (3.16.2's in-place mirror and its restore, byte for byte).
    make_mirror_test.py <RebirthSkelCompat.cpp> <out .cpp>"""
import sys

src = open(sys.argv[1], encoding='utf-8').read().split('\n')


def block(start, end, include_end=True):
    """Lines from the first starting with `start` to the first after it starting with `end`."""
    a = next(i for i, l in enumerate(src) if l.startswith(start))
    b = next(i for i in range(a + 1, len(src)) if src[i].startswith(end))
    return '\n'.join(src[a:b + 1 if include_end else b])


frozen = block('struct FrozenTable', 'bool ReadFrozenArray', include_end=False) + '\n' + block('bool ReadFrozenArray', '}')
opentable = block('// (3.16.0) The table whose frozen root is at', 'RawName ExistingName', include_end=False)
writearray = block('// Why the last WriteTableArray failed', '// ------', include_end=False)
spans = block('// (3.16.2) The rows of the mod\'s copies of the table', 'uint64_t* Answer(int slot', include_end=False)
copies = block('namespace TableCopies', '} // namespace TableCopies')

head = open(sys.argv[0].replace('make_mirror_test.py', 'mirror_head.inc'), encoding='utf-8').read()
tail = open(sys.argv[0].replace('make_mirror_test.py', 'mirror_tail.inc'), encoding='utf-8').read()
out = '\n'.join([head, frozen, opentable, writearray,
                 'namespace ListGetters\n{\n' + spans + '\n} // namespace ListGetters', copies, tail])
open(sys.argv[2], 'w', encoding='utf-8').write(out)
print('wrote %s (%d lines)' % (sys.argv[2], out.count('\n') + 1))
