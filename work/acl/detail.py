import sys
sys.path.insert(0, '/work/acl')
import numpy as np, pose
I = pose.IDX
def analyze(name, step=6):
    d = open('/work/fly1014/pkgs/%s.bin' % name, 'rb').read()
    c, bones, LQ, LT = pose.load(d)
    LQ[:, 0] = [0, 0, 0, 1]
    GQ, GT = pose.component(LQ, LT)
    hip, neck, head, nose = (GT[:, I[n]] for n in ('C_Hip_a', 'C_Neck_a', 'C_Head_a', 'C_Nose_A'))
    sp = neck - hip
    tilt = np.degrees(np.arctan2(np.hypot(sp[:, 0], sp[:, 1]), sp[:, 2]))
    lean = np.degrees(np.arctan2(sp[:, 1], sp[:, 0]))
    face = np.degrees(np.arctan2((nose - head)[:, 1], (nose - head)[:, 0]))
    vel = np.gradient(hip, axis=0) * c.sample_rate
    spd = np.linalg.norm(vel, axis=1)
    travel_yaw = np.degrees(np.arctan2(vel[:, 1], vel[:, 0]))
    climb = np.degrees(np.arctan2(vel[:, 2], np.hypot(vel[:, 0], vel[:, 1])))
    wing = [b for b in bones if 'Feather' in pose.NAMES[b] or 'Wing' in pose.NAMES[b]]
    print('%s  %d samples %.1fs  wing tracks %d' % (name, c.num_samples, (c.num_samples - 1) / c.sample_rate, len(wing)))
    for f in range(0, c.num_samples, step):
        print('   f%3d speed %5d climb %+4d travel-yaw %+5d face %+5d tilt %3d lean-dir %+5d  hipZ %7.0f' % (f, spd[f], climb[f], travel_yaw[f], face[f], tilt[f], lean[f], hip[f, 2]))
for n in sys.argv[1:]:
    analyze(n)
