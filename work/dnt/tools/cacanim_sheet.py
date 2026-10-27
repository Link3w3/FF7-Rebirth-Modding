"""What the game gets: .cacanim key animations (local keys per bone) put together on the model's bone hierarchy and
drawn, side and top views, with the Masamune on R_Weapon_a's socket (200 cm of blade), root motion included.
    cacanim_sheet.py <model npz> <out png> <cacanim> [<cacanim> ...]"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/work/ccanim/tools')
from ccretarget import q2m, order
import dnt_anim
from dnt_survey import EDGES

def read(path):
    b = open(path, 'rb').read()
    assert b[:8] == b'CACANIM1'
    ver, fps, F, loop, n = struct.unpack_from('<IfiIi', b, 8)
    p = 28
    tracks = {}
    for _ in range(n):
        ln = struct.unpack_from('<H', b, p)[0]; p += 2
        name = b[p:p + ln].decode(); p += ln
        k = struct.unpack_from('<i', b, p)[0]; p += 4
        a = np.frombuffer(b, '<f4', k * 10, p).reshape(k, 10).astype(float); p += k * 40
        tracks[name] = a
    return fps, F, bool(loop), tracks

def pose(model, tracks, F):
    m = np.load(model)
    names = [str(x) for x in m['bone_names']]; par = [int(x) for x in m['bone_parents']]
    Rn = q2m(m['bone_cq']); Pn = m['bone_ct'].astype(float)
    NB = len(names)
    G = np.zeros((F, NB, 3, 3)); T = np.zeros((F, NB, 3))
    for i in order(par):
        p = par[i]
        if names[i] in tracks:
            a = tracks[names[i]]
            a = np.repeat(a, F, 0) if len(a) == 1 else a
            Lr, Lt = q2m(a[:, 3:7]), a[:, 0:3]
        else:
            if p < 0:
                Lr = np.repeat(Rn[i][None], F, 0); Lt = np.repeat(Pn[i][None], F, 0)
            else:
                Lr = np.repeat((Rn[p].T @ Rn[i])[None], F, 0); Lt = np.repeat((Rn[p].T @ (Pn[i] - Pn[p]))[None], F, 0)
        if p < 0:
            G[:, i] = Lr; T[:, i] = Lt
        elif names[p] == 'Trans':
            # the game's root: its children in component axes (as the retarget wrote them), offset by the root's travel
            G[:, i] = Lr; T[:, i] = T[:, p] + Lt
        else:
            G[:, i] = G[:, p] @ Lr; T[:, i] = T[:, p] + np.einsum('fij,fj->fi', G[:, p], Lt)
    return names, G, T

def main(model, out, paths, cols=9):
    W, H = 128, 150
    img = Image.new('RGB', (130 + cols * W, len(paths) * H * 2), 'white')
    d = ImageDraw.Draw(img)
    for r, path in enumerate(paths):
        fps, F, loop, tracks = read(path)
        names, G, T = pose(model, tracks, F)
        ix = {n: i for i, n in enumerate(names)}
        w = ix['R_Weapon_a']
        bl = np.einsum('fij,j->fi', G[:, w] @ dnt_anim.SOCKET_R, np.array([1.0, 0, 0]))
        g0, tip = T[:, w], T[:, w] + 200 * bl
        y0 = r * H * 2
        root = T[:, ix['Trans']]
        d.text((4, y0 + 4), os.path.basename(path)[:-8], fill='black')
        d.text((4, y0 + 18), '%.2fs %df %s' % ((F - 1) / fps, F, 'loop' if loop else ''), fill='black')
        d.text((4, y0 + 32), 'root %+.0f %+.0f' % tuple(root[-1, :2] - root[0, :2]), fill='black')
        fr = np.linspace(0, F - 1, cols).astype(int)
        for c, k in enumerate(fr):
            ox = 130 + c * W + W // 2
            for view in (0, 1):
                oy = y0 + (H - 10 if view == 0 else H + H // 2)
                def pt(p):
                    if view == 0:
                        return (ox + (p[0] - root[k, 0]) * 0.33, oy - p[2] * 0.33)
                    return (ox + (p[0] - root[k, 0]) * 0.33, oy - (p[1] - root[k, 1]) * 0.33)
                for a, b in EDGES:
                    col = (40, 40, 160) if 'L_' in a + b else (160, 40, 40) if 'R_' in a + b else (0, 0, 0)
                    d.line([pt(T[k, ix[a]]), pt(T[k, ix[b]])], fill=col, width=2)
                d.line([pt(g0[k]), pt(tip[k])], fill=(0, 150, 0), width=2)
                hd = pt(T[k, ix['C_Head_a']]); d.ellipse([hd[0] - 4, hd[1] - 4, hd[0] + 4, hd[1] + 4], outline='black')
                if view == 0:
                    d.line([(ox - 45, oy), (ox + 45, oy)], fill=(190, 190, 190))
                    rp = pt(root[k]); d.ellipse([rp[0] - 2, rp[1] - 2, rp[0] + 2, rp[1] + 2], fill=(0, 160, 160))
            d.text((ox - 30, y0 + 2), '%d (%.2fs)' % (k, k / fps), fill=(110, 110, 110))
    img.save(out)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
