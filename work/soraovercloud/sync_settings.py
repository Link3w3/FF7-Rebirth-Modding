"""Cloud's per-animation settings onto Sora's retargeted animations, in their cooked packages (no editor):

    bPoseAnimation, OverrideBehaviorActionBlendTime / BlendOutTime, RootMotionScale, bEnableRootMotion, RootMotionRootLock,
    bForceRootLock, bUseNormalizedRootMotionScale, RateScale, Interpolation

Each of Sora's AnimSequence exports gets exactly the values Cloud's animation of the same set and name serializes for these
(a value Cloud's leaves out is left out: the game's default), so a pose loop is a pose (bPoseAnimation), an ability blends
in as fast as Cloud's and a hit reaction that Cloud plays without root motion has none for Sora either. The End editor
cannot write all of them itself: a value equal to the editor's own default (0 for a blend time, false for root motion)
is not saved, while the game's defaults differ (its cooked packages store those zeros).

The property block is written again (rebirth_fx.uwrite: Sora's own values byte for byte, the synced ones Cloud's bytes or
zero flags), the padding before the ACL block set again so the block stays 16-aligned, the package laid out the way the
game reads animations (align_moves.realign) and checked (build_sora_assets.verify_anim); everything else in the
container stays byte for byte.

    sync_settings.py <in .utoc> <out dir (new)> <name> <Cloud packages dir> [<Cloud packages dir> ...]
      (Cloud's packages as extract.py names them: Motion__<path>.uasset)
"""
import glob, hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/soraovercloud', '/work/soradata', '/work/iostore', '/work/cs',
                '/work/swap1012/tools', '/work/sephforms/tools', '/work/fx1018/editor/Python']
import build_sora_assets as B
from build_sora_assets import A, W, hdr, Toc, Zen, Package
from rebirth_fx import matcore, uwrite
import build_overcloud as O

SYNC = ('bPoseAnimation', 'OverrideBehaviorActionBlendTime', 'OverrideBehaviorActionBlendOutTime', 'RootMotionScale',
        'bEnableRootMotion', 'RootMotionRootLock', 'bForceRootLock', 'bUseNormalizedRootMotionScale', 'RateScale',
        'Interpolation')
SORA, CLOUD = 'PC0000_00_Sora_KH2', 'PC0000_Cloud'
MISSING = object()


def anim_export(data, label):
    pkg = Package(data, label)
    hits = [(i, v) for i, (cls, v, b) in pkg.exports.items() if cls == 'AnimSequence']
    assert len(hits) == 1, (label, len(hits))
    i, v = hits[0]
    s, size = Zen(data).bundle_positions()[i]
    assert v.at == 0, label
    return i, v, data[s:s + size]


def raw_fields(v, ex):
    return {k: (None if x.zero else bytes(ex[x.at:x.at + x.size])) for k, x in v.value.items()}


def sync(sdata, cdata, label, u):
    """Sora's package with Cloud's SYNC values: (bytes, [changed keys]) (the input itself when nothing differs)."""
    si, sv, sex = anim_export(sdata, label)
    ci, cv, cex = anim_export(cdata, label + ' (Cloud)')
    fields = raw_fields(sv, sex)
    cloud = raw_fields(cv, cex)
    changed = []
    for k in SYNC:
        want, have = cloud.get(k, MISSING), fields.get(k, MISSING)
        if want == have:
            continue
        if want is MISSING:
            del fields[k]
        else:
            fields[k] = want
        changed.append(k)
    if not changed:
        return sdata, []
    block = uwrite.struct_bytes(u, 'AnimSequence', fields)
    rest = sex[sv.at + sv.size:]
    # after the properties: guid flag (4), SkeletonGuid (16), block size (4), tag (4), align (2), pad (2), pad bytes, block
    bsize, tag = struct.unpack_from('<II', rest, 20)
    assert tag > 0xffff, (label, 'no aligned ACL block header')
    align, pad = struct.unpack_from('<HH', rest, 28)
    assert align == 16 and not any(rest[32:32 + pad]), (label, align, pad)
    assert (sv.size + 32 + pad) % 16 == 0, (label, 'the block was not 16-aligned in its export')
    new_pad = (-(len(block) + 32)) % 16
    new_ex = block + rest[:28] + struct.pack('<HH', align, new_pad) + b'\0' * new_pad + rest[32 + pad:]
    out = matcore.replace_export(O.no_pad(sdata), si, new_ex)
    out = A.realign(out)
    # checks: the synced values are Cloud's, every other value and the native data Sora's own
    ni, nv, nex = anim_export(out, label)
    got = raw_fields(nv, nex)
    assert got == fields, (label, 'the properties did not write back')
    assert nex[nv.size:nv.size + 28] == rest[:28] and nex[nv.size + 32 + new_pad:] == rest[32 + pad:], label
    assert (nv.size + 32 + new_pad) % 16 == 0
    zs, zo = Zen(sdata), Zen(out)
    assert zo.names == zs.names and zo.imports == zs.imports and len(zo.exports) == len(zs.exports), label
    ps, po = zs.bundle_positions(), zo.bundle_positions()
    for j in range(len(zs.exports)):
        if j == si:
            continue
        a, b = sdata[ps[j][0]:ps[j][0] + ps[j][1]], out[po[j][0]:po[j][0] + po[j][1]]
        assert b[:len(a)] == a and not any(b[len(a):]), (label, j)
    blocks = B.verify_anim(out, label, need_block=True)
    assert blocks >= 1, label
    return out, changed


def cloud_index(dirs):
    """{Cloud's package path ('Motion/...'): file}"""
    out = {}
    for d in dirs:
        for f in glob.glob(os.path.join(d, 'Motion__*.uasset')):
            out.setdefault(os.path.basename(f)[:-7].replace('__', '/'), f)
    return out


def cloud_of(path, cloud):
    """Sora's package path -> Cloud's original of it (his folder; a FromCloud battle animation is Cloud's of that name)"""
    if path.count('/%s/' % CLOUD) == 1:
        c = path                                  # (a copy in Cloud's folder: SoraOverCloudMotion_P)
    elif path.count('/%s/' % SORA) == 1 or path.endswith('/' + SORA):
        c = O.cloud_path('/Game/' + path)[len('/Game/'):]
    else:
        return None
    for cand in (c, c.replace('/Battle00/FromCloud/', '/Battle00/'), c.replace('/Battle01/FromCloud/', '/Battle01/')):
        if cand in cloud:
            return cloud[cand]
    return None


def main(in_utoc, out, name, *cloud_dirs):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    u = matcore.usmap()
    cloud = cloud_index(cloud_dirs)
    chunks, store = B.read(in_utoc)
    report, counts = [], {}
    entries = []
    for c in chunks:
        if c['type'] != 2:
            continue
        e = B.entry(c, store[c['id64']])
        z = Zen(c['data'])
        f = cloud_of(c['path'][:-len('.uasset')], cloud) if z.flags & A.PKG_ALIGNED_EXPORTS else None
        if f:
            try:
                is_seq = anim_export(c['data'], c['path'])
            except AssertionError:
                is_seq = None                      # (a blend space)
            if is_seq:
                new, changed = sync(c['data'], open(f, 'rb').read(), c['path'], u)
                if changed:
                    c['data'] = new
                    e['size'] = len(new) | (A.SHIFT << 60)
                    report.append((c['path'], ', '.join(changed)))
                    for k in changed:
                        counts[k] = counts.get(k, 0) + 1
        entries.append(e)
    os.makedirs(out)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=B.MOUNT)
    shutil.copy(in_utoc[:-5] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == B.MOUNT + c['path'], c['path']
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
    old = Toc(in_utoc)
    old_at = {(old.chunk_id64(i), old.chunk_type(i)): i for i in range(1, old.entries)}
    changed_paths = {p for p, _ in report}
    same = 0
    for i in range(1, back.entries):
        if back.files.get(i, '')[len(B.MOUNT):] in changed_paths:
            continue
        assert back.read(i) == old.read(old_at[(back.chunk_id64(i), back.chunk_type(i))]), back.files.get(i)
        same += 1
    files = {}
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        files[ext] = (os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    return dict(changed=len(report), unchanged=same, counts=counts, files=files, sample=report[:8])


if __name__ == '__main__':
    print(main(*sys.argv[1:]))
