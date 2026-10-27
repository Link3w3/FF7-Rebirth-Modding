import os, sys, struct
sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k, kh3dxbc

def shaders(pk):
    data = pk.data
    nm = pk.names
    # positions of FName refs to shader type / VF names
    marks = []
    want = {}
    for i, s in enumerate(nm):
        if ('VertexFactory' in s) or s.startswith(('TBasePass', 'TShadowDepth', 'FDepthOnly', 'TDepthOnly', 'FHitProxy', 'FVelocity',
                                                   'FFPostProcess', 'FPostProcess', 'TLightMapDensity', 'FDebugView', 'FConvertToUniform',
                                                   'FEvaluateSurfel', 'TTranslucency', 'FOnePass', 'FMeshDecal', 'TDeferredDecal',
                                                   'FDeferredDecal', 'TBasePassVS', 'TBasePassPS', 'FDistortion', 'TDistortion', 'FTranslucent',
                                                   'TMobile', 'FSelfShadow')) or s.endswith(('PS', 'VS', 'GS', 'HS', 'DS', 'CS')):
            want[i] = s
    out = []
    prev = 0
    blobs = kh3dxbc.blobs(data)
    for b in blobs:
        t = vf = None
        q = b['offset'] - 8
        lo = prev
        tpos = vfpos = None
        while q >= lo:
            i, n = struct.unpack_from('<ii', data, q)
            if n == 0 and i in want:
                s = want[i]
                if 'VertexFactory' in s:
                    if vf is None:
                        vf, vfpos = s, q
                elif t is None:
                    t, tpos = s, q
            if t is not None and vf is not None:
                break
            q -= 1
        out.append(dict(type=t, vf=vf, blob=b, tpos=tpos, vfpos=vfpos))
        prev = b['offset'] + b['size']
    return out

if __name__ == '__main__':
    base = sys.argv[1]
    pk = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
    sh = shaders(pk)
    # carry VF forward: a VF name appears once before its group
    import collections
    c = collections.Counter((s['type'], s['vf'], s['blob']['program']) for s in sh)
    for kk, n in sorted(c.items(), key=lambda x: str(x)):
        print(n, kk)
