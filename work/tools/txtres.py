"""FF7 Rebirth text resource packages (/Game/Text/<LANG>/*_TxtRes, class EndTextResource).
Export data: unversioned header (one fragment: Language), FString Language, uint32 0 (no guid), int32 count, then per
entry: FString key ("$..."), FString text, int32 n, n x {FName attribute (ARTICLE, PLURAL, ...), FString value}.
    entries, lang = parse(data)          (data: the package)
    add(data, [(key, text), ...])        -> new package bytes (keys already present get the new text)"""
import struct, sys
sys.path[:0] = ['/work/cs', '/work/charaspecmod', '/work/seph1013']
from zen import Zen
from tagged import export_layout


def _fstr(b, o):
    n = struct.unpack_from('<i', b, o)[0]
    o += 4
    if n == 0:
        return '', o, False
    if n > 0:
        return b[o:o + n - 1].decode('latin-1'), o + n, False
    n = -n
    return b[o:o + 2 * n - 2].decode('utf-16-le'), o + 2 * n, True


def _wstr(s):
    if s == '':
        return struct.pack('<i', 0)
    try:
        raw = s.encode('ascii')
        return struct.pack('<i', len(raw) + 1) + raw + b'\0'
    except UnicodeEncodeError:
        raw = s.encode('utf-16-le')
        return struct.pack('<i', -(len(raw) // 2 + 1)) + raw + b'\0\0'


def _body(data):
    z = Zen(data)
    assert len(z.exports) == 1, 'one export expected'
    L = export_layout(z)
    return z, L[0], data[L[0]:L[0] + z.exports[0]['serial_size']]


def parse_body(x):
    o = 2
    lang, o, _ = _fstr(x, o)
    guid = struct.unpack_from('<I', x, o)[0]
    o += 4
    count = struct.unpack_from('<i', x, o)[0]
    o += 4
    entries = []
    for _ in range(count):
        s = o
        key, o, _ = _fstr(x, o)
        text, o, _ = _fstr(x, o)
        n = struct.unpack_from('<i', x, o)[0]
        o += 4
        for _ in range(n):
            o += 8
            _, o, _ = _fstr(x, o)
        entries.append((key, text, x[s:o]))
    return dict(header=x[:2], lang=lang, guid=guid, entries=entries, tail=x[o:])


def parse(data):
    z, at, x = _body(data)
    p = parse_body(x)
    return p['entries'], p['lang']


def build_body(p, add):
    """p from parse_body; add: [(key, text)]: replaces the text of existing keys (their attributes dropped), appends the rest."""
    want = {k: t for k, t in add}
    out = bytearray(p['header']) + _wstr(p['lang']) + struct.pack('<I', p['guid'])
    rows = []
    seen = set()
    for key, text, raw in p['entries']:
        if key in want:
            rows.append(_wstr(key) + _wstr(want[key]) + struct.pack('<i', 0))
            seen.add(key)
        else:
            rows.append(raw)
    for key, text in add:
        if key not in seen:
            rows.append(_wstr(key) + _wstr(text) + struct.pack('<i', 0))
            seen.add(key)
    out += struct.pack('<i', len(rows))
    for r in rows:
        out += r
    out += p['tail']
    return bytes(out)


def add(data, pairs):
    """New package bytes with `pairs` added (the export grows; the package header is rewritten by build_package)."""
    from build_charaspec import build_package
    z, at, x = _body(data)
    p = parse_body(x)
    assert build_body(p, []) == x, 'text resource does not round-trip'
    return build_package(data, z, build_body(p, pairs))


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    entries, lang = parse(d)
    print(lang, len(entries))
    for k, t, _ in entries[:5]:
        print(' ', k, '=>', t[:60])
