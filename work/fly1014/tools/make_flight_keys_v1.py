"""Sephiroth's flying form (pack Battle03): his locomotion made from the flight in the game's final cutscenes, as key
animations (.cacanim) for Create a Character System's Import Key Animations, plus the manifest the editor build reads.
    make_flight_keys.py <out folder> <cutscene motions folder> <his Battle00 locomotion folder (.uasset/.uexp)>

Two loops come from the cutscenes (winged Sephiroth, on his own skeleton PC0010_00):
  hover:  EV_FOREE_8710 C0120, hovering with every feather of the wing moving (frames 4-77 loop)
  flight: EV_FOREE_8790 C0080, flying off at full speed, leaning into it (frames 110-140 loop); its wing moves as the
          hover's (the cutscene animates only the wing's root there)
Each locomotion key the game plays (idle, run, its starts, stops and turns, the walks) gets the body of one of them (or a
blend from one to the other) on the root motion of the game's own animation of that key: the same timing, distance and
turns, so the game's locomotion runs it as it runs his own. His body is turned to face forward, held up off the ground
(HOVER_LIFT) and kept level (the cutscene's climb and travel are taken out)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import aclclip
from aclclip import Clip, SK_INDEX, SK_NAMES, REF_T, REF_Q, qmul, qnorm, qslerp, q_axis_angle, qrot, qconj

IMPORT_FOLDER = '/Game/RebirthSkelCompat/Imported/SephirothFlight'
PACK = 'Battle03'
OWN = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
HOVER_LIFT = 45.0       # cm his hips are held above standing height (his feet off the ground)
FLIGHT_PITCH = 18.0     # degrees more lean into the flight than the cutscene (it climbs; his flight is level)
HOVER_SRC = ('EV_FOREE_8710_PC0010_10_C0120', 4, 77, 15)     # (clip, first frame, last frame, frames blended at the wrap)
FLIGHT_SRC = ('EV_FOREE_8790_PC0010_10_C0080', 110, 140, 6)

# key -> body: 'hover', 'flight', 'takeoff' (hover into flight), 'stop' (flight into hover)
KEYS = {
    'B_Idle01_0': 'hover', 'B_Idle01_1': 'hover', 'B_Idle01_2': 'hover',
    'B_Fall01_1': 'hover', 'B_Fall01_2': 'hover',
    'B_Run01_1': 'flight', 'B_Run01_1_L180': 'flight', 'B_Run01_1_R180': 'flight',
    'B_Run01_0_L0': 'takeoff', 'B_Run01_0_L90': 'takeoff', 'B_Run01_0_L180': 'takeoff', 'B_Run01_0_R180': 'takeoff',
    'B_Run01_2l': 'stop', 'B_Run01_2r': 'stop',
    'B_Turn01_L0': 'hover', 'B_Turn01_R0': 'hover', 'B_Turn01_L90': 'hover', 'B_Turn01_R90': 'hover',
    'B_Turn01_L180': 'hover', 'B_Turn01_R180': 'hover',
    'B_Walk01_0_L0': 'hover', 'B_Walk01_0_L90': 'hover', 'B_Walk01_0_R90': 'hover', 'B_Walk01_0_L180': 'hover', 'B_Walk01_0_R180': 'hover',
    'B_Walk01_1': 'hover', 'B_Walk01_2l': 'hover', 'B_Walk01_2r': 'hover',
    'B_WalkB01_0': 'hover', 'B_WalkB01_1': 'hover', 'B_WalkB01_2l': 'hover', 'B_WalkB01_2r': 'hover',
    'B_WalkL01_0': 'hover', 'B_WalkL01_1': 'hover', 'B_WalkL01_2l': 'hover', 'B_WalkL01_2r': 'hover',
    'B_WalkR01_0': 'hover', 'B_WalkR01_1': 'hover', 'B_WalkR01_2l': 'hover', 'B_WalkR01_2r': 'hover',
    'B_WalkFL01_1': 'hover', 'B_WalkFR01_1': 'hover', 'B_WalkBL01_1': 'hover', 'B_WalkBR01_1': 'hover',
}
LOOPS = {'B_Idle01_1', 'B_Run01_1', 'B_Fall01_1', 'B_Walk01_1', 'B_WalkB01_1', 'B_WalkL01_1', 'B_WalkR01_1',
         'B_WalkFL01_1', 'B_WalkFR01_1', 'B_WalkBL01_1', 'B_WalkBR01_1'}


def yaw_q(deg):
    deg = np.atleast_1d(np.asarray(deg, dtype=np.float64))
    h = np.radians(deg) / 2
    return np.stack([np.zeros_like(h), np.zeros_like(h), np.sin(h), np.cos(h)], -1)


def facing(c):
    """His mean facing (degrees) over the clip, from his nose, with the root unrotated."""
    w = c.world(['C_Head_a', 'C_Nose_A'])
    v = w['C_Nose_A'][0] - w['C_Head_a'][0]
    return float(np.degrees(np.arctan2(np.mean(np.sin(np.arctan2(v[:, 1], v[:, 0]))), np.mean(np.cos(np.arctan2(v[:, 1], v[:, 0]))))))


def body_loop(src_dir, src, pitch=0.0):
    """A body loop from a cutscene clip: the root unrotated and still, the hips at standing height (+ lift, + the
    cutscene's own bob), turned to face +X, pitched forward by `pitch`, the wrap blended."""
    name, a, b, LOOP_BLEND = src
    c = aclclip.from_game(open(os.path.join(src_dir, name + '.bin'), 'rb').read(), name)
    jt, jh = c.index['Trans'], c.index['C_Hip_a']
    hipz = c.T[:, jt, 2].copy()                     # (the hips ride the root in the cutscenes)
    c.Q[:, jt] = (0.0, 0.0, 0.0, 1.0)
    c.T[:, jt] = 0.0
    c = c.frames_range(a, b + LOOP_BLEND + 1)
    # his own bob while hovering (none in the flight: it climbs), at most 12 cm either way
    bob = np.clip(hipz[a:b + LOOP_BLEND + 1] - hipz[a:b + 1].mean(), -12.0, 12.0) * (0.0 if pitch else 1.0)
    c.T[:, jh] = REF_T[SK_INDEX['C_Hip_a']] + np.stack([np.zeros_like(bob), np.zeros_like(bob), bob + HOVER_LIFT], -1)
    turn = -facing(c)
    c.Q[:, jh] = qnorm(qmul(yaw_q(np.full(c.frames, turn)), c.Q[:, jh]))
    if pitch:
        # lean forward: about his lateral axis (component Y, facing +X), at the hips
        h = np.radians(pitch) / 2
        qp = np.array([0.0, np.sin(h), 0.0, np.cos(h)])
        c.Q[:, jh] = qnorm(qmul(np.broadcast_to(qp, c.Q[:, jh].shape), c.Q[:, jh]))
    # loop: the last LOOP_BLEND frames blend into the first ones, which are then dropped
    n = c.frames
    k = LOOP_BLEND
    out_T, out_Q, out_S = c.T[k:].copy(), c.Q[k:].copy(), c.S[k:].copy()
    m = n - k
    for j in range(m - k, m):
        t = (j - (m - k) + 1) / (k + 1)
        src_j = j - (m - k)
        out_Q[j] = qslerp(out_Q[j], c.Q[src_j], t)
        out_T[j] = out_T[j] * (1 - t) + c.T[src_j] * t
    c.T, c.Q, c.S = out_T, out_Q, out_S
    c.facing_turn = turn
    return c


def sample_loop(loop, times):
    """The loop's pose at these times (seconds, wrapping), per bone (T, Q)."""
    f = (np.asarray(times) * loop.fps) % loop.frames
    i0 = np.floor(f).astype(int) % loop.frames
    i1 = (i0 + 1) % loop.frames
    t = f - np.floor(f)
    T = loop.T[i0] * (1 - t)[:, None, None] + loop.T[i1] * t[:, None, None]
    Q = qslerp(loop.Q[i0], loop.Q[i1], np.repeat(t[:, None], len(loop.bones), 1))
    return T, Q


def game_root(loco_dir, key):
    """The game's own animation of `key`: (frames, fps, root translation (F,3) from its start, root yaw (F,) degrees)."""
    path = os.path.join(loco_dir, key)
    data = open(path + '.uasset', 'rb').read() + open(path + '.uexp', 'rb').read()
    g = aclclip.from_game(data, key)
    jt = g.index['Trans']
    q = g.Q[:, jt]
    up = qrot(q, np.broadcast_to(np.array([0.0, 0.0, 1.0]), q.shape[:-1] + (3,)))   # (the root's own forward, see pose.py)
    yaw = np.degrees(np.unwrap(np.arctan2(up[:, 1], up[:, 0])))
    yaw = yaw - yaw[0]
    return g.frames, g.fps, g.T[:, jt] - g.T[0, jt], yaw


def make_key(key, kind, hover, flight, loco_dir):
    frames, fps, root_t, root_yaw = game_root(loco_dir, key)
    if key in LOOPS:
        # a loop: as long as its body loop, moving at the game's speed for the key
        body = flight if kind == 'flight' else hover
        n = body.frames + 1
        secs = (frames - 1) / fps
        vel = (root_t[-1] - root_t[0]) / max(secs, 1e-6)
        t = np.arange(n) / body.fps
        root_t = t[:, None] * vel[None]
        root_yaw = np.zeros(n)
        fps_out = body.fps
    else:
        n = frames
        t = np.arange(n) / fps
        fps_out = fps
    bones = hover.bones
    assert flight.bones == bones
    if kind in ('hover', 'flight'):
        T, Q = sample_loop(hover if kind == 'hover' else flight, t)
    else:
        Th, Qh = sample_loop(hover, t)
        Tf, Qf = sample_loop(flight, t)
        w = np.clip(t / max(t[-1], 1e-6), 0, 1)
        w = w * w * (3 - 2 * w)                      # smoothstep
        if kind == 'stop':
            w = 1.0 - w
        T = Th * (1 - w)[:, None, None] + Tf * w[:, None, None]
        Q = qslerp(Qh, Qf, np.repeat(w[:, None], len(bones), 1))
    T = T.copy(); Q = Q.copy()
    jt = bones.index('Trans')
    T[:, jt] = root_t
    Q[:, jt] = yaw_q(root_yaw)
    c = Clip(bones, T, Q, np.ones_like(T), fps_out, 'FLY_' + key)
    return c


def main(out, cut_dir, loco_dir):
    os.makedirs(out, exist_ok=True)
    hover = body_loop(cut_dir, HOVER_SRC)
    flight = body_loop(cut_dir, FLIGHT_SRC, pitch=FLIGHT_PITCH)
    # one bone list for both (bones only one has: its reference pose)
    bones = sorted(set(hover.bones) | set(flight.bones), key=lambda n: SK_INDEX[n])
    hover_T, hover_Q = None, None
    for c in (hover, flight):
        T = np.repeat(REF_T[[SK_INDEX[n] for n in bones]][None], c.frames, 0).astype(np.float64)
        Q = np.repeat(REF_Q[[SK_INDEX[n] for n in bones]][None], c.frames, 0).astype(np.float64)
        if c is flight:
            # bones the flight does not move (the wing's feathers): as in the hover at the same time
            hover_T, hover_Q = sample_loop(hover, np.arange(c.frames) / c.fps)
        for j, n in enumerate(bones):
            if n in c.index:
                T[:, j] = c.T[:, c.index[n]]; Q[:, j] = c.Q[:, c.index[n]]
            elif c is flight:
                T[:, j] = hover_T[:, j]; Q[:, j] = hover_Q[:, j]
        c.bones, c.T, c.Q, c.S = bones, T, Q, np.ones_like(T)
        c.index = {b: i for i, b in enumerate(bones)}
    manifest = {'import_folder': IMPORT_FOLDER, 'skeleton': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton',
                'fps': 30, 'moves': [], 'sources': {'hover': list(HOVER_SRC[:3]), 'flight': list(FLIGHT_SRC[:3])},
                'turns': {'hover': round(hover.facing_turn, 1), 'flight': round(flight.facing_turn, 1)}}
    for key, kind in KEYS.items():
        c = make_key(key, kind, hover, flight, loco_dir)
        path = os.path.join(out, c.name + '.cacanim')
        tracks = c.write(path, loop=key in LOOPS)
        root = c.T[:, c.index['Trans']]
        manifest['moves'].append(dict(set=PACK, name=key, animation='%s/%s.%s' % (IMPORT_FOLDER, c.name, c.name), build=True,
                                      notifies_from=OWN + '%s.%s' % (key, key), hits=[], seconds=round(c.seconds, 3), frames=c.frames,
                                      body=kind, root_travel=[round(float(v), 1) for v in (root[-1] - root[0])], tracks=tracks))
        print('%-15s %-8s %3d frames %5.2fs  root %+6.0f %+6.0f  %3d tracks' % (key, kind, c.frames, c.seconds, *manifest['moves'][-1]['root_travel'][:2], tracks))
    json.dump(manifest, open(os.path.join(out, 'flight_moves.json'), 'w'), indent=1)
    return hover, flight


if __name__ == '__main__':
    main(*sys.argv[1:4])
