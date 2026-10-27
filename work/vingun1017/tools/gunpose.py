"""What Vincent does with his gun in each cutscene motion: per frame his right arm against his body (aiming, gun raised,
lowered), its pointing, two hands, crouch/prone, walking; runs of the same pose.  gunpose.py <cuts.json> <pkgs> <out json>"""
import sys, os, json
sys.path.append('/work/vingun1017/tools')
import numpy as np
import vpose

CUTS = json.load(open(sys.argv[1]))
PK = sys.argv[2]
I = vpose.IDX
IN_HAND = {'EV_FOREE_0630': [(312, 9999)], 'EV_GONGE_6010': [(2037, 2273)], 'EV_NIBLE_2740': [(4088, 6064)], 'EV_NIBLE_8310': [(189, 1582)]}
MUZZLE = {'EV_FOREE_0630': [320], 'EV_GONGE_6010': [2097, 2105, 2109, 2118]}


def unit(v):
    return v / np.maximum(1e-6, np.linalg.norm(v, axis=-1, keepdims=True))


def analyse(path):
    c, bones, LQ, LT = vpose.load(open(path, 'rb').read())
    GQ, GT = vpose.component(LQ, LT)
    # (the cut's motions turn their root bone into the cut's own frame: positions in the root's frame are the body's,
    # upright, with Z up)
    tq = GQ[:, I['Trans']] * np.array([-1.0, -1.0, -1.0, 1.0])
    tt = GT[:, I['Trans']]
    GT = vpose.qrot(np.repeat(tq[:, None], GT.shape[1], 1), GT - tt[:, None])
    P = lambda n: GT[:, I[n]]
    hip, neck = P('C_Hip_a'), P('C_Neck_a')
    up = unit(neck - hip)
    right = P('R_UpperArm_a') - P('L_UpperArm_a')
    right = unit(right - (right * up).sum(-1, keepdims=True) * up)
    fwd = np.cross(right, up)
    sh, el, ha, we = P('R_UpperArm_a'), P('R_Forearm_a'), P('R_Hand_a'), P('R_Weapon_a')
    arm = np.linalg.norm(vpose.REF_T[I['R_Forearm_a']]) + np.linalg.norm(vpose.REF_T[I['R_Hand_a']])
    rel = ha - sh
    f, r, u = (rel * fwd).sum(-1), (rel * right).sum(-1), (rel * up).sum(-1)
    ext = np.linalg.norm(rel, axis=-1) / arm
    point = unit(we - el)
    pitch = np.degrees(np.arcsin(np.clip((point * up).sum(-1), -1, 1)))
    yaw = np.degrees(np.arctan2((point * right).sum(-1), (point * fwd).sum(-1)))
    two = np.linalg.norm(P('L_Hand_a') - ha, axis=-1)
    feet = np.minimum(P('L_Foot_a')[:, 2], P('R_Foot_a')[:, 2])
    hip_h = hip[:, 2] - feet
    torso_tilt = np.degrees(np.arccos(np.clip(up[:, 2], -1, 1)))
    speed = np.r_[0, np.linalg.norm(np.diff(hip[:, :2], axis=0), axis=1)] * c.sample_rate
    turn = np.r_[0, np.degrees(np.arccos(np.clip((point[1:] * point[:-1]).sum(-1), -1, 1)))] * c.sample_rate
    labels = []
    for k in range(c.num_samples):
        if torso_tilt[k] > 60:
            body = 'prone'
        elif hip_h[k] < 60:
            body = 'crouch'
        else:
            body = 'walk' if speed[k] > 60 else 'stand'
        if turn[k] > 500:
            g = 'spin'
        elif ext[k] > 0.82 and -35 <= pitch[k] <= 35 and f[k] > 22:
            g = 'aim'
        elif pitch[k] > 40 and u[k] > -10:
            g = 'raised'
        elif u[k] < -38:
            g = 'lowered'
        else:
            g = 'held'
        if two[k] < 14:
            g += '+2hands'
        labels.append((body, g))
    runs = []
    for k, lab in enumerate(labels):
        if runs and runs[-1]['pose'] == lab:
            runs[-1]['to'] = k
        else:
            runs.append({'pose': lab, 'from': k, 'to': k})
    # tiny runs (under 3 frames) fold into the one before
    out = []
    for run in runs:
        if out and run['to'] - run['from'] < 2:
            out[-1]['to'] = run['to']
        else:
            out.append(run)
    frames = [dict(k=k, ext=round(float(ext[k]), 2), fwd=round(float(f[k])), up=round(float(u[k])), side=round(float(r[k])), pitch=round(float(pitch[k])),
                   yaw=round(float(yaw[k])), two=round(float(two[k])), hip=round(float(hip_h[k])), tilt=round(float(torso_tilt[k])), speed=round(float(speed[k])))
              for k in range(c.num_samples)]
    return dict(samples=c.num_samples, rate=c.sample_rate, runs=[dict(body=x['pose'][0], gun=x['pose'][1], frm=x['from'], to=x['to']) for x in out], frames=frames)


report = {}
for ev, spans in IN_HAND.items():
    for s in sorted(CUTS[ev]['vincent'], key=lambda x: x['from']):
        inside = any(s['to'] > a and s['from'] < b for a, b in spans)
        if not inside:
            continue
        name = s['anim']
        path = [os.path.join(PK, f) for f in os.listdir(PK) if f.endswith('__' + name + '.uasset')]
        if not path:
            print('missing', name); continue
        a = analyse(path[0])
        a['cut'] = ev
        a['section'] = [s['from'], s['to']]
        a['shots'] = [m - s['from'] for m in MUZZLE.get(ev, []) if s['from'] <= m < s['to']]
        report[name] = a
        summary = ', '.join('%s/%s %d-%d' % (x['body'], x['gun'], x['frm'], x['to']) for x in a['runs'])
        print('%-34s %4d fr %s%s' % (name, a['samples'], summary[:260], ('  SHOTS at ' + str(a['shots'])) if a['shots'] else ''), flush=True)
json.dump(report, open(sys.argv[3], 'w'), indent=1)
