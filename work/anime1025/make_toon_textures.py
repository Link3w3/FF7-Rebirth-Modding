"""All the toonier textures for Anime Sephiroth and his Masamune: colour textures flattened (toonify3.toon_flat, settings per
texture), normal maps softened (toonify.soft_normal). Writes toon/<name>_Toon.png and a contact sheet."""
import sys, time
import numpy as np
from PIL import Image
sys.path.insert(0, '/work/anime1025')
from toonify3 import toon_flat
from toonify import soft_normal

COLOR = {
    'PC0010_00_BodyA_C': dict(),
    'PC0010_00_BodyB_C': dict(),
    'PC0010_00_Head_C': dict(detail_s=12, detail_r=0.12, wide_s=100, wide_r=0.07, flatten=0.55, sat=1.1),
    'PC0010_00_Hair_C': dict(detail_s=10, detail_r=0.2, wide_s=60, wide_r=0.1, flatten=0.5, sat=1.1),
    'PC0010_10_Wing_C': dict(detail_s=20, detail_r=0.2, wide_s=120, wide_r=0.1, flatten=0.6),
    'PC0010_00_Eye_C': dict(detail_s=4, detail_r=0.15, wide_s=24, wide_r=0.1, flatten=0.4, sat=1.3),
    'WE1021_00_Body_C': dict(detail_s=15, detail_r=0.2, wide_s=80, wide_r=0.1, flatten=0.6),
}
NORMAL = {
    'PC0010_00_BodyA_N': dict(sigma=3.0, flatten=0.7),
    'PC0010_00_BodyB_N': dict(sigma=3.0, flatten=0.7),
    'PC0010_00_Head_N': dict(sigma=4.0, flatten=0.6),
    'PC0010_00_Hair_N': dict(sigma=1.5, flatten=0.8),
    'PC0010_10_Wing_N': dict(sigma=2.0, flatten=0.8),
    'WE1021_00_Body_N': dict(sigma=1.5, flatten=0.7),
}

if __name__ == '__main__':
    t0 = time.time()
    for name, kw in COLOR.items():
        rgb = np.array(Image.open('tex/%s.png' % name).convert('RGB'))
        Image.fromarray(toon_flat(rgb, **kw)).save('toon/%s_Toon.png' % name)
        print(name, 'done %.1f s' % (time.time() - t0))
    for name, kw in NORMAL.items():
        rg = np.array(Image.open('tex/%s.png' % name).convert('RGBA'))[..., :2]
        Image.fromarray(soft_normal(rg, **kw)).save('toon/%s_Toon.png' % name)
        print(name, 'done %.1f s' % (time.time() - t0))
