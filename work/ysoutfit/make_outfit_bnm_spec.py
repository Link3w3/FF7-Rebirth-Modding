"""The Young Sephiroth outfit's own Bonamik (PC0010_10 on PC0010_10_Skeleton = Sephiroth's skeleton + CH049_001's 103
physics bones, the model CH049_001 scaled up to Sephiroth's height): CH049_001's Bonamik (ch049_bnm_spec.json) with
  * its colliders on Sephiroth's bones (hip -> C_Hip_a, spine3 -> C_Spine_c, spine4 -> C_Spine_d, neck -> C_Neck_a,
    head -> C_Head_a, left/right upleg, leg, foot, toe -> L/R_UpperLeg_a, Foreleg_a, Foot_a, Toe_a): the colliders sit on
    their bones (no offsets), so they keep their place;
  * every length (radii, offsets) times the outfit's scale (its physics bones are CH049's x 1.172);
  * the coat, hair, collar and shoulder chains on the same physics bones (their names are the outfit's).
    make_outfit_bnm_spec.py <ch049 spec> <outfit_bones.json> <out spec>"""
import json, sys
import numpy as np

RENAME = {'hip': 'C_Hip_a', 'spine3': 'C_Spine_c', 'spine4': 'C_Spine_d', 'neck': 'C_Neck_a', 'head': 'C_Head_a'}
for s, u in (('L', 'left'), ('R', 'right')):
    RENAME.update({u + '_upleg': s + '_UpperLeg_a', u + '_leg': s + '_Foreleg_a', u + '_foot': s + '_Foot_a', u + '_toe': s + '_Toe_a'})
LENGTH_KEYS = ('m_Radius',)
VECTOR_KEYS = ('m_LocalTransform', 'mOuterOffset', 'mInnerOffset')


def main(src, bones_path, out):
    spec = json.load(open(src))
    bones = {b[0] for b in json.load(open(bones_path))['user']}
    scale = 1.172
    renamed = 0
    for b in spec['mBodies']:
        p = b['mParentName']
        if p in RENAME:
            b['mParentName'] = RENAME[p]
            b['mName'] = b['mName'].replace('_' + p + '_', '_' + RENAME[p] + '_')
            renamed += 1
        assert b['mParentName'] in bones, b['mParentName']
        for k in LENGTH_KEYS:
            if k in b:
                b[k] = round(b[k] * scale, 4)
        for k in VECTOR_KEYS:
            if k in b:
                b[k] = [round(v * scale, 4) for v in b[k]]
    # body names may have changed: the shapes, links and cones name bodies
    names = {}
    for b in spec['mBodies']:
        pass
    old_to_new = {}
    spec2 = json.load(open(src))
    for old, new in zip(spec2['mBodies'], spec['mBodies']):
        old_to_new[old['mName']] = new['mName']
    for key in ('mShapes',):
        for s in spec[key]:
            s['mBodies'] = [old_to_new.get(n, n) for n in s['mBodies']]
    for key in ('mLinks', 'mCones'):
        for l in spec[key]:
            for f in list(l.keys()):
                if isinstance(l[f], str) and l[f] in old_to_new:
                    l[f] = old_to_new[l[f]]
            for k in VECTOR_KEYS:
                if k in l:
                    l[k] = [round(v * scale, 4) for v in l[k]]
    names = {b['mName'] for b in spec['mBodies']}
    assert len(names) == len(spec['mBodies'])
    for s in spec['mShapes']:
        assert all(n in names for n in s['mBodies']), s
    for key in ('mLinks', 'mCones'):
        for l in spec[key]:
            for f, v in l.items():
                if isinstance(v, str) and v.startswith('Bdy_'):
                    assert v in names, (key, f, v)
    json.dump(spec, open(out, 'w'), indent=1)
    print('%d bodies (%d colliders moved onto Sephiroth\'s bones), %d links, %d cones, %d shapes; lengths x%.3f' % (
        len(spec['mBodies']), renamed, len(spec['mLinks']), len(spec['mCones']), len(spec['mShapes']), scale))


if __name__ == '__main__':
    main(*sys.argv[1:4])
