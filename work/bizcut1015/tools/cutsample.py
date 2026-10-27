"""Samples the cut: per shot, the camera's world transform and FOV, and the characters' actor transforms."""
import math, sys
sys.path[:0] = ['/work/bizcut1015/tools', '/work/cs']
from cutread import Seq, PK, guid_str, eval_channel

PRE = PK + 'Cut__Game__8800-FOREE__EV_FOREE_8630__EV_FOREE_8630_'


def rot_matrix(roll, pitch, yaw):
    """UE FRotator -> rotation matrix (columns X forward, Y right, Z up), degrees."""
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    # FRotationMatrix (UE4): rows are the axes
    X = (cp * cy, cp * sy, sp)
    Y = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    Z = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return X, Y, Z


def to_rotator(X, Y, Z):
    """Axes -> (roll, pitch, yaw) degrees (FMatrix::Rotator)."""
    pitch = math.degrees(math.atan2(X[2], math.sqrt(X[0] ** 2 + X[1] ** 2)))
    yaw = math.degrees(math.atan2(X[1], X[0]))
    # roll from Y axis
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    # Y axis with roll 0:
    y0 = (-sy, cy, 0.0)
    z0 = (-sp * cy, -sp * sy, cp)
    roll = math.degrees(math.atan2(-(Y[0] * z0[0] + Y[1] * z0[1] + Y[2] * z0[2]), Y[0] * y0[0] + Y[1] * y0[1] + Y[2] * y0[2]))
    return roll, pitch, yaw


class Xf:
    def __init__(self, t=(0, 0, 0), r=(0, 0, 0), s=(1, 1, 1)):
        self.t = tuple(t)
        self.r = tuple(r)   # roll, pitch, yaw
        self.s = tuple(s)
        self.axes = rot_matrix(*self.r)

    def apply(self, p):
        """Local point -> world."""
        X, Y, Z = self.axes
        x, y, z = p[0] * self.s[0], p[1] * self.s[1], p[2] * self.s[2]
        return tuple(self.t[k] + X[k] * x + Y[k] * y + Z[k] * z for k in range(3))

    def inverse_apply(self, p):
        X, Y, Z = self.axes
        d = [p[k] - self.t[k] for k in range(3)]
        return (sum(d[k] * X[k] for k in range(3)) / self.s[0], sum(d[k] * Y[k] for k in range(3)) / self.s[1],
                sum(d[k] * Z[k] for k in range(3)) / self.s[2])

    def compose(self, child):
        """World of a child transform given relative to self (scale ignored for rotation)."""
        t = self.apply(child.t)
        X, Y, Z = self.axes
        cX, cY, cZ = child.axes

        def rot(v):
            return tuple(X[k] * v[0] + Y[k] * v[1] + Z[k] * v[2] for k in range(3))
        out = Xf(t, (0, 0, 0), tuple(self.s[k] * child.s[k] for k in range(3)))
        nX, nY, nZ = rot(cX), rot(cY), rot(cZ)
        out.r = to_rotator(nX, nY, nZ)
        out.axes = (nX, nY, nZ)
        return out

    def relative(self, world):
        """world (an Xf) expressed in self's space (rotation relative too); scale divided."""
        t = self.inverse_apply(world.t)
        X, Y, Z = self.axes

        def loc(v):
            return (sum(v[k] * X[k] for k in range(3)), sum(v[k] * Y[k] for k in range(3)), sum(v[k] * Z[k] for k in range(3)))
        wX, wY, wZ = world.axes
        out = Xf(t)
        out.axes = (loc(wX), loc(wY), loc(wZ))
        out.r = to_rotator(*out.axes)
        return out


def section_xf(seq, sec, tick):
    def ch(name, default):
        c = sec.get(name)
        if not isinstance(c, dict):
            return default
        v = eval_channel(c, tick, seq.tick_rate)
        return default if v is None else v
    t = tuple(ch('Translation[%d]' % k, 0.0) for k in range(3))
    r = tuple(ch('Rotation[%d]' % k, 0.0) for k in range(3))
    s = tuple(ch('Scale[%d]' % k, 1.0) for k in range(3))
    return Xf(t, r, s)


def track_xf(seq, tracks, tick):
    for tr in tracks:
        if seq.kind(tr) != 'MovieScene3DTransformTrack':
            continue
        for k, sec in seq.track_sections(tr):
            lo, hi = seq.range_of(sec)
            if (lo is None or tick >= lo) and (hi is None or tick < hi or hi == lo):
                return section_xf(seq, sec, tick)
        secs = seq.track_sections(tr)
        if secs:
            return section_xf(seq, secs[0][1], tick)
    return None


def track_float(seq, tracks, prop, tick):
    for tr in tracks:
        if seq.kind(tr) == 'MovieSceneFloatTrack' and seq.track_name(tr) == prop:
            for k, sec in seq.track_sections(tr):
                c = sec.get('FloatCurve')
                if isinstance(c, dict):
                    return eval_channel(c, tick, seq.tick_rate)
    return None


class Cut:
    def __init__(self):
        self.cam = Seq(PRE + 'Camera.uasset')
        self.chars = Seq(PRE + 'Character.uasset')
        pos = self.cam.possessables()
        self.cam_bind = {g: t for g, n, t in self.cam.bindings()}
        self.cam_pos = pos
        # camera actor guid -> (component guid, end component guid)
        self.children = {}
        for g, p in pos.items():
            if p['parent']:
                self.children.setdefault(p['parent'], {})[p['name']] = g
        self.shots = []
        for k, sec in self.cam.track_sections(self.cam.movie['CameraCutTrack']):
            lo, hi = self.cam.range_of(sec)
            g = guid_str((sec.get('CameraBindingID') or {}).get('Guid'))
            self.shots.append(dict(name=pos[g]['name'].split('_')[-1], lo=lo, hi=hi, cam=g))
        cpos = self.chars.possessables()
        self.char_tracks = {cpos[g]['name'].replace('EV_FOREE_8630_', ''): t for g, n, t in self.chars.bindings()}

    def camera(self, shot, tick):
        g = shot['cam']
        actor = track_xf(self.cam, self.cam_bind.get(g, []), tick) or Xf()
        kids = self.children.get(g, {})
        comp_g = kids.get('Camera Component')
        end_g = kids.get('End Camera Component')
        comp = track_xf(self.cam, self.cam_bind.get(comp_g, []), tick) if comp_g else None
        world = actor.compose(comp) if comp else actor
        fov = track_float(self.cam, self.cam_bind.get(comp_g, []), 'FieldOfView', tick) if comp_g else None
        focal = track_float(self.cam, self.cam_bind.get(end_g, []), 'FocalLength', tick) if end_g else None
        film = track_float(self.cam, self.cam_bind.get(end_g, []), 'FilmWidth', tick) if end_g else None
        roll = track_float(self.cam, self.cam_bind.get(end_g, []), 'Roll', tick) if end_g else None
        focus = track_float(self.cam, self.cam_bind.get(end_g, []), 'FocusDistance', tick) if end_g else None
        return dict(world=world, actor=actor, comp=comp, fov=fov, focal=focal, film=film, roll=roll, focus=focus)

    def char(self, name, tick):
        return track_xf(self.chars, self.char_tracks.get(name, []), tick)

    def visible(self, name, tick):
        for tr in self.char_tracks.get(name, []):
            for k, sec in self.chars.track_sections(tr):
                bc = sec.get('BoolCurve')
                if isinstance(bc, dict) and bc.get('Times'):
                    import bisect
                    i = bisect.bisect_right(bc['Times'], tick) - 1
                    return bc['Values'][i] if i >= 0 else bc.get('DefaultValue')
        return None
