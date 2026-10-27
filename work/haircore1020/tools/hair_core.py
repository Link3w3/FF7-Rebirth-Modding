"""Young Sephiroth's hair core: an opaque shell inside his hair cards, as Rebirth's own characters have. Sephiroth's
PC0010_00 carries a section PC0010_00_HairCore (an instance of RMI_Surface_Hair_Wide with his hair's own textures,
BLEND_Masked): a smooth closed shell that sits ~0.5 cm over his scalp with ~2 cm of hair cards outside it, and runs on
down his back inside his long hair, so the alpha-tested cards never show the head or the background through their gaps.

His core is built the same way, over his head mesh (head_geo, in the scene build_blend.build_scene makes: centimetres,
facing +X, Z up), as a grid in polar coordinates around the centre of his skull (a sphere fitted to the scalp):
  * theta from the crown (0) down to an edge theta_max(phi) per azimuth phi (from the back):
      - the hairline: where the head texture stops being painted hair (grey: R - B small) going down from the crown;
      - at the back, further down the neck while his hair still covers it (at least 2 cards outside at every step),
        stopping 1.5 cm short of where the cover ends; smoothed around the head;
    rings at fractions of theta_max, so the last ring is the edge;
  * each grid point: the head's skin along that direction (ray from the centre), lifted along the skin's normal: up to
    0.5 cm (Sephiroth's), never past 60% of the way to the median hair card above it (most cards stay outside), and
    easing to 0.12 cm over the last 1.5 cm before the edge, so the edge meets the skin under the hair;
  * UVs: u from the azimuth, mirrored (the back 0, the front 1), v from theta: into the top-left panel of his hair colour
    texture (silver, fine vertical strands), so the strands run down from the crown, with no seam anywhere;
  * weights: the head's, interpolated at the skin point under each grid point (C_Head_a, the nape's neck bones), so the
    core moves with his skin exactly and never leaves it, whatever the hair's Bonamik does;
  * vertex colour white, material slot PC0010_13_HairCore.
"""
import math
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from PIL import Image

CORE_NAME = 'PC0010_13_HairCore_geo'
CORE_MAT = 'PC0010_13_HairCore'
# the hair colour texture's silver panel (pixels of the 512 x 512 texture, from its top-left corner)
PANEL = (8.0, 8.0, 200.0, 248.0)
TEX = 512.0
RIGID = ('C_Head_a', 'C_Neck_a', 'C_Neck_b', 'C_Spine_d')


def _bilinear(img, uv):
    H, W = img.shape[:2]
    x = np.clip(uv[:, 0] * W - 0.5, 0, W - 1)
    y = np.clip((1.0 - uv[:, 1]) * H - 0.5, 0, H - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, W - 1), np.minimum(y0 + 1, H - 1)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) +
            img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def mesh_arrays(ob):
    me = ob.data
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    W = np.array(ob.matrix_world)
    co = co @ W[:3, :3].T + W[:3, 3]
    tri = np.array([p.vertices[:] for p in me.polygons])
    return me, co, tri


class Skin:
    """The head mesh as ray target: hit point, smooth normal, UV, painted-hair mask and bone weights at the hit."""

    def __init__(self, ob, tex_path, lo=0.075, hi=0.105):
        me, co, tri = mesh_arrays(ob)
        self.ob, self.co, self.tri = ob, co, tri
        self.bvh = BVHTree.FromPolygons(co.tolist(), tri.tolist(), all_triangles=True)
        # per-corner UVs and normals, per face
        n_l = len(me.loops)
        uv = np.zeros(n_l * 2)
        me.uv_layers['UVMap'].data.foreach_get('uv', uv)
        nrm = np.zeros(n_l * 3)
        if hasattr(me, 'corner_normals'):
            me.corner_normals.foreach_get('vector', nrm)
        else:
            me.calc_normals_split()
            me.loops.foreach_get('normal', nrm)
        li = np.array([p.loop_indices[:] for p in me.polygons])
        self.face_uv = uv.reshape(-1, 2)[li]           # (faces, 3, 2)
        self.face_n = nrm.reshape(-1, 3)[li]           # (faces, 3, 3)
        img = np.asarray(Image.open(tex_path).convert('RGB'), np.float32) / 255.0
        self.img, self.lo, self.hi = img, lo, hi
        gname = {g.index: g.name for g in ob.vertex_groups}
        self.weights = [{gname[g.group]: g.weight for g in v.groups if g.weight > 0} for v in me.vertices]

    def hit(self, origin, d):
        loc, fn, fi, dist = self.bvh.ray_cast(Vector(origin), Vector(d), 100.0)
        if loc is None:
            return None
        p = np.array(loc)
        a, b, c = self.co[self.tri[fi]]
        v0, v1, v2 = b - a, c - a, p - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        w1 = (d11 * d20 - d01 * d21) / den
        w2 = (d00 * d21 - d01 * d20) / den
        bc = np.array([1 - w1 - w2, w1, w2])
        n = bc @ self.face_n[fi]
        n /= np.linalg.norm(n)
        uv = bc @ self.face_uv[fi]
        return dict(p=p, n=n, uv=uv, face=fi, bc=bc, dist=dist)

    def hairy(self, h):
        rgb = _bilinear(self.img, h['uv'][None])[0]
        return float(np.clip((self.hi - (rgb[0] - rgb[2])) / (self.hi - self.lo), 0.0, 1.0))

    def weights_at(self, h):
        out = {}
        for vi, b in zip(self.tri[h['face']], h['bc']):
            for n, w in self.weights[vi].items():
                out[n] = out.get(n, 0.0) + w * b
        return out


class Cards:
    """The hair cards as ray target: the distinct cards crossed along a ray."""

    def __init__(self, obs):
        vs, fs, base = [], [], 0
        for ob in obs:
            _, co, tri = mesh_arrays(ob)
            vs.append(co)
            fs.append(tri + base)
            base += len(co)
        self.bvh = BVHTree.FromPolygons(np.concatenate(vs).tolist(), np.concatenate(fs).tolist(), all_triangles=True)

    def crossings(self, origin, d, far=8.0):
        out = []
        o = Vector(origin)
        dv = Vector(d)
        t = 0.0
        while t < far:
            loc, fn, fi, dist = self.bvh.ray_cast(o, dv, far - t)
            if loc is None:
                break
            t += dist
            if not out or t - out[-1] > 0.02:      # (his cards are doubled: one crossing per card)
                out.append(t)
            o = loc + dv * 0.005
            t += 0.005
        return out


def sphere_fit(P):
    A = np.c_[2 * P, np.ones(len(P))]
    b = (P ** 2).sum(1)
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = x[:3]
    return c, math.sqrt(x[3] + c @ c)


def direction(theta, phi):
    """theta from +Z (the crown), phi from the back (-X) towards +Y."""
    st = math.sin(theta)
    return np.array([-st * math.cos(phi), st * math.sin(phi), math.cos(theta)])


def make_core(coll, arm_ob, head_tex, hair_names=('hair_geo', 'hair_tp_geo'), lift=0.5, lift_edge=0.12, ramp=1.5,
              share=0.6, n_phi=60, n_rings=22, report=None):
    report = report if report is not None else {}
    skin = Skin(coll.objects['head_geo'], head_tex)
    cards = Cards([coll.objects[n] for n in hair_names])

    # the skull's centre: a sphere through the painted scalp
    mask_v = np.zeros(len(skin.co))
    me = skin.ob.data
    lv = np.zeros(len(me.loops), int)
    me.loops.foreach_get('vertex_index', lv)
    uv = skin.face_uv.reshape(-1, 2)
    li = np.array([p.loop_indices[:] for p in me.polygons]).ravel()
    rgb = _bilinear(skin.img, uv)
    hv = np.clip((skin.hi - (rgb[:, 0] - rgb[:, 2])) / (skin.hi - skin.lo), 0, 1)
    acc, cnt = np.zeros(len(skin.co)), np.zeros(len(skin.co))
    np.add.at(acc, lv[li], hv)
    np.add.at(cnt, lv[li], 1)
    mask_v = acc / np.maximum(cnt, 1)
    top = skin.co[:, 2] > np.percentile(skin.co[:, 2], 60)
    C, R = sphere_fit(skin.co[(mask_v > 0.5) & top])
    report['skull_centre'] = C.round(2).tolist()
    report['skull_radius'] = round(R, 2)

    # per azimuth: the hairline, and at the back how far down the hair still covers the neck
    phis = np.linspace(-math.pi, math.pi, n_phi, endpoint=False)
    dt = math.radians(1.0)
    hairline = np.zeros(n_phi)
    cover = np.zeros(n_phi)
    for j, phi in enumerate(phis):
        th = dt
        last_hair = 0.0
        while th < math.radians(175):
            h = skin.hit(C, direction(th, phi))
            if h is None or skin.hairy(h) < 0.5:
                break
            last_hair = th
            th += dt
        hairline[j] = last_hair
        th = last_hair
        last_cov = last_hair
        while th < math.radians(170):
            h = skin.hit(C, direction(th, phi))
            if h is None:
                break
            if len(cards.crossings(h['p'] + h['n'] * 0.05, h['n'])) < 2:
                break
            last_cov = th
            th += dt
        cover[j] = last_cov
    # the back of the neck (within 50 deg of the back, easing out by 80: his ears are at ~85): down the neck as far as
    # the hair covers it, less 1.5 cm
    a = np.abs(phis)
    taper = np.clip((math.radians(80) - a) / math.radians(30), 0.0, 1.0)
    taper = taper * taper * (3 - 2 * taper)
    shrink = 1.5 / R
    edge = hairline + taper * np.maximum(cover - shrink - hairline, 0.0)
    # smooth around the head (circular), then never below the hairline - 2 deg (no bald notch)
    for _ in range(6):
        edge = 0.25 * np.roll(edge, 1) + 0.5 * edge + 0.25 * np.roll(edge, -1)
    edge = np.minimum(edge, np.maximum(hairline, cover))
    report['hairline_deg'] = dict(min=round(math.degrees(hairline.min()), 1), max=round(math.degrees(hairline.max()), 1))
    report['edge_deg'] = [round(math.degrees(e), 1) for e in edge]

    # the grid
    rows = []
    pole = skin.hit(C, direction(0.0, 0.0))
    for k in range(1, n_rings + 1):
        rows.append([(k / n_rings * edge[j], phis[j]) for j in range(n_phi)])
    pts, nrm, wts, info = [], [], [], []
    for th, phi in [(0.0, 0.0)] + [p for r in rows for p in r]:
        h = skin.hit(C, direction(th, phi))
        assert h is not None, ('no skin under the core', math.degrees(th), math.degrees(phi))
        info.append((th, phi, h))
    # lift
    L = []
    for i, (th, phi, h) in enumerate(info):
        cr = cards.crossings(h['p'] + h['n'] * 0.02, h['n'])
        cap = share * (np.median(cr) + 0.02) if cr else lift
        e = edge[np.argmin(np.abs(((phis - phi + math.pi) % (2 * math.pi)) - math.pi))] if th > 0 else 1.0
        to_edge = (e - th) * R if th > 0 else 99.0
        s = np.clip(to_edge / ramp, 0.0, 1.0)
        s = s * s * (3 - 2 * s)
        want = lift_edge + (lift - lift_edge) * s
        L.append((max(min(want, cap), 0.06), len(cr)))
    lifts = np.array([l for l, _ in L])
    ncross = np.array([n for _, n in L])
    # smooth the lift on the grid (rings x azimuths, the pole apart)
    G = lifts[1:].reshape(n_rings, n_phi)
    for _ in range(3):
        G = 0.5 * G + 0.125 * (np.roll(G, 1, 1) + np.roll(G, -1, 1) + np.vstack([G[:1], G[:-1]]) + np.vstack([G[1:], G[-1:]]))
    lifts[1:] = np.minimum(G.ravel(), lifts[1:] + 0.1)
    Q = np.array([h['p'] + h['n'] * l for (th, phi, h), l in zip(info, lifts)])
    W = [skin.weights_at(h) for (th, phi, h) in info]

    # faces: the pole fan, then quads split into two triangles (outward: counter-clockwise seen from outside)
    F = []
    for j in range(n_phi):
        a, b = 1 + j, 1 + (j + 1) % n_phi
        F.append((0, a, b))
    for k in range(n_rings - 1):
        r0, r1 = 1 + k * n_phi, 1 + (k + 1) * n_phi
        for j in range(n_phi):
            j1 = (j + 1) % n_phi
            a, b, c, d = r0 + j, r0 + j1, r1 + j1, r1 + j
            F += [(a, d, c), (a, c, b)]
    F = np.array(F)
    # orient outward (away from the skull centre)
    fn = np.cross(Q[F[:, 1]] - Q[F[:, 0]], Q[F[:, 2]] - Q[F[:, 0]])
    out = np.einsum('ij,ij->i', fn, Q[F].mean(1) - C)
    if (out < 0).mean() > 0.5:
        F = F[:, ::-1]
        fn = -fn
        out = -out
    report['faces_facing_out'] = float((out > 0).mean())

    # UVs: mirrored azimuth, theta down the panel
    u = np.array([abs(phi) / math.pi for th, phi, h in info])
    v = np.array([th for th, phi, h in info]) / max(edge.max(), 1e-6)
    px = PANEL[0] + u * (PANEL[2] - PANEL[0])
    py = PANEL[1] + v * (PANEL[3] - PANEL[1])
    UV = np.stack([px / TEX, 1.0 - py / TEX], axis=1)

    report.update(core_vertices=int(len(Q)), core_faces=int(len(F)),
                  lift_cm=dict(min=round(float(lifts.min()), 3), median=round(float(np.median(lifts)), 3), max=round(float(lifts.max()), 3)),
                  cards_outside=dict(min=int(ncross.min()), median=float(np.median(ncross)), none=int((ncross == 0).sum()),
                                     fewer_than_2=int((ncross < 2).sum())),
                  bounds_cm=[Q.min(0).round(2).tolist(), Q.max(0).round(2).tolist()])

    me2 = bpy.data.meshes.new(CORE_NAME)
    me2.from_pydata(Q.tolist(), [], F.tolist())
    me2.validate(verbose=False)
    assert len(me2.polygons) == len(F), ('faces dropped', len(me2.polygons), len(F))
    uvl = me2.uv_layers.new(name='UVMap')
    li2 = np.zeros(len(me2.loops), int)
    me2.loops.foreach_get('vertex_index', li2)
    uvl.uv.foreach_set('vector', UV[li2].ravel())
    ca = me2.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.ones(len(Q) * 4))
    mat = bpy.data.materials.get(CORE_MAT) or bpy.data.materials.new(CORE_MAT)
    me2.materials.append(mat)
    me2.shade_smooth()
    ob2 = bpy.data.objects.new(CORE_NAME, me2)
    coll.objects.link(ob2)
    ob2.parent = arm_ob
    groups = {}
    dropped = {}
    for i, w in enumerate(W):
        # only the skull and neck carry it (his jaw and lip bones reach the nape's skin faintly: the core must not talk)
        for n in [n for n in w if n not in RIGID]:
            dropped[n] = max(dropped.get(n, 0.0), w.pop(n))
        if not w:
            w = {'C_Head_a': 1.0}
        tot = sum(w.values())
        for n, x in w.items():
            if x / tot < 1e-3:
                continue
            if n not in groups:
                groups[n] = ob2.vertex_groups.new(name=n)
            groups[n].add([i], x / tot, 'REPLACE')
    mod = ob2.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm_ob
    report['bones'] = sorted(groups)
    report['weights_dropped_max'] = {k: round(v, 3) for k, v in dropped.items()}
    return ob2, report
