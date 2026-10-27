"""Vincent's Galian Beast entrance from the game's transformation cutscene EV_NIBLE_8310 (the Shinra Manor fight: his own
cameras, animations, effects and sounds), for the GALIAN form:

  shot 1 (before the switch, on Vincent): cut C0230 - the camera high above him as the change takes hold, his cutscene
         animation, the aura around his body (BodyAura_01), his groan, the cutscene's sound track (1606f, from 53.5 s),
  shot 2 (before the switch, on Vincent): cut C0260 to the change (77.333 s, where the cutscene hides him and shows the beast)
         - the low wide shot as he twists, his cry,
  shot 3 (after the switch, on the beast): the rest of C0260 - the beast where he stood (a short white flash hides the swap),
  shot 4 (on the beast): cut C0280 - the camera close on the beast, then back as it roars, its aura (BodyAura_02) and the
         roar's smoke, the shot's own sounds (EV_NIBLE_8310_28, 2447f).

Camera keys are the cut's camera (actor transform + camera component, FieldOfView, EndCameraComponent's Roll) at 30 fps,
relative to where the character's model stands in the cut (its actor + the mesh's -88 cm, turned with the actor), at the
cut models' own size (the battle's beast is full size too: "scale" 1).
    make_galian_intro.py <out.json>"""
import json, sys
sys.path[:0] = ['/work/galian1017/tools', '/work/bizcut1015/tools', '/work/cs']
from cutsample8310 import Cut, Xf

MESH_Z = -88.0          # the characters' mesh below their actor (as make_bizarro_intro.py)
FPS = 30.0
CUT = '/Game/Cut/Game/8700-NIBLE/EV_NIBLE_8310'
FX = '/Game/Effect/Cut/8700-NIBLE/EV_NIBLE_8310/Particle/'
SE_DIR = '/Game/Sound/SE/Cut/8700-NIBLE/EV_NIBLE_8310/'
VOICE_DIR = '/Game/Sound/Voice/{language}/Cut/8700-NIBLE/EV_NIBLE_8310/'
TRACK, TRACK_FROM = 'EV_NIBLE_8310_1606f', 53.5333   # the cut's sound track from the aura on (ManualSE, frame 1606)
CHANGE = 77.3333        # the cut hides Vincent and shows the beast (CutEvent ActorDraw)


def anim(name):
    return '%s/Motion/%s.%s' % (CUT, name, name)


def fx(name):
    return FX + name + '.' + name


def se(cue, at, start=0.0, stop=True):
    s = dict(bank=SE_DIR + cue + '.' + cue, cue=cue, at=round(at, 3))
    if start:
        s['start'] = round(start, 3)
    if stop:
        s['stop_at_end'] = True
    return s


def voice(cue, at):
    return dict(voice=VOICE_DIR + cue + '.' + cue, cue=cue, at=round(at, 3))


def relative_keys(c, shot_name, who, t0, t1):
    """Camera keys of shot `shot_name` from cut time t0 to t1 (s), relative to `who`'s model."""
    sh = next(s for s in c.shots if s['name'] == shot_name)
    rate = c.cam.tick_rate
    keys = []
    n = int(round((t1 - t0) * FPS))
    for k in range(n + 1):
        t = min(t0 + k / FPS, t1 - 1.0 / rate)
        tick = int(round(t * rate))
        tick = max(sh['lo'], min(sh['hi'] - 1, tick))
        cam = c.camera(sh, tick)
        actor = c.char(who, tick)
        model = Xf((actor.t[0], actor.t[1], actor.t[2] + MESH_Z), actor.r, (1, 1, 1))
        rel = model.relative(cam['world'])
        roll = rel.r[0] + (cam['roll'] or 0.0)
        keys.append([round(k / FPS if k < n else t1 - t0, 4), round(rel.t[0], 2), round(rel.t[1], 2), round(rel.t[2], 2),
                     round(rel.r[1], 3), round(rel.r[2], 3), round(roll, 3), round(cam['fov'], 3)])
    return keys


def build():
    c = Cut()
    shots = []
    # 1. C0230 (67.3 - 70.333): above Vincent; the aura (on him 65.07 - 70.33 in the cut), his groan at its start
    a0, a1 = 67.3, 70.3333
    shots.append(dict(
        name='C0230', seconds=round(a1 - a0, 3), before_switch=True,
        animation=anim('EV_NIBLE_8310_PC0011_00_C0230'), animation_start=0.0,
        camera=relative_keys(c, 'C0230', 'PC0011_00', a0, a1),
        effects=[dict(effect=fx('FX_EV_NIBLE_8310_BodyAura_01'), socket='C_Hip_a', at=0, seconds=round(a1 - a0, 3))],
        sounds=[voice('C3110_MAIN_6100_0900_24_vin', 0.0), se(TRACK, 0.0, a0 - TRACK_FROM)]))
    # 2. C0260 to the change (74.667 - 77.333): the low wide shot as he twists, his cry
    b0 = 74.6667
    shots.append(dict(
        name='C0260', seconds=round(CHANGE - b0, 3), before_switch=True,
        animation=anim('EV_NIBLE_8310_PC0011_00_C0260'), animation_start=0.0,
        camera=relative_keys(c, 'C0260', 'PC0011_00', b0, CHANGE),
        effects=[],
        sounds=[voice('C3110_MAIN_6100_0900_32_vin', 0.0), se(TRACK, 0.0, b0 - TRACK_FROM)]))
    # 3. the rest of C0260 (77.333 - 78.967): the beast where he stood
    c1 = 78.9667
    shots.append(dict(
        name='C0260b', seconds=round(c1 - CHANGE, 3), scale=1.0, flash=0.5, flash_color=[1.0, 1.0, 1.0],
        animation=anim('EV_NIBLE_8310_EB2160_00_C0260'), animation_start=round(CHANGE - b0, 3),
        camera=relative_keys(c, 'C0260', 'EB2160_00', CHANGE, c1),
        effects=[],
        sounds=[se(TRACK, 0.0, CHANGE - TRACK_FROM)]))
    # 4. C0280 (80.933 - 89.933): close on the beast, then back as it roars; its aura (84.1) and the roar's smoke (86.7)
    d0, d1 = 80.9333, 89.9333
    shots.append(dict(
        name='C0280', seconds=round(d1 - d0, 3), scale=1.0,
        animation=anim('EV_NIBLE_8310_EB2160_00_C0280'), animation_start=0.0,
        camera=relative_keys(c, 'C0280', 'EB2160_00', d0, d1),
        effects=[dict(effect=fx('FX_EV_NIBLE_8310_BodyAura_02'), socket='C_Hip_a', at=round(84.1 - d0, 3), seconds=round(d1 - 84.1, 3)),
                 dict(effect=fx('FX_EV_NIBLE_8310_Roar_Smoke_01'), at=round(86.7 - d0, 3), seconds=round(d1 - 86.7, 3), offset=[80.0, 0.0, 0.0])],
        sounds=[se('EV_NIBLE_8310_28', 0.0), se('EV_NIBLE_8310_2447f', 81.5667 - d0), se(TRACK, 0.0, d0 - TRACK_FROM)]))
    return dict(shots=shots, camera=dict(hold=0.2, blend_back=1.2, bars=0), hold_input=True, skip=True, invincible=True)


if __name__ == '__main__':
    e = build()
    json.dump(e, open(sys.argv[1], 'w'), indent=1)
    for s in e['shots']:
        k = s['camera']
        print(s['name'], s['seconds'], 's', len(k), 'keys; first', k[0], 'last', k[-1])
        for x in s['effects']:
            print('   effect', x['effect'].split('.')[-1], 'at', x['at'], 'for', x['seconds'], 'socket', x.get('socket'), 'offset', x.get('offset'))
        for x in s['sounds']:
            print('   sound', x['cue'], 'at', x['at'], 'start', x.get('start', 0))
    print('total %.2f s' % sum(s['seconds'] for s in e['shots']))
