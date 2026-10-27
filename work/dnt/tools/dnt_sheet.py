"""Side and top views of chosen Dissidia NT motions (retargeted), 9 frames each: for picking moves.
    dnt_sheet.py <motion folder> <model npz> <base g1m> <out png> <clip,clip,...>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g2a, dnt_anim
from dnt_survey import EDGES, blade

def main(folder, model, base, out, clips, cols=9):
    skel = dnt_anim.DntSkeleton(base); rig = dnt_anim.Rig(model, skel)
    clips = clips.split(',')
    W, H = 128, 150
    img = Image.new('RGB', (110 + cols * W, len(clips) * H * 2), 'white')
    d = ImageDraw.Draw(img)
    for r, c in enumerate(clips):
        mot = g2a.read(os.path.join(folder, c + '.g1a'))
        LQ, LT, G, T, rep = rig.retarget(mot, travel=False)
        g0, tip = blade(rig, G, T)
        hip = T[:, rig.ix['C_Hip_a']]
        y0 = r * H * 2
        d.text((4, y0 + 4), c, fill='black'); d.text((4, y0 + 18), '%.2fs %df' % (mot.length / mot.fps, mot.frames), fill='black')
        d.text((4, y0 + 32), 'side (fwd ->)', fill='gray'); d.text((4, y0 + H + 4), 'top (fwd ->)', fill='gray')
        fr = np.linspace(0, mot.frames - 1, cols).astype(int)
        span = max(1.0, np.ptp(hip[:, 0]), np.ptp(hip[:, 1]))
        for k_i, k in enumerate(fr):
            ox = 110 + k_i * W + W // 2
            for view in (0, 1):
                oy = y0 + (H - 10 if view == 0 else H + H // 2)
                def pt(p):
                    if view == 0:
                        return (ox + (p[0] - hip[k, 0]) * 0.33, oy - p[2] * 0.33 * (1 if True else 1))
                    return (ox + (p[0] - hip[k, 0]) * 0.33, oy - (p[1] - hip[k, 1]) * 0.33)
                for a, b in EDGES:
                    col = (40, 40, 160) if 'L_' in a + b else (160, 40, 40) if 'R_' in a + b else (0, 0, 0)
                    d.line([pt(T[k, rig.ix[a]]), pt(T[k, rig.ix[b]])], fill=col, width=2)
                d.line([pt(g0[k]), pt(tip[k])], fill=(0, 150, 0), width=2)
                h = pt(T[k, rig.ix['C_Head_a']]); d.ellipse([h[0] - 4, h[1] - 4, h[0] + 4, h[1] + 4], outline='black')
                if view == 0:
                    d.line([(ox - 45, oy), (ox + 45, oy)], fill=(190, 190, 190))
            d.text((ox - 30, y0 + 2), '%d x%+.0f y%+.0f' % (k, hip[k, 0] - hip[0, 0], hip[k, 1] - hip[0, 1]), fill=(110, 110, 110))
    img.save(out)

if __name__ == '__main__':
    main(*sys.argv[1:6])
