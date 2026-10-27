"""Vincent's gun in the game's cutscenes: for each cutscene with Vincent, his animation sections (the cut's motions),
the gun's attach events (Constraint: which socket of whom), effects on the gun or his hands (muzzle flashes), and the
sound events, at 30 fps.  scan_cuts.py <pkgs dir> <out json>"""
import sys, os, re, json, glob
sys.path[:0] = ['/work/bizcut1015/tools', '/work/cs']
from cutread import Seq

PK = sys.argv[1]
OUT = sys.argv[2]
FPS = 30.0


def strings_of(blob):
    """Readable ASCII names in an event payload (its tagged properties' values)."""
    if isinstance(blob, str) and blob.startswith("b'"):
        try:
            blob = eval(blob)
        except Exception:
            return []
    if not isinstance(blob, (bytes, bytearray)):
        return []
    return [m.decode() for m in re.findall(rb'[A-Za-z0-9_/.:\-]{3,}', blob)]


def payload(kv):
    p = (kv or {}).get('Parameters') or {}
    st = p.get('struct') or {}
    return st.get('asset', ''), strings_of(p.get('bytes'))


def frames(seq, ticks):
    return round(ticks / seq.tick_rate * FPS, 1)


cuts = sorted({re.match(r'(Cut__Game__[^_]+(?:_[^_]+)*?__EV_[A-Z]+_[0-9]+)__', os.path.basename(f)).group(1)
               for f in glob.glob(PK + '/Cut__Game__*__EV_*__EV_*.uasset')})
report = {}
for base in cuts:
    ev = base.rsplit('__', 1)[1]
    r = {'cut': ev, 'vincent': [], 'gun': [], 'attach': [], 'effects': [], 'sounds': []}

    def seq(suffix):
        path = os.path.join(PK, '%s__%s%s.uasset' % (base, ev, suffix))
        return Seq(path) if os.path.exists(path) else None

    ch = seq('_Character')
    if ch and ch.movie:
        for g, name, tracks in ch.bindings():
            name = name or ''
            who = 'vincent' if 'PC0011' in name else 'gun' if 'WE0011' in name else None
            if not who:
                continue
            for t in tracks:
                for kind, sec in ch.track_sections(t):
                    if kind != 'MovieSceneSkeletalAnimationSection':
                        continue
                    params = sec.get('Params') or {}
                    if params.get('SlotName') == 'FacialSlot':
                        continue
                    lo, hi = ch.range_of(sec)
                    r[who].append({'binding': name, 'anim': params.get('RefOnDisconnected'), 'from': frames(ch, lo or 0), 'to': frames(ch, hi or 0),
                                   'start_offset': params.get('StartFrameOffset') or params.get('FirstLoopStartFrameOffset'),
                                   'rate': params.get('PlayRate')})
    co = seq('_Constraint')
    if co and co.movie:
        for t in co.movie.get('MasterTracks') or []:
            for kind, sec in co.track_sections(t):
                ed = (sec or {}).get('EventData') or {}
                for tm, kv in zip(ed.get('Times', []), ed.get('KeyValues', [])):
                    asset, names = payload(kv)
                    vals = [n for n in names if not re.match(r'(ActorName|ParentName|SocketName|Detach)_\d+_', n) and n not in ('NameProperty', 'BoolProperty', 'None')]
                    r['attach'].append({'frame': frames(co, tm), 'clip': asset.rsplit('.', 1)[-1], 'values': vals})
    fx = seq('_Effect')
    if fx and fx.movie:
        for g, name, tracks in fx.bindings():
            spans, att = [], []
            for t in tracks:
                tt = fx.obj(t) or {}
                for kind, sec in fx.track_sections(t):
                    if kind == 'MovieSceneSpawnSection':
                        bc = sec.get('BoolCurve') or {}
                        ts, vs = bc.get('Times', []), bc.get('Values', [])
                        on = None
                        for a, b in zip(ts, vs):
                            if b and on is None:
                                on = a
                            elif not b and on is not None:
                                spans.append([frames(fx, on), frames(fx, a)]); on = None
                        if on is not None:
                            spans.append([frames(fx, on), None])
                for sref in tt.get('ConstraintSections') or []:
                    sec = fx.obj(sref) or {}
                    if sec.get('AttachActorName'):
                        lo, hi = fx.range_of(sec)
                        att.append({'actor': sec.get('AttachActorName'), 'socket': sec.get('AttachSocketName'), 'from': frames(fx, lo or 0), 'to': frames(fx, hi or 0)})
            if any('PC0011' in a['actor'] or 'WE0011' in a['actor'] for a in att):
                r['effects'].append({'effect': name, 'spawn': spans, 'attached': att})
    for suffix in ('_Sound', '_ManualSE'):
        so = seq(suffix)
        if not (so and so.movie):
            continue
        for t in so.movie.get('MasterTracks') or []:
            for kind, sec in so.track_sections(t):
                ed = (sec or {}).get('EventData') or {}
                for tm, kv in zip(ed.get('Times', []), ed.get('KeyValues', [])):
                    asset, names = payload(kv)
                    cues = [n for n in names if n.startswith('EV_') or n.startswith('/Game/') or 'SE' in n]
                    r['sounds'].append({'frame': frames(so, tm), 'track': suffix[1:], 'clip': asset.rsplit('.', 1)[-1], 'names': cues[:6]})
    report[ev] = r
    print('%-14s vincent %2d sections, gun %d, attach %2d, effects on him/gun %2d, sounds %3d' % (
        ev, len(r['vincent']), len(r['gun']), len(r['attach']), len(r['effects']), len(r['sounds'])), flush=True)
json.dump(report, open(OUT, 'w'), indent=1)
