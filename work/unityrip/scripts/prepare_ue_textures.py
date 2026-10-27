"""The Unity textures (extract_unity.py's PNGs) split the way Rebirth's RM_Surface reads them:
  _C   colour (sRGB, RGB only)                     -> TC_DEFAULT, sRGB
  _A   coverage (the colour map's alpha)           -> TC_ALPHA (BC4)
  _N   normal (OpenGL / Y+ as Unity; the editor flips green)   -> TC_NORMALMAP
  _Mr  metallic   (MROX R x _Metallic)             -> TC_ALPHA
  _Mg  roughness  (MROX G as roughness, the smoothness scaled by _GlossMapScale: 1 - (1 - G) x scale)  -> TC_ALPHA
Single-channel maps are written grey with the same value in alpha, so they read the same whichever channel the
compressor takes.

    prepare_ue_textures.py <model dir> <out dir>
"""
import json, os, sys
import numpy as np
from PIL import Image

PREFIX = 'CH049_001_'


def load(model_dir, name):
    return np.asarray(Image.open(os.path.join(model_dir, 'textures', name + '.png')).convert('RGBA')).astype(np.float64) / 255.0


def save_rgb(a, path):
    Image.fromarray(np.clip(np.round(a[..., :3] * 255), 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)


def save_mask(v, path):
    g = np.clip(np.round(v * 255), 0, 255).astype(np.uint8)
    Image.fromarray(np.stack([g, g, g, g], -1), 'RGBA').save(path, optimize=True)


def main(model_dir, out):
    os.makedirs(out, exist_ok=True)
    info = json.load(open(os.path.join(model_dir, 'model.json')))
    M = info['materials']
    made = {}

    def put(kind, part, arr, fn):
        p = os.path.join(out, PREFIX + part + '_' + kind + '.png')
        fn(arr, p)
        made[PREFIX + part + '_' + kind] = os.path.basename(p)

    # colour + coverage
    for part, tex in [('Body', 'tex_ch049_001_body_AAAT'), ('Head', 'tex_ch049_001_head_AAAX'), ('Hair', 'tex_ch049_001_hair_AAAT'),
                      ('Eye', 'tex_ch049_001_eye_AAAX'), ('EyeShadow', 'tex_ch049_001_eye_shadow_AAAT')]:
        a = load(model_dir, tex)
        put('C', part, a, save_rgb)
        if tex.endswith('AAAT'):
            put('A', part, a[..., 3], save_mask)
    # normals (already rebuilt to RGB by extract_unity.py)
    for part, tex in [('Body', 'tex_ch049_001_body_NNNX'), ('Head', 'tex_ch049_001_head_NNNX')]:
        put('N', part, load(model_dir, tex), save_rgb)
    # metallic / roughness from MROX with each material's own scales
    for part, tex, mat in [('Body', 'tex_ch049_001_body_MROX', 'mat_ch049_001_body'), ('Head', 'tex_ch049_001_head_MROX', 'mat_ch049_001_head'),
                           ('Hair', 'tex_ch049_001_hair_MROX', 'mat_ch049_001_hair')]:
        a = load(model_dir, tex)
        f = M[mat]['floats']
        metal = a[..., 0] * f.get('_Metallic', 1.0)
        gs = f.get('_GlossMapScale', 1.0)
        rough = 1.0 - (1.0 - a[..., 1]) * gs
        if metal.max() > 0 and part != 'Hair':          # (hair: Rebirth's hair shading takes no metal; Unity's 0.65 was a toon tint)
            put('Mr', part, metal, save_mask)
        put('Mg', part, rough, save_mask)
        print(part, 'metal mean %.3f' % metal.mean(), 'rough mean %.3f' % rough.mean())
    json.dump(made, open(os.path.join(out, 'textures.json'), 'w'), indent=1)
    print(len(made), 'textures:', ' '.join(sorted(made)))


if __name__ == '__main__':
    main(*sys.argv[1:])
