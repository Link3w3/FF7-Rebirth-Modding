import sys, os, numpy as np
sys.path[:0] = ['/work/gamelight/tools', '/work/iostore', '/work/cs']
import gametex
from zen import Zen
P = '/work/fx1018/pkgs/'
FILES = {
  'BT709PQToACESBT2020PQ': '..__..__..__Engine__Content__EngineResources__VolumeBT709PQToACESBT2020PQ.uasset',
  'ACESBT2020PQToACESsRGB': '..__..__..__Engine__Content__EngineResources__VolumeACESBT2020PQToACESsRGB.uasset',
  'ACESBT2020PQ1000ToACESBT2020PQ250': '..__..__..__Engine__Content__EngineResources__VolumeACESBT2020PQ1000ToACESBT2020PQ250.uasset',
  'Default_day': 'Lighting__LUT__0001-COMMON__0001_Default_day.uasset',
  'SLUM7_day': 'Lighting__LUT__1200-GRASA__030-SLUM7_day_HDR.uasset',
}
def load(name):
    d = open(P + FILES[name], 'rb').read()
    z = Zen(d)
    pds = gametex.platform_data(d, z.names)
    assert pds, name
    t = pds[0]
    m = t['mips'][0]
    w, h, dz = m['x'], m['y'], m['z']
    fmt = t['fmt']
    data = m['data']
    if fmt == 'PF_FloatRGBA':
        a = np.frombuffer(data[:w*h*dz*8], np.float16).reshape(dz, h, w, 4).astype(np.float32)
    elif fmt == 'PF_A2B10G10R10':
        v = np.frombuffer(data[:w*h*dz*4], np.uint32).reshape(dz, h, w)
        a = np.stack([(v & 1023)/1023.0, ((v>>10)&1023)/1023.0, ((v>>20)&1023)/1023.0, (v>>30)/3.0], -1).astype(np.float32)
    elif fmt == 'PF_B8G8R8A8':
        a = np.frombuffer(data[:w*h*dz*4], np.uint8).reshape(dz, h, w, 4)[..., [2,1,0,3]].astype(np.float32)/255.0
    else:
        raise ValueError(fmt)
    return t, a
if __name__ == '__main__':
    out = {}
    for n in FILES:
        t, a = load(n)
        print(n, t['fmt'], t['x'], t['y'], t['slices'], [ (m['x'],m['y'],m['z'],m['size']) for m in t['mips']], a.shape, 'min', a[...,:3].min(), 'max', a[...,:3].max())
        np.save('/work/gamelight/lut/%s.npy' % n, a)
