"""Facts about a game shader blob: signatures, resource table, reflection names (via dxc -dumpbin)."""
import struct, subprocess, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxbc import container, signature, psv0_resources
DXC = '/home/user/microsoft/dxc-build/bin/dxc'
ENV = dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib')


def resource_table(blob):
    at = blob.find(b'DXBC')
    h = blob[:at]
    p = 0
    bits = struct.unpack_from('<I', h, p)[0]; p += 4
    maps = {}
    for name in ('SRVMap', 'SamplerMap', 'UAVMap', 'LayoutHashes', 'TextureMap'):
        n = struct.unpack_from('<i', h, p)[0]; p += 4
        maps[name] = list(struct.unpack_from('<%dI' % n, h, p)); p += 4 * n
    return bits, maps, p == len(h)


def entries(m, nub):
    """[(ub, resource index, bind)] of a packed resource map (8:16:8)."""
    out = []
    for v in m[nub:]:
        if v == 0xFFFFFFFF:
            break
        out.append((v >> 24, (v >> 8) & 0xFFFF, v & 0xFF))
    return out


def data_entries(blob):
    at = blob.find(b'DXBC')
    c = container(blob, at)
    tail = blob[at + c['total']:]
    out = []
    q = 0
    while q + 5 <= len(tail) - 4:
        key = tail[q]; size = struct.unpack_from('<I', tail, q + 1)[0]
        out.append((chr(key), tail[q + 5:q + 5 + size]))
        q += 5 + size
    return out, tail[q:]


def dump(dxbc_bytes):
    with tempfile.NamedTemporaryFile(suffix='.dxbc', delete=False) as f:
        f.write(dxbc_bytes)
        path = f.name
    try:
        r = subprocess.run([DXC, '-dumpbin', path], capture_output=True, text=True, env=ENV)
        return r.stdout + r.stderr
    finally:
        os.unlink(path)


def bindings(text):
    """[(name, type, dim, hlsl bind)] from the dumpbin's Resource Bindings table."""
    out = []
    sec = text.split('; Resource Bindings:', 1)
    if len(sec) < 2:
        return out
    for line in sec[1].splitlines()[3:]:
        if not line.startswith('; ') or line.strip() == ';':
            break
        parts = line[2:].split()
        if len(parts) >= 7:
            out.append((parts[0], parts[1], parts[3], parts[-2]))
    return out


def cbuffer_members(text, cb):
    """{member: offset} of cbuffer `cb` from the dumpbin's buffer definitions."""
    out = {}
    m = re.search(r'; cbuffer %s\n; \{\n(.*?)\n; \}' % cb, text, re.S)
    if not m:
        return out
    for line in m.group(1).splitlines():
        mm = re.match(r';\s+(?:row_major )?(\S+) (\w+)(\[\d+\])?;\s*; Offset:\s+(\d+)', line)
        if mm:
            out[mm.group(2)] = (int(mm.group(4)), mm.group(1), mm.group(3))
    return out


def info(blob):
    at = blob.find(b'DXBC')
    c = container(blob, at)
    d = dict(isg=[], osg=[])
    for fourcc, o, size in c['parts']:
        if fourcc == 'ISG1':
            d['isg'] = signature(blob, o)
        if fourcc == 'OSG1':
            d['osg'] = signature(blob, o)
    d['psv0'] = psv0_resources(blob, c)
    bits, maps, exact = resource_table(blob)
    nub = len(maps['LayoutHashes'])
    d['ub_bits'], d['layout_hashes'] = bits, maps['LayoutHashes']
    d['tex'] = entries(maps['TextureMap'], nub)
    d['samp'] = entries(maps['SamplerMap'], nub)
    d['srv'] = entries(maps['SRVMap'], nub)
    d['uav'] = entries(maps['UAVMap'], nub)
    d['data'], d['data_tail'] = data_entries(blob)
    text = dump(blob[at:at + c['total']])
    d['text'] = text
    d['bindings'] = bindings(text)
    d['discard'] = 'dx.op.discard' in text
    return d
