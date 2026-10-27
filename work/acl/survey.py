import sys, glob, os, json
sys.path.insert(0, '/work/acl')
import numpy as np, pose
I = pose.IDX
rows = []
for fn in sorted(glob.glob('/work/fly1014/pkgs/*.bin')):
    name = os.path.basename(fn)[:-4]
    d = open(fn, 'rb').read()
    try:
        c, bones, LQ, LT = pose.load(d)
    except Exception as ex:
        print(name, 'FAIL', ex); continue
    GQ, GT = pose.component(LQ, LT)
    S = c.num_samples
    root = GT[:, I['Trans']]; hip = GT[:, I['C_Hip_a']]; neck = GT[:, I['C_Neck_a']]; head = GT[:, I['C_Head_a']]; nose = GT[:, I['C_Nose_A']]
    feet = np.minimum(GT[:, I['L_Foot_a'], 2], GT[:, I['R_Foot_a'], 2])
    spine = neck - hip
    tilt = np.degrees(np.arctan2(np.hypot(spine[:, 0], spine[:, 1]), spine[:, 2]))  # 0 upright, 90 horizontal
    travel = np.linalg.norm(np.diff(hip, axis=0), axis=1).sum()
    disp = hip[-1] - hip[0]
    speed = travel / max(1e-6, (S - 1) / c.sample_rate)
    # wing: feather bones' motion (if animated)
    wing = [b for b in bones if 'Feather' in pose.NAMES[b] or 'Wing' in pose.NAMES[b]]
    flap = 0.0
    if wing:
        w = GT[:, wing] - hip[:, None]
        flap = float(np.mean(np.std(w, axis=0)))
    # height of the hips above the feet: legs dangling vs standing
    hip_over_feet = float(np.mean(hip[:, 2] - feet))
    rows.append(dict(name=name, sec=round((S - 1) / c.sample_rate, 2), travel=round(float(travel)), speed=round(float(speed)),
                     dz=round(float(disp[2])), dxy=round(float(np.hypot(disp[0], disp[1]))), tilt=round(float(np.mean(tilt))),
                     tilt_rng=round(float(np.ptp(tilt))), hipfeet=round(hip_over_feet), wings=len(wing), flap=round(flap, 1),
                     zmin=round(float(hip[:, 2].min() - hip[0, 2])), zmax=round(float(hip[:, 2].max() - hip[0, 2]))))
    r = rows[-1]
    print('%-32s %5.1fs travel %6d speed %5d dz %+6d dxy %6d tilt %3d (%3d) hip-feet %4d wings %2d flap %5.1f' % (
        r['name'], r['sec'], r['travel'], r['speed'], r['dz'], r['dxy'], r['tilt'], r['tilt_rng'], r['hipfeet'], r['wings'], r['flap']), flush=True)
json.dump(rows, open('/work/fly1014/survey.json', 'w'), indent=1)
