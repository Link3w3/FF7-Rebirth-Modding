"""Cloud's additive clips (local space, base = a frame of another clip) onto Sora: the clip's deltas (UE's
ConvertPoseToAdditive: rotation target * inverse(base), translation target - base) put back on the base clip's frame,
that absolute pose retargeted like any clip, written as a .cacanim; the editor then makes the import additive again on
Sora's own base clip (same name, same frame), so the engine takes the delta from Sora's poses.
    retarget_additive.py <pkgs dir> <additive json (cloud_additive_other.json)> <out dir>"""
import json, os, sys
import numpy as np
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/acl']
import retarget as R
import acl13


def pkg_file(pkgs, path):
    return os.path.join(pkgs, path.replace('/Game/', '').replace('/', '__') + '.uasset')


def decode_delta(data):
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = R.track_map(data, c.num_bones)
    S = c.num_samples
    n = len(R.CLOUD.names)
    dQ = np.zeros((S, n, 4)); dQ[..., 3] = 1.0
    dT = np.zeros((S, n, 3))
    for k, b in enumerate(bones):
        dQ[:, b] = rot[:, k]
        dT[:, b] = trans[:, k]
    return c.sample_rate, S, R.qnorm(dQ), dT, c.default_scale


def main(pkgs, js, out):
    add = json.load(open(js))['additive']
    report = {}
    for clip, atype, btype, base, frame in add:
        assert 'LOCAL_SPACE_BASE' in atype and 'ANIM_FRAME' in btype, (clip, atype, btype)
        fps, S, dQ, dT, ds = decode_delta(open(pkg_file(pkgs, clip), 'rb').read())
        assert ds == 0, clip
        bfps, bS, LQb, LTb = R.decode(open(pkg_file(pkgs, base), 'rb').read())
        f = min(int(frame), bS - 1)
        LQ = R.qnorm(R.qmul(dQ, LQb[f][None]))
        LT = dT + LTb[f][None]
        LQs, LTs, LSs, GT = R.retarget(LQ, LT)
        parts = clip.split('/')   # /Game/Motion/<Player|Level|FieldAction>/...
        if parts[3] == 'Player':
            rel = os.path.join(parts[5], parts[6])          # <set>/<clip>
        else:
            rel = os.path.join(parts[3], parts[4], parts[6])  # <kind>/<set>/<clip>
        path = os.path.join(out, rel + '.cacanim')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        n = R.write_cacanim(path, fps, LQs, LTs, LSs, False)
        # how far the deltas move things (degrees of the largest bone delta), a sanity number
        ang = float(np.degrees(2 * np.arccos(np.clip(np.abs(dQ[..., 3]), 0, 1))).max())
        report[clip] = dict(base=base, frame=f, frames=S, tracks=n, max_delta_deg=round(ang, 1), out=rel)
    json.dump(report, open(os.path.join(out, 'report_additive.json'), 'w'), indent=1)
    return report


if __name__ == '__main__':
    r = main(*sys.argv[1:4])
    for k, v in r.items():
        print(k.split('/Motion/')[1], v['frames'], v['max_delta_deg'], v['out'])
