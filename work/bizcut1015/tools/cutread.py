"""Reads a cut's LevelSequence packages (EndCinemaSequence) into plain data: bindings, tracks, sections, channels."""
import sys
sys.path[:0] = ['/work/bizcut1015/tools', '/work/cs']
from zen import Zen
import scriptobjs, unv

PK = '/work/bizcut1015/plan1/pkgs/'


def guid_str(g):
    return '%08X-%08X-%08X-%08X' % tuple(g) if g else None


class Seq:
    def __init__(self, path):
        self.path = path
        self.z = Zen(open(path, 'rb').read())
        self.objs = {}
        self.cls = {}
        self.errors = {}
        for i, e in enumerate(self.z.exports):
            cls = scriptobjs.name_of(e['cls'])
            self.cls[i] = cls
            short = cls.split('.')[-1]
            try:
                obj, rest = unv.export_object(self.z, i, 'U' + short)
                obj['__name__'] = e['name']
                obj['__outer__'] = e['outer']
                self.objs[i] = obj
            except Exception as ex:
                self.errors[i] = str(ex)
        self.movie = next((o for i, o in self.objs.items() if self.cls[i].endswith('.MovieScene')), None)
        self.sequence = next((o for i, o in self.objs.items() if self.cls[i].endswith('Sequence')), None)
        m = self.movie
        self.tick = m.get('TickResolution', {}) if m else {}
        self.tick_rate = (self.tick.get('Numerator', 60000) / float(self.tick.get('Denominator', 1))) if self.tick else 60000.0
        self.display = m.get('DisplayRate', {}) if m else {}

    def obj(self, ref):
        if ref and ref[0] == 'export':
            return self.objs.get(ref[1])
        return None

    def kind(self, ref):
        if ref and ref[0] == 'export':
            return self.cls.get(ref[1], '').split('.')[-1]
        return None

    def seconds(self, ticks):
        return ticks / self.tick_rate

    def possessables(self):
        out = {}
        for p in (self.movie.get('Possessables') or []):
            cls = p.get('PossessedObjectClass')
            cname = scriptobjs.name_of(cls[1]) if cls and cls[0] == 'import' else cls
            out[guid_str(p.get('Guid'))] = dict(name=p.get('Name'), cls=cname, parent=guid_str(p.get('ParentGuid')), tags=p.get('Tags'))
        return out

    def spawnables(self):
        out = {}
        for s in (self.movie.get('Spawnables') or []):
            out[guid_str(s.get('Guid'))] = dict(name=s.get('Name'), template=s.get('ObjectTemplate'), spawnable=s)
        return out

    def bindings(self):
        return [(guid_str(b.get('ObjectGuid')), b.get('BindingName'), b.get('Tracks') or []) for b in (self.movie.get('ObjectBindings') or [])]

    def track_sections(self, tref):
        t = self.obj(tref)
        if t is None:
            return []
        return [(self.kind(s), self.obj(s)) for s in (t.get('Sections') or t.get('AnimationSections') or [])]

    def track_name(self, tref):
        t = self.obj(tref) or {}
        pb = t.get('PropertyBinding') or {}
        return pb.get('PropertyName') or pb.get('PropertyPath') or t.get('DisplayName')

    def range_of(self, section):
        r = section.get('SectionRange') or {}
        lo, hi = r.get('lower'), r.get('upper')
        lo_v = lo[1] if lo and lo[0] != 2 else None
        hi_v = hi[1] if hi and hi[0] != 2 else None
        return lo_v, hi_v


def eval_channel(ch, t, tick_rate):
    """Value of a float channel at tick t (cubic/linear/constant as keyed; tangents per UE's FMovieSceneFloatChannel:
    tangent units are value per tick-frame... approximated with Hermite in ticks)."""
    times, values = ch['times'], ch['values']
    if not times:
        return ch['default'] if ch['has_default'] else None
    if t <= times[0]:
        return values[0]['v']
    if t >= times[-1]:
        return values[-1]['v']
    import bisect
    k = bisect.bisect_right(times, t) - 1
    t0, t1 = times[k], times[k + 1]
    a, b = values[k], values[k + 1]
    u = (t - t0) / float(t1 - t0)
    if a['interp'] == 1:   # RCIM_Constant
        return a['v']
    if a['interp'] == 0:   # RCIM_Linear
        return a['v'] + (b['v'] - a['v']) * u
    # RCIM_Cubic: Hermite with the leave / arrive tangents (per frame of the tick resolution -> scale by the gap)
    dt = float(t1 - t0)
    m0 = a['leave'] * dt
    m1 = b['arrive'] * dt
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    return h00 * a['v'] + h10 * m0 + h01 * b['v'] + h11 * m1
