"""A game shader blob for a compiled pixel shader: resource table + DXBC + optional data, as the game's D3D12 RHI reads it.

  resource table  u32 ResourceTableBits; then SRVMap, SamplerMap, UAVMap, LayoutHashes, TextureMap, each an i32 count and
                  that many u32. A map starts with one offset per uniform buffer slot (0 = none), then each buffer's
                  entries (buffer << 24 | resource index << 8 | register), in buffer order, ended by 0xFFFFFFFF.
  optional data   key byte, u32 size, data ... then a u32 with the size of all of it (+4). 'p' holds the resource counts
                  (samplers [1], SRVs [2], constant buffers [3], UAVs [4]); 'u' the uniform buffer names by slot.

The new shader binds its resources wherever the compiler put them; the table says which uniform buffer member goes to
which register, so any member of the game's View buffer and any texture of the carrier's Material buffer can be used
(and, given a catalog, a resource of another of the carrier's buffers where the carrier's own shader binds it: the
translucent pass's TranslucentBasePass, gamemat/translucent.py).
"""
import re
import struct

from . import ub

MAPS = ('SRVMap', 'SamplerMap', 'UAVMap', 'LayoutHashes', 'TextureMap')


def parse(blob):
    """(resource table dict, dxbc offset, dxbc size, optional data [(key, bytes)]) of a game shader blob."""
    at = blob.find(b'DXBC')
    p = 0
    bits = struct.unpack_from('<I', blob, p)[0]
    p += 4
    maps = {}
    for name in MAPS:
        n = struct.unpack_from('<i', blob, p)[0]
        p += 4
        maps[name] = list(struct.unpack_from('<%dI' % n, blob, p))
        p += 4 * n
    if p != at:
        raise ValueError('the resource table does not end at the DXBC container (%d vs %d)' % (p, at))
    total = struct.unpack_from('<I', blob, at + 24)[0]
    tail = blob[at + total:]
    data = []
    q = 0
    while q + 5 <= len(tail) - 4:
        key = tail[q:q + 1].decode('latin1')
        size = struct.unpack_from('<I', tail, q + 1)[0]
        data.append((key, tail[q + 5:q + 5 + size]))
        q += 5 + size
    if struct.unpack_from('<I', tail, q)[0] != q + 4 or q + 4 != len(tail):
        raise ValueError('the optional data does not end with its size')
    return dict(bits=bits, maps=maps), at, total, data


def encode_map(entries, slots):
    """entries [(buffer slot, resource index, register)] -> the u32 list of one map."""
    entries = sorted(entries)
    out = [0] * slots
    for slot in range(slots):
        mine = [e for e in entries if e[0] == slot]
        if mine:
            out[slot] = len(out)
            for b, r, reg in mine:
                if not (0 <= r < 0x10000 and 0 <= reg < 0x100):
                    raise ValueError('resource %d / register %d out of range' % (r, reg))
                out.append((b << 24) | (r << 8) | reg)
    out.append(0xFFFFFFFF)
    return out


def build(carrier_blob, dxbc, bindings, material_resource, name, catalog=None):
    """The new blob.
    carrier_blob       the carrier's original shader (its uniform buffer slots, layout hashes and optional data)
    dxbc               the compiled container
    bindings           [(name, type, dim, 'tN'/'sN'/'cbN')] from its reflection
    material_resource  callable: 'Material_Texture2D_3' / 'Material_Texture2D_3Sampler' / 'GameCoverageTexture' ...
                       -> resource index in the carrier's Material buffer (raises KeyError when it has none)
    catalog            optional {binding name: (uniform buffer name, 'tex' / 'srv' / 'samp' / 'uav', resource index)}
                       for the other resources (those the carrier's own shader binds); None: View and Material only
    """
    table, at, total, data = parse(carrier_blob)
    hashes = table['maps']['LayoutHashes']
    slots = len(hashes)
    names = _ub_names(data)
    view_slot = names.index('View') if 'View' in names else None
    material_slot = names.index('Material') if 'Material' in names else None
    tex, samp, srv, uav = [], [], [], []
    counts = dict(s=0, t=0, cb=0, u=0)
    problems = []
    for bname, typ, dim, bind in bindings:
        m = re.match(r'^(cb|t|s|u)(\d+)$', bind)
        if not m:
            problems.append('binding %s at %s' % (bname, bind))
            continue
        kind, reg = m.group(1), int(m.group(2))
        counts[kind] = max(counts[kind], reg + 1)
        if kind == 'cb':
            if bname not in names or names.index(bname) != reg:
                problems.append('constant buffer %s is at b%d; the carrier has %s there' % (bname, reg, names[reg] if reg < len(names) else 'nothing'))
            continue
        target = tex if kind == 't' and typ == 'texture' else samp if kind == 's' else srv if kind == 't' else uav
        if bname.startswith('View_'):
            if view_slot is None:
                problems.append('%s: the carrier has no View buffer' % bname)
                continue
            try:
                target.append((view_slot, ub.resource_index('View', bname[5:]), reg))
            except KeyError:
                problems.append('%s is not in the game\'s View buffer' % bname)
            continue
        if bname.startswith('Material_') or bname.startswith('Game'):
            if material_slot is None:
                problems.append('%s: the carrier has no Material buffer' % bname)
                continue
            try:
                target.append((material_slot, material_resource(bname), reg))
            except KeyError as error:
                problems.append(str(error).strip('"\''))
            continue
        if catalog and bname in catalog:
            ub_name, map_kind, index = catalog[bname]
            if ub_name not in names:
                problems.append('%s: the carrier has no %s buffer' % (bname, ub_name))
                continue
            dict(tex=tex, samp=samp, srv=srv, uav=uav)[map_kind].append((names.index(ub_name), index, reg))
            continue
        problems.append('%s (%s) is not something the game\'s base pass gives a shader' % (bname, typ))
    if problems:
        return None, problems
    maps = dict(SRVMap=encode_map(srv, slots), SamplerMap=encode_map(samp, slots), UAVMap=encode_map(uav, slots),
                LayoutHashes=list(hashes), TextureMap=encode_map(tex, slots))
    bits = 0
    for b, r, reg in tex + samp + srv + uav:
        bits |= 1 << b
    head = struct.pack('<I', bits)
    for mname in MAPS:
        head += struct.pack('<i', len(maps[mname])) + struct.pack('<%dI' % len(maps[mname]), *maps[mname])
    out_data = []
    for key, value in data:
        if key == 'p':
            value = bytearray(value)
            value[1], value[2], value[3] = counts['s'], counts['t'], counts['cb']
            if len(value) > 4:
                value[4] = counts['u']
            value = bytes(value)
        elif key == 'n' and name is not None:
            value = name.encode('latin1') + b'\0'
        out_data.append((key, value))
    tail = b''.join(k.encode('latin1') + struct.pack('<I', len(v)) + v for k, v in out_data)
    tail += struct.pack('<I', len(tail) + 4)
    return head + dxbc + tail, []


def _ub_names(data):
    for key, value in data:
        if key == 'u':
            n = struct.unpack_from('<I', value, 0)[0]
            p = 4
            names = []
            for _ in range(n):
                ln = struct.unpack_from('<i', value, p)[0]
                p += 4
                names.append(value[p:p + ln - 1].decode('latin1') if ln > 0 else '')
                p += max(ln, 0)
            return names
    return []
