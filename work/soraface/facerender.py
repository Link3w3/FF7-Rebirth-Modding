"""Renders Sora's face (front view, textured) for a pose of his face bones: a contact sheet tool for choosing facial poses.

    pose: {bone: (q [x,y,z,w], t [x,y,z])} local transforms; bones not given stay at the reference pose.
"""
import json
import numpy as np
from PIL import Image, ImageDraw
import fbxbin

SKEL = '/work/sora1019/flat/skel.json'
TEX = '/work/kh3mat1018/'
SK = json.load(open(SKEL))
NAMES = [b['name'] for b in SK]
PAR = [b['parent'] for b in SK]
IDX = {n: i for i, n in enumerate(NAMES)}
REFQ = np.array([b['q'] for b in SK], np.float64)
REFT = np.array([b['t'] for b in SK], np.float64)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)


def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0); vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2 * (y * vz - z * vy); ty = 2 * (z * vx - x * vz); tz = 2 * (x * vy - y * vx)
    return np.stack([vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)], -1)


def qinv(q):
    return q * np.array([-1, -1, -1, 1.0])


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def fk(LQ, LT):
    CQ = np.zeros_like(LQ); CT = np.zeros_like(LT)
    for i in range(len(LQ)):
        p = PAR[i]
        if p < 0:
            CQ[i] = LQ[i]; CT[i] = LT[i]
        else:
            assert p < i
            CQ[i] = qmul(CQ[p], LQ[i]); CT[i] = CT[p] + qrot(CQ[p], LT[i])
    return CQ, CT


REF_CQ, REF_CT = fk(REFQ, REFT)
_chk = np.array([b['cst'] for b in SK])
assert np.abs(_chk - REF_CT).max() < 1e-3, np.abs(_chk - REF_CT).max()


def uv0(geo):
    for le in geo.findall('LayerElementUV'):
        if le.props[0] == 0:
            uv = le.find('UV').props[0].reshape(-1, 2)
            if le.find('UVIndex') is not None:
                return uv[le.find('UVIndex').props[0]], False
            return uv, True
    raise KeyError('uv0')


class Face:
    MATS = {'p_ex011_F_mat0_Inst': 'face', 'p_ex011_EYE_Inst': 'eye', 'p_ex011_M_mat0_Inst': 'mouth',
            'p_ex011_E_mat2_Inst': 'lash', 'p_ex011_E_mat3_Inst': 'lash'}

    def __init__(self, fbx='/work/soraface/sora_mesh.fbx'):
        root, _ = fbxbin.read(fbx)
        objs = root.find('Objects')
        by_id = {k.props[0]: k for k in objs.kids}
        conn = [(c.props[1], c.props[2]) for c in root.find('Connections').kids if c.props[0] == 'OO']
        children = {}
        parents = {}
        for ch, pa in conn:
            children.setdefault(pa, []).append(ch); parents.setdefault(ch, []).append(pa)
        geo = next(k for k in objs.kids if k.name == 'Geometry')
        V = geo.find('Vertices').props[0].reshape(-1, 3).astype(np.float64); V[:, 1] *= -1
        pvi = geo.find('PolygonVertexIndex').props[0]
        ends = np.nonzero(pvi < 0)[0]
        idx = pvi.copy(); idx[ends] = -idx[ends] - 1
        T = idx.reshape(-1, 3)
        uvs, per_vertex = uv0(geo)
        UV = uvs[T] if per_vertex else uvs.reshape(-1, 3, 2)
        mats = geo.find('LayerElementMaterial').find('Materials').props[0]
        mesh_model = next(p for p in parents[geo.props[0]] if by_id.get(p) is not None and by_id[p].name == 'Model')
        mat_names = [by_id[c].props[1].split('\x00')[0] for c in children.get(mesh_model, []) if by_id.get(c) is not None and by_id[c].name == 'Material']
        keep = np.array([self.MATS.get(mat_names[m]) is not None for m in mats])
        self.kind = [self.MATS[mat_names[m]] for m in mats[keep]]
        T = T[keep][:, ::-1]; UV = UV[keep][:, ::-1]
        used = np.unique(T)
        remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
        self.V = V[used]; self.T = remap[T]; self.UV = UV
        # skin weights for the kept vertices
        self.W = []
        skin = next(k for k in objs.kids if k.name == 'Deformer' and k.props[2] == 'Skin')
        for cid in children.get(skin.props[0], []):
            cl = by_id[cid]
            if cl.name != 'Deformer' or cl.find('Indexes') is None:
                continue
            bones = [by_id[c] for c in children.get(cid, []) if by_id.get(c) is not None and by_id[c].name == 'Model']
            bname = bones[0].props[1].split('\x00')[0]
            vi = remap[cl.find('Indexes').props[0].astype(np.int64)]
            w = cl.find('Weights').props[0].astype(np.float64)
            m = vi >= 0
            if m.any():
                self.W.append((IDX[bname], vi[m], w[m]))
        # eye colouring: angle of each eye vertex from its eye's forward (+X) at the reference pose
        self.eyecol = np.zeros((len(self.V), 3))
        ev = np.unique(self.T[np.array([k == 'eye' for k in self.kind])])
        lens = np.unique(T[np.array([mat_names[m] == 'p_ex011_Eyelens_Inst' for m in mats[keep]])]) if False else None
        lv = V[np.unique(idx.reshape(-1, 3)[np.array([mat_names[m] == 'p_ex011_Eyelens_Inst' for m in mats])])]
        for side in ('R_eye', 'L_eye'):
            c = REF_CT[IDX[side]]
            mine = ev[(self.V[ev, 1] > 0) == (c[1] > 0)]
            fwd = lv[(lv[:, 1] > 0) == (c[1] > 0)].mean(0) - c; fwd /= np.linalg.norm(fwd)
            d = self.V[mine] - c; d /= np.linalg.norm(d, axis=1, keepdims=True)
            ang = np.degrees(np.arccos(np.clip(d @ fwd, -1, 1)))
            col = np.where(ang[:, None] < 14, [0.05, 0.05, 0.12], np.where(ang[:, None] < 33, [0.25, 0.45, 0.95], [0.97, 0.97, 0.97]))
            self.eyecol[mine] = col
        self.tex = {
            'face': np.asarray(Image.open(TEX + 'texp011/Character__pc__p_ex011__mdl__mat0__p_ex011_F_0d00.png').convert('RGB'), np.float32) / 255,
            'lash': np.asarray(Image.open(TEX + 'texp011/Character__pc__p_ex011__mdl__mat0__p_ex011_E_0d01.png').convert('RGBA'), np.float32) / 255,
            'mouth': np.asarray(Image.open(TEX + 'tex/Shader__Material_set__SQEX_MouthTexSet__Mouth_M_0d00.png').convert('RGB'), np.float32) / 255,
        }

    def skin(self, pose):
        LQ = REFQ.copy(); LT = REFT.copy()
        for b, (q, t) in pose.items():
            if b in IDX:
                LQ[IDX[b]] = q; LT[IDX[b]] = t
        CQ, CT = fk(LQ, LT)
        out = np.zeros_like(self.V)
        for bi, vi, w in self.W:
            dq = qmul(CQ[bi], qinv(REF_CQ[bi]))
            R = qmat(dq); t = CT[bi] - R @ REF_CT[bi]
            out[vi] += w[:, None] * (self.V[vi] @ R.T + t)
        return out

    def render(self, pose, scale=22.0, box=(-8.6, 8.6, 135.2, 155.5), label=None):
        P = self.skin(pose)
        y0, y1, z0, z1 = box
        Wd = int((y1 - y0) * scale); Ht = int((z1 - z0) * scale)
        sx = (y1 - P[:, 1]) * scale          # Sora's right (+Y) on the viewer's left
        sy = (z1 - P[:, 2]) * scale
        dep = P[:, 0]
        img = np.ones((Ht, Wd, 3), np.float32) * np.array([0.82, 0.84, 0.88], np.float32)
        zb = np.full((Ht, Wd), -1e9, np.float32)
        L = np.array([0.8, -0.25, 0.55]); L /= np.linalg.norm(L)
        tri = self.T
        e1 = P[tri[:, 1]] - P[tri[:, 0]]; e2 = P[tri[:, 2]] - P[tri[:, 0]]
        nrm = np.cross(e1, e2); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        for k in range(len(tri)):
            kind = self.kind[k]
            if kind != 'lash' and nrm[k, 0] < -0.05:
                continue
            a, b, c = tri[k]
            xs = np.array([sx[a], sx[b], sx[c]]); ys = np.array([sy[a], sy[b], sy[c]])
            minx = max(int(np.floor(xs.min())), 0); maxx = min(int(np.ceil(xs.max())), Wd - 1)
            miny = max(int(np.floor(ys.min())), 0); maxy = min(int(np.ceil(ys.max())), Ht - 1)
            if minx > maxx or miny > maxy:
                continue
            gx, gy = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9:
                continue
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not inside.any():
                continue
            d = w0 * dep[a] + w1 * dep[b] + w2 * dep[c]
            if kind == 'lash':
                d = d + 0.02
            sub = zb[miny:maxy + 1, minx:maxx + 1]
            m = inside & (d > sub)
            if not m.any():
                continue
            shade = 0.6 + 0.4 * max(0.0, float(nrm[k] @ L))
            if kind == 'eye':
                col = w0[..., None] * self.eyecol[a] + w1[..., None] * self.eyecol[b] + w2[..., None] * self.eyecol[c]
                col = col * (0.85 + 0.15 * shade)
            else:
                uv = self.UV[k]
                u = w0 * uv[0, 0] + w1 * uv[1, 0] + w2 * uv[2, 0]
                v = w0 * uv[0, 1] + w1 * uv[1, 1] + w2 * uv[2, 1]
                tex = self.tex[kind]
                th, tw = tex.shape[:2]
                tx = np.clip((u % 1.0) * tw, 0, tw - 1).astype(int); ty = np.clip(((1 - v) % 1.0) * th, 0, th - 1).astype(int)
                col = tex[ty, tx]
                if kind == 'lash':
                    m = m & (col[..., 3] > 0.45)
                    col = np.broadcast_to(np.array([0.12, 0.07, 0.05], np.float32), col.shape[:-1] + (3,))
                else:
                    col = col[..., :3] * shade
            sub[m] = d[m]
            img[miny:maxy + 1, minx:maxx + 1][m] = col[m]
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        if label:
            dr = ImageDraw.Draw(im)
            dr.rectangle([0, 0, Wd, 14], fill=(30, 30, 30))
            dr.text((3, 1), label, fill=(255, 255, 255))
        return im


def pose_from_track(track, frame):
    """{bone: (q, t)} at a frame of a dumped track file (tracks/<name>.json)."""
    out = {}
    for b, tr in track['bones'].items():
        q = tr['q'][min(frame, len(tr['q']) - 1)]; t = tr['p'][min(frame, len(tr['p']) - 1)]
        out[b] = (np.array(q, np.float64), np.array(t, np.float64))
    return out


def sheet(images, cols, path):
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    s = Image.new('RGB', (w * cols, h * rows), (255, 255, 255))
    for i, im in enumerate(images):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    s.save(path)
    return path
