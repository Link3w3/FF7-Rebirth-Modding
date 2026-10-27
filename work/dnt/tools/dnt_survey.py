"""Features of every Dissidia NT motion (retargeted, as dnt_anim.py does) to tell them apart: length, travel, hip height,
the Masamune tip's speed (swings), and a contact sheet per batch (front view, Rebirth bones, the blade 200 cm).
    dnt_survey.py <motion folder> <model npz> <base g1m> <out folder>"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g2a, dnt_anim
from ccretarget import q2m
EDGES = [('C_Hip_a', 'C_Spine_b'), ('C_Spine_b', 'C_Spine_d'), ('C_Spine_d', 'C_Neck_a'), ('C_Neck_a', 'C_Head_a'),
         ('C_Spine_d', 'L_Shoulder_a'), ('L_Shoulder_a', 'L_UpperArm_a'), ('L_UpperArm_a', 'L_Forearm_a'), ('L_Forearm_a', 'L_Hand_a'),
         ('C_Spine_d', 'R_Shoulder_a'), ('R_Shoulder_a', 'R_UpperArm_a'), ('R_UpperArm_a', 'R_Forearm_a'), ('R_Forearm_a', 'R_Hand_a'),
         ('C_Hip_a', 'L_UpperLeg_a'), ('L_UpperLeg_a', 'L_Foreleg_a'), ('L_Foreleg_a', 'L_Foot_a'), ('L_Foot_a', 'L_Toe_a'),
         ('C_Hip_a', 'R_UpperLeg_a'), ('R_UpperLeg_a', 'R_Foreleg_a'), ('R_Foreleg_a', 'R_Foot_a'), ('R_Foot_a', 'R_Toe_a')]

def blade(rig, G, T):
    w = rig.ix['R_Weapon_a']
    d = np.einsum('fij,j->fi', G[:, w] @ dnt_anim.SOCKET_R, np.array([1.0, 0, 0]))
    return T[:, w], T[:, w] + 200 * d

def main(folder, model, base, out, per=10, cols=7):
    os.makedirs(out, exist_ok=True)
    skel = dnt_anim.DntSkeleton(base); rig = dnt_anim.Rig(model, skel)
    files = sorted(f for f in os.listdir(folder) if f.endswith('.g1a'))
    feats = []
    sheet, row = None, 0
    W, H = 150, 190
    batch = 0
    def flush():
        nonlocal sheet, batch
        if sheet is not None:
            sheet.save(os.path.join(out, 'sheet_%02d.png' % batch)); batch += 1
        sheet = None
    for f in files:
        mot = g2a.read(os.path.join(folder, f))
        LQ, LT, G, T, rep = rig.retarget(mot, travel=False)
        g0, tip = blade(rig, G, T)
        sp = np.linalg.norm(np.diff(tip, axis=0), axis=1) * mot.fps / 100.0      # m/s
        fast = sp > 12
        swings = int(np.sum(fast[1:] & ~fast[:-1]) + (1 if fast[0] else 0))
        hip = T[:, rig.ix['C_Hip_a']]
        hand_up = float(np.max(T[:, rig.ix['L_Hand_a'], 2] - T[:, rig.ix['C_Head_a'], 2]))
        fe = dict(clip=f[:-4], frames=mot.frames, fps=mot.fps, sec=round(mot.length / mot.fps, 2),
                  travel=round(float(np.linalg.norm(hip[-1, :2] - hip[0, :2])), 1), maxtravel=round(float(np.max(np.linalg.norm(hip[:, :2] - hip[0, :2], axis=1))), 1),
                  hip=[round(float(hip[:, 2].min()), 1), round(float(hip[:, 2].max()), 1)], swings=swings,
                  tipmax=round(float(sp.max()), 1), lhand_over_head=round(hand_up, 1),
                  loopish=round(float(np.abs(LQ[0] - LQ[-1]).max()), 3))
        feats.append(fe)
        if sheet is None:
            sheet = Image.new('RGB', (W * cols + 120, H * per), 'white'); row = 0
        d = ImageDraw.Draw(sheet)
        d.text((4, row * H + 4), '%s %.2fs' % (fe['clip'], fe['sec']), fill='black')
        d.text((4, row * H + 18), 'tr %s sw %d' % (fe['maxtravel'], swings), fill='black')
        d.text((4, row * H + 32), 'hip %s' % (fe['hip'],), fill='black')
        fr = np.linspace(0, mot.frames - 1, cols).astype(int)
        for c, k in enumerate(fr):
            ox, oy = 120 + c * W + W // 2, row * H + H - 12
            def pt(p):
                # front-ish view: x = UE Y (right) minus a bit of X depth, y = up
                return (ox + (p[1] - hip[0, 1]) * 0.55 + (p[0] - hip[0, 0]) * 0.25, oy - p[2] * 0.55)
            for a, b in EDGES:
                d.line([pt(T[k, rig.ix[a]]), pt(T[k, rig.ix[b]])], fill=(40, 40, 160) if a.startswith('L') or b.startswith('L') else (160, 40, 40) if a.startswith('R') or b.startswith('R') else (0, 0, 0), width=2)
            d.line([pt(g0[k]), pt(tip[k])], fill=(0, 150, 0), width=2)
            d.ellipse([pt(T[k, rig.ix['C_Head_a']])[0] - 5, pt(T[k, rig.ix['C_Head_a']])[1] - 9, pt(T[k, rig.ix['C_Head_a']])[0] + 5, pt(T[k, rig.ix['C_Head_a']])[1] + 1], outline='black')
            d.line([(ox - 50, oy), (ox + 50, oy)], fill=(180, 180, 180))
            d.text((ox - 10, row * H + 4), str(k), fill=(120, 120, 120))
        row += 1
        if row == per:
            flush()
    flush()
    json.dump(feats, open(os.path.join(out, 'features.json'), 'w'), indent=0)
    for fe in feats:
        print('%-10s %5.2fs tr %6.1f/%6.1f hip %-14s swings %d tipmax %5.1f lh %6.1f loop %.3f' % (
            fe['clip'], fe['sec'], fe['travel'], fe['maxtravel'], fe['hip'], fe['swings'], fe['tipmax'], fe['lhand_over_head'], fe['loopish']))

if __name__ == '__main__':
    main(*sys.argv[1:5])
