"""Koei Tecmo G1M models (Dissidia Final Fantasy NT, G1M 0037 / G1MS 0032 / G1MG 0044), read with numpy.

Written for the Dissidia NT Sephiroth pipeline from the layouts in Project G1M (github.com/Joschuka/Project-G1M) and
eArmada8's gust_stuff (g1m_export_meshes.py), checked against the game's files.

    g1m.py info <file.g1m> [base.g1m]        chunks, skeleton, materials, shader parameters, submeshes, LODs
    g1m.py skel <base.g1m> [model.g1m]       the (combined) skeleton: index, parent, local and world transforms

Skeletons: a character's base g1m (<outfit>.g1m) holds the main skeleton (its G1MS joints are in local index order;
the index list maps global ids to them). A model g1m (<outfit>_default.g1m, parts) has its own G1MS: when its first
joint's parent field is 0x80000000 it is an "external" layer whose joints hang under the base skeleton (a parent
with the 0x80000000 bit is a base skeleton joint by local id... see combine()). Joint palettes name a joint by its
local id in the model's G1MS, with 0x80000000 set when the joint is the base skeleton's.
"""
import json
import struct
import sys

import numpy as np

SEMANTICS = ['POSITION', 'BLENDWEIGHT', 'BLENDINDICES', 'NORMAL', 'PSIZE', 'TEXCOORD', 'TANGENT', 'BINORMAL',
             'TESSFACTOR', 'POSITIONT', 'COLOR', 'FOG', 'DEPTH', 'SAMPLE']
# data type -> (numpy dtype, count)
DTYPES = {0x00: ('<f4', 1), 0x01: ('<f4', 2), 0x02: ('<f4', 3), 0x03: ('<f4', 4), 0x05: ('u1', 4), 0x07: ('<u2', 4),
          0x09: ('<u4', 4), 0x0A: ('<f2', 2), 0x0B: ('<f2', 4), 0x0D: ('u1n', 4)}


def chunks(b):
    assert b[:4] == b'_M1G', b[:4]
    first, _, count = struct.unpack_from('<III', b, 12)
    out = []
    o = first
    for _ in range(count):
        magic, ver, size = struct.unpack_from('<4s4sI', b, o)
        out.append((magic[::-1].decode('ascii', 'replace'), ver[::-1].decode('ascii', 'replace'), o, size))
        o += size
    return out


def chunk(b, name):
    for m, v, o, s in chunks(b):
        if m == name:
            return b[o:o + s], v
    return None, None


class Skeleton:
    """One G1MS: joints in local order, local<->global id maps, local transforms (scale, quaternion xyzw, position)."""

    def __init__(self, data):
        ver = struct.unpack_from('<I', data, 4)[0]
        off, _, n, nidx, layer, _ = struct.unpack_from('<IIHHHH', data, 12)
        self.layer = layer
        self.count = n
        self.global_of_local = {}
        self.local_of_global = {}
        for i in range(nidx):
            lid = struct.unpack_from('<H', data, 28 + 2 * i)[0]
            if lid != 0xFFFF:
                self.global_of_local[lid] = i
                self.local_of_global[i] = lid
        self.parent_raw = []
        self.scale = np.zeros((n, 3))
        self.quat = np.zeros((n, 4))       # x y z w
        self.pos = np.zeros((n, 3))
        for i in range(n):
            o = off + 48 * i
            sx, sy, sz, parent, qx, qy, qz, qw, px, py, pz, pw = struct.unpack_from('<3fI4f4f', data, o)
            self.scale[i] = (sx, sy, sz)
            self.parent_raw.append(parent)
            self.quat[i] = (qx, qy, qz, qw)
            self.pos[i] = (px, py, pz)
        self.external = bool(n) and self.parent_raw[0] == 0x80000000


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def quat_rot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, float)
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def quat_matrix(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


class Rig:
    """The combined skeleton: base joints first (local order), then the model's external layer joints.
    names: 'b<global id>' for base joints, 'x<model>_<local>' for layer joints."""

    def __init__(self, base, layers=()):
        self.names, self.parents, self.lquat, self.lpos, self.lscale = [], [], [], [], []
        self.base_count = base.count
        for i in range(base.count):
            self.names.append('b%d' % base.global_of_local.get(i, 1000 + i))
            p = base.parent_raw[i]
            self.parents.append(-1 if p == 0xFFFFFFFF else int(p))
            self.lquat.append(base.quat[i]); self.lpos.append(base.pos[i]); self.lscale.append(base.scale[i])
        self.layer_start = {}
        for tag, sk in layers:
            start = len(self.names)
            self.layer_start[tag] = start
            for i in range(sk.count):
                p = sk.parent_raw[i]
                if p & 0x80000000:
                    # a joint under the base skeleton: the low bits are... the base joint's local id
                    pp = p & 0xFFFF
                    parent = pp if pp != 0xFFFF and pp < base.count else -1
                else:
                    parent = start + p
                self.names.append('%s_%d' % (tag, i))
                self.parents.append(parent)
                self.lquat.append(sk.quat[i]); self.lpos.append(sk.pos[i]); self.lscale.append(sk.scale[i])
        n = len(self.names)
        self.wquat = [None] * n
        self.wpos = [None] * n
        for i in range(n):
            self._world(i)
        self.wquat = np.array(self.wquat)
        self.wpos = np.array(self.wpos)

    def _world(self, i):
        if self.wquat[i] is not None:
            return
        p = self.parents[i]
        if p < 0:
            self.wquat[i] = np.array(self.lquat[i]); self.wpos[i] = np.array(self.lpos[i])
            return
        self._world(p)
        self.wquat[i] = quat_mul(self.wquat[p], self.lquat[i])
        self.wpos[i] = quat_rot(self.wquat[p], self.lpos[i]) + self.wpos[p]


def read_attr(data, buf_off, stride, count, attr_off, dtype):
    dt, n = DTYPES[dtype]
    raw = np.frombuffer(data, dtype=np.uint8, count=stride * count, offset=buf_off).reshape(count, stride)
    if dt == 'u1n':
        return raw[:, attr_off:attr_off + 4].astype(np.float32) / 255.0
    size = np.dtype(dt).itemsize * n
    cols = raw[:, attr_off:attr_off + size].copy()
    return cols.view(dt).reshape(count, n).astype(np.float64 if dt in ('<f4', '<f2') else np.int64)


class Geometry:
    def __init__(self, data):
        self.data = data
        self.version = struct.unpack_from('<I', data, 4)[0]
        self.platform = data[12:16]
        self.bbox = struct.unpack_from('<6f', data, 20)
        nsec = struct.unpack_from('<I', data, 44)[0]
        o = 48
        self.sockets, self.materials, self.shaders, self.vbufs, self.attrs = [], [], [], [], []
        self.palettes, self.ibufs, self.submeshes, self.lods = [], [], [], []
        new = self.version > 0x30303430
        for _ in range(nsec):
            magic, size, count = struct.unpack_from('<3I', data, o)
            p = o + 12
            if magic == 0x10001:
                for j in range(count):
                    s = struct.unpack_from('<2hf3f3f2hf3f3f', data, p)
                    self.sockets.append(s); p += 64
            elif magic == 0x10002:
                for j in range(count):
                    u1, tcount, u2, u3 = struct.unpack_from('<4I', data, p); p += 16
                    texs = []
                    for k in range(tcount):
                        tid, layer, ttype, sub, tx, ty = struct.unpack_from('<6H', data, p); p += 12
                        texs.append(dict(index=tid, layer=layer, type=ttype, subtype=sub, tile=(tx, ty)))
                    self.materials.append(dict(unk=(u1, u2, u3), textures=texs))
            elif magic == 0x10003:
                for j in range(count):
                    sc = struct.unpack_from('<I', data, p)[0]; p += 4
                    params = []
                    for k in range(sc):
                        psize, nsize, unk1, btype, bcount = struct.unpack_from('<3I2H', data, p)
                        name = data[p + 16:p + 16 + nsize].split(b'\0')[0].decode('ascii', 'replace')
                        q = p + 16 + nsize
                        fmt = {1: 'f', 2: '2f', 3: '3f', 4: '4f', 5: 'i'}.get(btype)
                        vals = []
                        if fmt:
                            w = struct.calcsize('<' + fmt)
                            for l in range(bcount):
                                v = struct.unpack_from('<' + fmt, data, q + w * l)
                                vals.append(v[0] if len(v) == 1 else list(v))
                        params.append(dict(name=name, type=btype, values=vals, unk=unk1))
                        p += psize
                    self.shaders.append(params)
            elif magic == 0x10004:
                j = 0
                repo = None
                while j < count:
                    unk, stride, n = struct.unpack_from('<3I', data, p); p += 12
                    if new:
                        p += 4
                    self.vbufs.append(dict(stride=stride, count=n, offset=p, unk=unk))
                    if stride == 1:
                        repo = p
                    p += stride * n
                    j += 1
                    acc = repo
                    while j < count and struct.unpack_from('<I', data, p)[0] == 0x80000000:
                        unk, stride, n = struct.unpack_from('<3I', data, p); p += 12
                        if new:
                            p += 4
                        self.vbufs.append(dict(stride=stride, count=n, offset=acc, unk=unk))
                        acc += stride * n
                        j += 1
            elif magic == 0x10005:
                for j in range(count):
                    lc = struct.unpack_from('<I', data, p)[0]; p += 4
                    blist = struct.unpack_from('<%dI' % lc, data, p); p += 4 * lc
                    ac = struct.unpack_from('<I', data, p)[0]; p += 4
                    attrs = []
                    for k in range(ac):
                        bid, aoff, dtype, dummy, sem, layer = struct.unpack_from('<2H4B', data, p); p += 8
                        attrs.append(dict(buffer=blist[bid], offset=aoff, dtype=dtype, semantic=SEMANTICS[sem], layer=layer))
                    self.attrs.append(attrs)
            elif magic == 0x10006:
                for j in range(count):
                    jc = struct.unpack_from('<I', data, p)[0]; p += 4
                    ents = []
                    for k in range(jc):
                        g1mm, phys, joint = struct.unpack_from('<3I', data, p); p += 12
                        ents.append(dict(g1mm=g1mm, physics=phys, joint=joint))
                    self.palettes.append(ents)
            elif magic == 0x10007:
                for j in range(count):
                    n, dt = struct.unpack_from('<II', data, p); p += 8
                    if new:
                        p += 4
                    w = dt // 8
                    self.ibufs.append(dict(count=n, width=w, offset=p))
                    p += n * w
                    p = (p + 3) & ~3
            elif magic == 0x10008:
                for j in range(count):
                    v = struct.unpack_from('<14I', data, p); p += 56
                    keys = ['flags', 'vbuf', 'palette', 'bone', 'unk', 'shader', 'material', 'ibuf', 'unk2', 'prim',
                            'vstart', 'vcount', 'istart', 'icount']
                    self.submeshes.append(dict(zip(keys, v)))
            elif magic == 0x10009:
                for j in range(count):
                    lod, group, gidx, c1, c2 = struct.unpack_from('<5I', data, p); p += 20
                    rng = None
                    if self.version > 0x30303340:
                        rng = struct.unpack_from('<4I', data, p); p += 16
                    meshes = []
                    for k in range(c1 + c2):
                        name = data[p:p + 16].split(b'\0')[0].decode('ascii', 'replace'); p += 16
                        cloth, unk, nunid, ic = struct.unpack_from('<2H2I', data, p); p += 12
                        idx = list(struct.unpack_from('<%dI' % ic, data, p)) if ic else []
                        p += 4 * ic if ic else 4
                        meshes.append(dict(name=name, cloth=cloth, unk=unk, nunid=nunid, submeshes=idx))
                    self.lods.append(dict(lod=lod, group=group, group_index=gidx, counts=(c1, c2), range=rng,
                                          meshes=meshes))
            o += size

    def submesh_arrays(self, si):
        """The submesh's vertex attributes as {semantic+layer: array} (its vertex range) and its triangle list
        (indices relative to the submesh's first vertex)."""
        sm = self.submeshes[si]
        attrs = self.attrs[sm['vbuf']]
        out = {}
        for a in attrs:
            vb = self.vbufs[a['buffer']]
            if a['dtype'] not in DTYPES:
                continue
            arr = read_attr(self.data, vb['offset'], vb['stride'], vb['count'], a['offset'], a['dtype'])
            key = a['semantic'] + ('' if a['layer'] == 0 else str(a['layer']))
            out[key] = arr[sm['vstart']:sm['vstart'] + sm['vcount']]
        ib = self.ibufs[sm['ibuf']]
        dt = {1: np.uint8, 2: np.uint16, 4: np.uint32}[ib['width']]
        idx = np.frombuffer(self.data, dtype=dt, count=sm['icount'], offset=ib['offset'] + ib['width'] * sm['istart'])
        idx = idx.astype(np.int64)
        if sm['prim'] == 4:          # triangle strip
            tris = []
            flip = False
            for i in range(len(idx) - 2):
                a, b, c = idx[i], idx[i + 1], idx[i + 2]
                if a != b and b != c and a != c:
                    tris.append((a, c, b) if flip else (a, b, c))
                flip = not flip
            tris = np.array(tris, dtype=np.int64).reshape(-1, 3)
        else:
            tris = idx.reshape(-1, 3)
        return out, tris - sm['vstart']


def info(path, base_path=None):
    b = open(path, 'rb').read()
    print(path)
    for m, v, o, s in chunks(b):
        print('  %s %s %d bytes' % (m, v, s))
    ms, _ = chunk(b, 'G1MS')
    sk = Skeleton(ms) if ms else None
    if sk:
        print('  G1MS: %d joints, %d global ids, layer %d, external %s' % (sk.count, len(sk.global_of_local), sk.layer,
                                                                          sk.external))
    mg, _ = chunk(b, 'G1MG')
    if not mg:
        return
    g = Geometry(mg)
    print('  G1MG %x: %d sockets, %d materials, %d shader blocks, %d vbufs, %d attr sets, %d palettes, %d ibufs, '
          '%d submeshes, %d lod groups' % (g.version, len(g.sockets), len(g.materials), len(g.shaders), len(g.vbufs),
                                           len(g.attrs), len(g.palettes), len(g.ibufs), len(g.submeshes), len(g.lods)))
    for i, s in enumerate(g.submeshes):
        print('   sub %2d flags %3d vbuf %d pal %d mat %2d shader %2d prim %d verts %5d idx %6d' % (
            i, s['flags'], s['vbuf'], s['palette'], s['material'], s['shader'], s['prim'], s['vcount'], s['icount']))
    for l in g.lods:
        print('   lod %d group %d idx %d counts %s range %s' % (l['lod'], l['group'], l['group_index'], l['counts'],
                                                                l['range']))
        for m in l['meshes']:
            print('      %-16s cloth %d unk %d nun %d subs %s' % (m['name'], m['cloth'], m['unk'], m['nunid'],
                                                                  m['submeshes']))
    for i, a in enumerate(g.attrs):
        print('   attrs %d: %s' % (i, ', '.join('%s%d:%x@b%d+%d' % (x['semantic'], x['layer'], x['dtype'], x['buffer'],
                                                                     x['offset']) for x in a)))
    for i, m in enumerate(g.materials):
        print('   material %d %s: %s' % (i, m['unk'], ' '.join('t%d(l%d type%d/%d)' % (t['index'], t['layer'], t['type'],
                                                                                  t['subtype']) for t in m['textures'])))
    for i, sh in enumerate(g.shaders):
        print('   shader %d: %s' % (i, '; '.join('%s=%s' % (p['name'], json.dumps(p['values'])[:60]) for p in sh)))


if __name__ == '__main__':
    if sys.argv[1] == 'info':
        info(*sys.argv[2:4])
