"""KH3 cooked static meshes (.uasset + .uexp) -> their LOD0 render data (positions, normals, tangents, UVs, colours,
indices, sections, material slots), for writing out as FBX the editor imports.

    python3 kh3mesh.py <mesh .uasset> ...      (prints what each one holds)
"""
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import tagged            # noqa: E402


class R(object):
    def __init__(self, d, p):
        self.d, self.p = d, p

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]
        self.p += 4
        return v

    def take(self, n):
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def bulk(self):
        """TResourceArray::BulkSerialize: element size, count, the elements."""
        size, count = self.i32(), self.i32()
        if size < 0 or count < 0 or size * count > len(self.d) - self.p:
            raise ValueError('bulk array %d x %d at %d does not fit' % (size, count, self.p - 8))
        return size, count, self.take(size * count)


def _half(h):
    return struct.unpack('<e', struct.pack('<H', h))[0]


def _packed_normal(b):
    return tuple(x / 127.5 - 1.0 for x in b[:3]), b[3] / 127.5 - 1.0


def read_mesh(uasset, uexp):
    pk = k.Package(uasset, uexp)
    e = [x for x in pk.exports if pk.class_name(x) == 'StaticMesh'][0]
    end = e['offset'] + e['size']
    props = tagged.parse(pk.data, e['offset'], end, pk.names)
    d = pk.data

    def ref(i):
        if i < 0:
            im = pk.imports[-i - 1]
            outer = im['outer']
            pkg = pk.imports[-outer - 1]['name'] if outer < 0 else None
            return '%s.%s' % (pkg, im['name']) if pkg else im['name']
        return pk.exports[i - 1]['name'] if i > 0 else None

    slots = []
    sm = tagged.find(props, 'StaticMaterials')
    if sm is not None:
        for (s, t, refs) in sm.elements:
            ch = tagged.parse(d, s, t, pk.names)
            mi = tagged.find(ch, 'MaterialInterface')
            sn = tagged.find(ch, 'MaterialSlotName')
            slot = dict(material=ref(struct.unpack_from('<i', d, mi.value_start)[0]) if mi else None,
                        name=tagged._name(d, sn.value_start, pk.names) if sn else 'Slot%d' % len(slots))
            slots.append(slot)
    r = R(d, props.end)
    r.take(4)                                  # object guid flag
    strip = r.take(2)
    cooked = r.i32()
    if not cooked:
        raise ValueError('not cooked')
    r.i32(), r.i32()                           # body setup, nav collision
    r.take(16)                                 # lighting guid
    nsock = r.i32()
    r.take(4 * nsock)
    nlod = r.i32()
    if not 1 <= nlod <= 8:
        raise ValueError('%d LODs' % nlod)
    # LOD 0
    lstrip = r.take(2)
    nsec = r.i32()
    sections = []
    for _ in range(nsec):
        mat, first, ntri, vmin, vmax, col, shadow = struct.unpack_from('<iIIIIii', d, r.p)
        r.p += 28
        sections.append(dict(material=mat, first=first, triangles=ntri, vmin=vmin, vmax=vmax))
    r.f32()                                    # max deviation
    stride, nverts = r.u32(), r.u32()
    size, count, pos = r.bulk()
    if stride != 12 or size != 12 or count != nverts:
        raise ValueError('positions: stride %d size %d count %d verts %d' % (stride, size, count, nverts))
    positions = [struct.unpack_from('<3f', pos, i * 12) for i in range(nverts)]
    vstrip = r.take(2)
    ntex, vstride, vverts = r.u32(), r.u32(), r.u32()
    full_uv, hp_tangent = r.i32(), r.i32()
    size, count, vb = r.bulk()
    if vverts != nverts or count != nverts or size != vstride:
        raise ValueError('vertex buffer: %d verts %d count %d size %d stride' % (vverts, count, size, vstride))
    tb = 16 if hp_tangent else 8
    ub = 8 if full_uv else 4
    if tb + ub * ntex != vstride:
        raise ValueError('vertex stride %d != tangents %d + %d uv x %d' % (vstride, tb, ntex, ub))
    normals, tangents, uvs = [], [], [[] for _ in range(ntex)]
    for i in range(nverts):
        o = i * vstride
        if hp_tangent:
            raise ValueError('high precision tangents')
        tx, _ = _packed_normal(vb[o:o + 4])
        tz, sign = _packed_normal(vb[o + 4:o + 8])
        tangents.append(tx)
        normals.append((tz, sign))
        for c in range(ntex):
            q = o + tb + c * ub
            if full_uv:
                uvs[c].append(struct.unpack_from('<2f', vb, q))
            else:
                h = struct.unpack_from('<2H', vb, q)
                uvs[c].append((_half(h[0]), _half(h[1])))
    cstrip = r.take(2)
    cstride, cverts = r.u32(), r.u32()
    colors = None
    if cverts:
        size, count, cb = r.bulk()
        if count != nverts or size != 4:
            raise ValueError('colours: %d x %d' % (size, count))
        colors = [tuple(cb[i * 4 + j] for j in (2, 1, 0, 3)) for i in range(nverts)]   # BGRA -> RGBA
    b32 = r.i32()
    size, count, ib = r.bulk()
    n = count // (4 if b32 else 2)
    indices = list(struct.unpack_from('<%d%s' % (n, 'I' if b32 else 'H'), ib, 0))
    return dict(name=e['name'], slots=slots, sections=sections, positions=positions, normals=normals, tangents=tangents,
                uvs=uvs, colors=colors, indices=indices, strip=(strip, lstrip, vstrip, cstrip), full_uv=full_uv)


def load(path):
    base = path[:-7] if path.endswith('.uasset') else path
    return read_mesh(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())


# ---------------------------------------------------------------------------------------------------------------------
# FBX (7.3 ASCII) out. The file is declared Z-up / -Y front / right-handed, which is the axis system the editor's FBX
# import converts to, so nothing is converted; the import then turns every position and normal (x, y, z) into
# (x, -y, z), so they go out with y negated and come back as they were.
# ---------------------------------------------------------------------------------------------------------------------

def _arr(vals, fmt='%.6g'):
    out = []
    line = []
    for i, v in enumerate(vals):
        line.append(fmt % v if isinstance(v, float) else str(v))
        if len(line) == 24:
            out.append(','.join(line))
            line = []
    if line:
        out.append(','.join(line))
    return ',\n\t\t\t\t'.join(out)


def to_fbx(m, name=None):
    name = name or m['name']
    P = m['positions']
    I = m['indices']
    nrm = m['normals']
    verts = []
    for (x, y, z) in P:
        verts += [float(x), float(-y), float(z)]
    pvi = []
    for t in range(0, len(I), 3):
        a, b, c = I[t], I[t + 1], I[t + 2]
        pvi += [a, b, -c - 1]
    normals = []
    for v in I:
        (nx, ny, nz), _ = nrm[v]
        normals += [float(nx), float(-ny), float(nz)]
    layers = []
    uv_blocks = []
    for c, uv in enumerate(m['uvs']):
        flat = []
        for (u, v) in uv:
            flat += [float(u), float(1.0 - v)]          # FBX v runs up; the import flips it back
        uv_blocks.append('''		LayerElementUV: %d {
			Version: 101
			Name: "UVChannel_%d"
			MappingInformationType: "ByPolygonVertex"
			ReferenceInformationType: "IndexToDirect"
			UV: *%d {
				a: %s
			}
			UVIndex: *%d {
				a: %s
			}
		}
''' % (c, c + 1, len(flat), _arr(flat), len(I), _arr(I)))
    color_block = ''
    if m['colors']:
        flat = []
        for (r, g, b, a) in m['colors']:
            flat += [(r + 0.5) / 255.0, (g + 0.5) / 255.0, (b + 0.5) / 255.0, (a + 0.5) / 255.0]   # the import truncates 255 * c
        color_block = '''		LayerElementColor: 0 {
			Version: 101
			Name: "Col"
			MappingInformationType: "ByPolygonVertex"
			ReferenceInformationType: "IndexToDirect"
			Colors: *%d {
				a: %s
			}
			ColorIndex: *%d {
				a: %s
			}
		}
''' % (len(flat), _arr(flat), len(I), _arr(I))
    # one material per slot; each triangle takes its section's slot
    slots = m['slots'] or [dict(name='Slot0', material=None)]
    tri_mat = [0] * (len(I) // 3)
    for s in m['sections']:
        for t in range(s['first'] // 3, s['first'] // 3 + s['triangles']):
            tri_mat[t] = max(0, min(s['material'], len(slots) - 1))
    mat_block = '''		LayerElementMaterial: 0 {
			Version: 101
			Name: ""
			MappingInformationType: "ByPolygon"
			ReferenceInformationType: "IndexToDirect"
			Materials: *%d {
				a: %s
			}
		}
''' % (len(tri_mat), _arr(tri_mat))
    layer0 = ['LayerElementNormal', 'LayerElementMaterial'] + (['LayerElementColor'] if m['colors'] else []) + \
             (['LayerElementUV'] if m['uvs'] else [])
    layer_text = '''		Layer: 0 {
			Version: 100
%s		}
''' % ''.join('''			LayerElement:  {
				Type: "%s"
				TypedIndex: 0
			}
''' % t for t in layer0)
    for c in range(1, len(m['uvs'])):
        layer_text += '''		Layer: %d {
			Version: 100
			LayerElement:  {
				Type: "LayerElementUV"
				TypedIndex: %d
			}
		}
''' % (c, c)
    geo_id, model_id = 2000000001, 3000000001
    mats = ''
    conns = ['\tC: "OO",%d,0' % model_id, '\tC: "OO",%d,%d' % (geo_id, model_id)]
    for i, s in enumerate(slots):
        mid = 4000000001 + i
        mats += '''	Material: %d, "Material::%s", "" {
		Version: 102
		ShadingModel: "phong"
		MultiLayer: 0
		Properties70:  {
			P: "DiffuseColor", "Color", "", "A",0.8,0.8,0.8
		}
	}
''' % (mid, s['name'])
        conns.append('\tC: "OO",%d,%d' % (mid, model_id))
    text = '''; FBX 7.3.0 project file
; written by kh3mesh.py from a KINGDOM HEARTS III cooked static mesh
; ----------------------------------------------------

FBXHeaderExtension:  {
	FBXHeaderVersion: 1003
	FBXVersion: 7300
	Creator: "kh3mesh"
}
GlobalSettings:  {
	Version: 1000
	Properties70:  {
		P: "UpAxis", "int", "Integer", "",2
		P: "UpAxisSign", "int", "Integer", "",1
		P: "FrontAxis", "int", "Integer", "",1
		P: "FrontAxisSign", "int", "Integer", "",-1
		P: "CoordAxis", "int", "Integer", "",0
		P: "CoordAxisSign", "int", "Integer", "",1
		P: "OriginalUpAxis", "int", "Integer", "",2
		P: "OriginalUpAxisSign", "int", "Integer", "",1
		P: "UnitScaleFactor", "double", "Number", "",1
		P: "OriginalUnitScaleFactor", "double", "Number", "",1
	}
}
Documents:  {
	Count: 1
	Document: 1000000001, "", "Scene" {
		Properties70:  {
			P: "SourceObject", "object", "", ""
			P: "ActiveAnimStackName", "KString", "", "", ""
		}
		RootNode: 0
	}
}
References:  {
}
Definitions:  {
	Version: 100
	Count: %d
	ObjectType: "GlobalSettings" {
		Count: 1
	}
	ObjectType: "Model" {
		Count: 1
	}
	ObjectType: "Geometry" {
		Count: 1
	}
	ObjectType: "Material" {
		Count: %d
	}
}
Objects:  {
	Geometry: %d, "Geometry::%s", "Mesh" {
		Vertices: *%d {
			a: %s
		}
		PolygonVertexIndex: *%d {
			a: %s
		}
		GeometryVersion: 124
		LayerElementNormal: 0 {
			Version: 101
			Name: ""
			MappingInformationType: "ByPolygonVertex"
			ReferenceInformationType: "Direct"
			Normals: *%d {
				a: %s
			}
		}
%s%s%s%s	}
	Model: %d, "Model::%s", "Mesh" {
		Version: 232
		Properties70:  {
			P: "DefaultAttributeIndex", "int", "Integer", "",0
		}
		Shading: T
		Culling: "CullingOff"
	}
%s}
Connections:  {
%s
}
''' % (3 + len(slots), len(slots), geo_id, name, len(verts), _arr(verts), len(pvi), _arr(pvi), len(normals),
       _arr(normals), ''.join(uv_blocks), color_block, mat_block, layer_text, model_id, name, mats, '\n'.join(conns))
    return text


def write_fbx(path, out_dir):
    m = load(path)
    out = os.path.join(out_dir, m['name'] + '.fbx')
    with open(out, 'w') as f:
        f.write(to_fbx(m))
    return m, out


if __name__ == '__main__':
    if sys.argv[1] == '--fbx':
        os.makedirs(sys.argv[2], exist_ok=True)
        for p in sys.argv[3:]:
            m, out = write_fbx(p, sys.argv[2])
            print(out, len(m['positions']), 'verts', len(m['indices']) // 3, 'tris')
        sys.exit(0)
    for p in sys.argv[1:]:
        m = load(p)
        bb = [(min(v[i] for v in m['positions']), max(v[i] for v in m['positions'])) for i in range(3)]
        print('%-20s verts %5d tris %5d uv %d colours %s  sections %s  slots %s  bounds %s' % (
            m['name'], len(m['positions']), len(m['indices']) // 3, len(m['uvs']), bool(m['colors']),
            [(s['material'], s['triangles']) for s in m['sections']], [(s['name'], s['material']) for s in m['slots']],
            ' '.join('%.1f..%.1f' % b for b in bb)))
