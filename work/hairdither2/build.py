"""HairDitherFix 2.0: the game's hair carriers (RMI_Surface_Hair_Wide, RMI_Surface_Hair_Wetness_Wide) with their base pass
and depth pass pixel shaders patched (irpatch.py: all 64 blue-noise slices, hashed alpha anchored to the texture
coordinates, the game's own cut-offs), their shader maps inline, packed as one override container."""
import hashlib, json, os, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/custmat', '/work/fx1018/editor/Python']
import lz4.block
import irpatch
from custom_mi import with_inline_shaders, unique_shader_map_id, wrap_shader
from carriers import Carrier, PKGS
from pack_anime import raw_bundle
from rebirth_fx import matcore, fxcore

DXC = '/home/user/microsoft/dxc-build/bin/'
ENV = dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib')
CARRIERS = ['RMI_Surface_Hair_Wide', 'RMI_Surface_Hair_Wetness_Wide']
PATCH_TYPES = ('TBasePassPS', 'fa99734846c7227e', 'TDepthOnlyPS')
HEADER = '/work/custmat/pakchunk4_container_header.bin'


def run(args):
    r = subprocess.run(args, env=ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('%s failed:\n%s%s' % (args[0], r.stdout[-2000:], r.stderr[-2000:]))
    return r.stdout


def patch_blob(blob, work, tag, hashed=True):
    at = blob.find(b'DXBC')
    total = struct.unpack_from('<I', blob, at + 24)[0]
    src = os.path.join(work, tag + '.orig.dxbc')
    open(src, 'wb').write(blob[at:at + total])
    text = run([DXC + 'dxc', '-dumpbin', src])
    out, rep = irpatch.patch(text, hashed=hashed)
    ll = os.path.join(work, tag + '.ll')
    open(ll, 'w').write(out)
    asm = os.path.join(work, tag + '.dxbc')
    run([DXC + 'dxa', ll, '-o', asm])
    signed = os.path.join(work, tag + '.signed.dxbc')
    v = run([DXC + 'dxv', asm, '-o', signed])
    if 'Validation succeeded' not in v:
        raise RuntimeError('validation: ' + v)
    new = wrap_shader(blob, open(signed, 'rb').read())
    return new, rep


def carrier_package(name, work, report, hashed=True):
    path = PKGS + 'Renderer__MaterialInstance__Surface__%s.uasset' % name
    data = open(path, 'rb').read()
    c = Carrier(path)
    bundle = raw_bundle(os.path.join(HERE, 'bundles', name + '.bundle'))
    assert [b['index'] for b in bundle] == c.order, 'bundle order differs from the shader map'
    types = {}
    for s in c.shaders:
        types.setdefault(s['res'], set()).add(s['type'])
    shaders, patched = [], {}
    for res, s in enumerate(bundle):
        blob = lz4.block.decompress(s['code'], uncompressed_size=s['usize']) if len(s['code']) != s['usize'] else s['code']
        want = s['freq'] == 5 and any(t.startswith(PATCH_TYPES) for t in types.get(res, ()))
        if want and b'DXBC' in blob:
            try:
                new, rep = patch_blob(blob, work, '%s_%d' % (name, res), hashed=hashed)
            except irpatch.PatchError as e:
                rep = None
                patched[res] = dict(types=sorted(types[res]), skipped=str(e))
            if rep is not None:
                shaders.append(dict(hash=hashlib.sha1(new).digest(), code=new, usize=len(new), freq=s['freq']))
                rep['types'] = sorted(types[res])
                patched[res] = rep
                continue
        shaders.append(dict(hash=s['hash'], code=s['code'], usize=s['usize'], freq=s['freq']))
    mi, _ = unique_shader_map_id(data, 'HairDitherFix2.0:' + name + (':hashed' if hashed else ':slices'))
    mi = with_inline_shaders(mi, shaders)
    check = matcore.MaterialInstance(mi, 'check')
    assert not check.pkg.errors, check.pkg.errors
    s1, z1 = check.z.bundle_positions()[check.index]
    s0, z0 = c.mi.z.bundle_positions()[c.mi.index]
    assert mi[s1:s1 + check.v.size] == data[s0:s0 + c.mi.v.size], 'the property block changed'
    report[name] = dict(size=len(mi), shaders=len(shaders), patched={str(k): v for k, v in sorted(patched.items())})
    return mi


def main(out_dir, mod_name='HairDitherFix_P', hashed=True):
    work = os.path.join(HERE, 'work')
    os.makedirs(work, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    packages = [carrier_package(n, work, report, hashed=hashed) for n in CARRIERS]
    files = fxcore.build_mod(packages, [open(HEADER, 'rb').read()], out_dir, mod_name)
    json.dump(report, open(os.path.join(out_dir, mod_name + '.report.json'), 'w'), indent=1)
    return files, report


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
    hashed = not (len(sys.argv) > 2 and sys.argv[2] == 'slices')
    files, report = main(out, hashed=hashed)
    for f in files:
        print(f, os.path.getsize(f))
    for k, v in report.items():
        n_ok = sum(1 for x in v['patched'].values() if 'skipped' not in x)
        n_skip = [(r, x['skipped']) for r, x in v['patched'].items() if 'skipped' in x]
        print(k, 'size', v['size'], 'shaders', v['shaders'], 'patched', n_ok, 'skipped', n_skip)
