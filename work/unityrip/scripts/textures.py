import sys, os, numpy as np, UnityPy
env = UnityPy.load(sys.argv[1]); out = sys.argv[2]
for o in env.objects:
    if o.type.name == 'Texture2D':
        t = o.read()
        img = t.image
        p = os.path.join(out, t.m_Name + '.png')
        img.save(p)
        a = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
        st = ' '.join('%s[%.2f..%.2f m%.2f]' % (c, a[..., i].min(), a[..., i].max(), a[..., i].mean()) for i, c in enumerate('RGBA'))
        print(t.m_Name, t.m_Width, t.m_Height, t.m_TextureFormat, 'mips', t.m_MipCount, 'cs', getattr(t, 'm_ColorSpace', '?'), st)
