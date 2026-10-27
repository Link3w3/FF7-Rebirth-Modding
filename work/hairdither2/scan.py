"""Find the shaders of a carrier that dither against the spatiotemporal blue noise (the View frame index & 7 slice)."""
import sys, os, struct, subprocess, re, json
sys.path.insert(0, '/work/custmat')
import lz4.block
from carriers import Carrier, PKGS
from pack_anime import raw_bundle
DXC = '/home/user/microsoft/dxc-build/bin/dxc'
ENV = dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib')
B = '/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/anime/'

def blob_of(s):
    return lz4.block.decompress(s['code'], uncompressed_size=s['usize']) if len(s['code']) != s['usize'] else s['code']

def dxil_text(blob, tmp):
    at = blob.find(b'DXBC')
    total = struct.unpack_from('<I', blob, at + 24)[0]
    open(tmp, 'wb').write(blob[at:at + total])
    r = subprocess.run([DXC, '-dumpbin', tmp], env=ENV, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

PAT_FRAME = re.compile(r'%(\d+) = call %dx\.types\.CBufRet\.i32 @dx\.op\.cbufferLoadLegacy\.i32\(i32 59, %dx\.types\.Handle %(\d+), i32 175\)')

def scan(carrier, bundle_path, out_dir):
    c = Carrier(PKGS + 'Renderer__MaterialInstance__Surface__%s.uasset' % carrier)
    bundle = raw_bundle(bundle_path)
    assert [b['index'] for b in bundle] == c.order
    types = {}
    for s in c.shaders:
        types.setdefault(s['res'], set()).add(s['type'])
    hits = {}
    for res, s in enumerate(bundle):
        if s['freq'] != 5:
            continue
        blob = blob_of(s)
        txt = dxil_text(blob, os.path.join(out_dir, 'tmp.dxbc'))
        if txt is None:
            continue
        uses_frame = PAT_FRAME.search(txt)
        and7 = re.search(r'= and i32 %\d+, 7\n', txt)
        tex3d = 'Texture3D' in txt
        if uses_frame and and7 and tex3d:
            hits[res] = sorted(types.get(res, []))
            open(os.path.join(out_dir, '%s_%d.ll' % (carrier, res)), 'w').write(txt)
    return hits

if __name__ == '__main__':
    carrier = sys.argv[1]
    hits = scan(carrier, B + carrier + '.bundle', sys.argv[2])
    for k, v in sorted(hits.items()):
        print(k, v)
    json.dump({str(k): v for k, v in hits.items()}, open(os.path.join(sys.argv[2], carrier + '_hits.json'), 'w'), indent=1)
