"""Bizarro Sephiroth's entrance from his transformation cutscene EV_FOREE_8630 (the game's own cameras, animations,
effects and line), for the BIZARRO form of SephirothForms.json:

  shot 1 (before the switch, on Sephiroth): the end of cut C0130 - Sephiroth's close-up as he says "Alone at last.
         Shall we?", his cutscene animation, the darkness that starts the transformation (Transform_01), the cutscene's
         sound track;
  shot 2 (after the switch, on Bizarro): cut C0160 (to 51.4 s) - Bizarro revealed, the camera rising along him, his cutscene
         animation, the transformation's sphere and shockwave as he appears (Transform_02, Transform_Shockwave_01), his
         aura (Transform_03), the sound track from there.

Camera keys are the cut's camera (actor transform + camera component, FieldOfView, EndCameraComponent's Roll) at 30 fps,
relative to where the character's model stands in the cut (its actor + the mesh's -88 cm, turned with the actor), in
the cut character's units (Bizarro's cut model is full size: "scale" 1, so the battle's 0.1 model gets them at 0.1).
    make_bizarro_intro.py <out.json>"""
import json, math, sys
sys.path[:0] = ['/work/bizcut1015/tools']
from cutsample import Cut, Xf

MESH_Z = -88.0          # the characters' mesh below their actor (CharacterMesh0 RelativeLocation Z, BP default)
FPS = 30.0
CUT = '/Game/Cut/Game/8800-FOREE/EV_FOREE_8630'
FX = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_8630/Particle/'
VOICE = '/Game/Sound/Voice/{language}/Cut/8800-FOREE/EV_FOREE_8630/C3510_MAIN_3400_0400_00_sep.C3510_MAIN_3400_0400_00_sep'
SE = '/Game/Sound/SE/Cut/8800-FOREE/EV_FOREE_8630/EV_FOREE_8630_0465f.EV_FOREE_8630_0465f'
SE_FROM = 15.5          # the cut starts that sound track 15.5 s in (ManualSE, frame 465)


def anim(name):
    return '%s/Motion/%s.%s' % (CUT, name, name)


def fx(name):
    return FX + name + '.' + name


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


def offset_of(c, who, t, world):
    actor = c.char(who, int(round(t * c.cam.tick_rate)))
    model = Xf((actor.t[0], actor.t[1], actor.t[2] + MESH_Z), actor.r, (1, 1, 1))
    p = model.inverse_apply(world)
    return [round(p[0], 1), round(p[1], 1), round(p[2], 1)]


def build():
    c = Cut()
    # shot 1: C0130 from 29.6 s (the line at 30.733) to its end (36.7)
    a0, a1 = 29.6, 36.7
    shot1 = dict(
        name='C0130', seconds=round(a1 - a0, 3), before_switch=True,
        animation=anim('EV_FOREE_8630_PC0010_10_C0130'), animation_start=round(a0 - 24.1667, 3),
        camera=relative_keys(c, 'C0130', 'PC0010_10', a0, a1),
        effects=[dict(effect=fx('FX_EV_FOREE_8630_Transform_01'), at=round(35.0333 - a0, 3), seconds=round(a1 - 35.0333, 3),
                      offset=offset_of(c, 'PC0010_10', 35.0333, (-2067.6, -10049.8, 1658.9)))],
        sounds=[dict(voice=VOICE, cue='C3510_MAIN_3400_0400_00_sep', at=round(30.7333 - a0, 3)),
                dict(bank=SE, cue='EV_FOREE_8630_0465f', at=0, start=round(a0 - SE_FROM, 3), stop_at_end=True)])
    # shot 2: C0160 (42.7 to 51.4: it ends as he starts to drop to the ground, which the battle's model does not do), Bizarro
    # (full size in the cut)
    b0, b1 = 42.7, 51.4
    mid = offset_of(c, 'EB2210_00', b0, (2822.3, -5021.3, 2332.2))      # his actor's middle
    mid[2] += 900.0                                                       # the sphere and shockwave around his body
    shot2 = dict(
        name='C0160', seconds=round(b1 - b0, 3), scale=1.0, flash=1.2, flash_color=[1.0, 1.0, 1.0],
        animation=anim('EV_FOREE_8630_EB2210_00_C0160'), animation_start=0.0,
        camera=relative_keys(c, 'C0160', 'EB2210_00', b0, b1),
        effects=[dict(effect=fx('FX_EV_FOREE_8630_Transform_02'), at=0, seconds=1.6, offset=mid),
                 dict(effect=fx('FX_EV_FOREE_8630_Transform_Shockwave_01'), at=0, seconds=1.1, offset=mid),
                 dict(effect=fx('FX_EV_FOREE_8630_Transform_03'), at=0, seconds=round(b1 - b0, 3),
                      offset=offset_of(c, 'EB2210_00', b0, (3470.1, -5047.2, 2474.4)))],
        sounds=[dict(bank=SE, cue='EV_FOREE_8630_0465f', at=0, start=round(b0 - SE_FROM, 3), stop_at_end=True)])
    return dict(shots=[shot1, shot2], camera=dict(hold=0.2, blend_back=1.2, bars=0), hold_input=True, skip=True, invincible=True)


if __name__ == '__main__':
    e = build()
    json.dump(e, open(sys.argv[1], 'w'), indent=1)
    for s in e['shots']:
        k = s['camera']
        print(s['name'], s['seconds'], 's', len(k), 'keys; first', k[0], 'last', k[-1])
        for x in s['effects']:
            print('   effect', x['effect'].split('.')[-1], 'at', x['at'], 'for', x['seconds'], 'offset', x.get('offset'))
        for x in s['sounds']:
            print('   sound', x['cue'], 'at', x['at'], 'start', x.get('start', 0))
