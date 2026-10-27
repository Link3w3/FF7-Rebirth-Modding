"""Sephiroth's KH2 form: his KH2 moves as key animations (.cacanim) for Create a Character System's Import Key Animations, plus the
manifest the editor build reads (which FF7 Rebirth animation name each one plays as, in which pack, and its hits).
    make_kh2_keys.py <out folder>
The retargeted FBXs play at 60 fps (KH2's rate; the files say 24). The retarget kept the hips at standing height, so
grounded moves get their hips lowered until a foot touches the ground. The game moves the character by the root (Trans)
of its animations, so the in-place KH2 runs and walks get root motion (their stride's speed)."""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from clip import Clip

SRC = '/data/uploads/Kh2Rebirth/Remap'
FILES = {os.path.basename(f).split('_')[0]: f for f in glob.glob(SRC + '/*.fbx')}
IMPORT_FOLDER = '/Game/RebirthSkelCompat/Imported/KH2Sephiroth'
PACK = 'Battle04'                      # his KH2 form: an animation pack of its own (hold Triangle after the flying form)
OWN = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'

RUN_RATE, RUN_SPEED = 1.5, 700.0       # KH2's stride runs at about 4.6 m/s; the game's run at 7.8 m/s
WALK_SPEED = 120.0                     # KH2's walk stride (the game's walk is 1.06 m/s)

# name -> how it is made. src: KH2/KH3 file; frames: (a, b) slice; reverse; ground; rate (playback speed); twist (hips
# turned, chest kept forward, degrees); root (cm/s added to Trans); hits (s, after edits); loop; hold (s at the end);
# face: turned to face the way the move goes (the remaps keep KH2's bladed stance, chest and face 30-65 degrees to his
# left, which the game shows as sideways): 'body' the whole body, 'travel' chest, face, knees and planted feet over the
# feet's stride, 'span' the whole body by the turn its first frames need, changing to the turn its last frames need.
SPEC = {
    # ---- standing, running, walking
    'B_Idle01_1':   dict(src='OWA1015', face='body', ground=True, loop=True, kh3='1015 battle idle'),
    'B_Idle01_0':   dict(src='OWA1014', face='span', ground=True, kh3='1014 into the battle stance'),
    'B_Run01_1':    dict(src='OWA1013', face='travel', ground=True, rate=RUN_RATE, root=(RUN_SPEED, 0, 0), loop=True, kh3='1013 run'),
    'B_Run01_0_L0':   dict(src='OWA1021', face='travel', ground=True, kh3='1021 run start'),
    'B_Run01_0_L90':  dict(src='OWA1021L', face='travel', ground=True, kh3='1021L run start, left'),
    'B_Run01_0_R90':  dict(src='OWA1021R', face='travel', ground=True, notifies='B_Run01_0_L90', kh3='1021R run start, right'),
    'B_Run01_0_L180': dict(src='OWA1021BL', face='travel', ground=True, kh3='1021BL run start, turning back left'),
    'B_Run01_0_R180': dict(src='OWA1021BR', face='travel', ground=True, kh3='1021BR run start, turning back right'),
    'B_Walk01_1':   dict(src='OWA1016', face='travel', ground=True, root=(WALK_SPEED, 0, 0), loop=True, kh3='1016 battle walk'),
    'B_WalkFL01_1': dict(src='OWA1016', face='travel', ground=True, twist=-45, root=(WALK_SPEED * .7071, -WALK_SPEED * .7071, 0), loop=True, kh3='1016, legs turned'),
    'B_WalkFR01_1': dict(src='OWA1016', face='travel', ground=True, twist=45, root=(WALK_SPEED * .7071, WALK_SPEED * .7071, 0), loop=True, kh3='1016, legs turned'),
    'B_WalkL01_1':  dict(src='OWA1016', face='travel', ground=True, twist=-90, root=(0, -WALK_SPEED, 0), loop=True, kh3='1016, legs turned'),
    'B_WalkR01_1':  dict(src='OWA1016', face='travel', ground=True, twist=90, root=(0, WALK_SPEED, 0), loop=True, kh3='1016, legs turned'),
    'B_WalkB01_1':  dict(src='OWA1016', face='travel', reverse=True, ground=True, root=(-WALK_SPEED, 0, 0), loop=True, kh3='1016 played backwards'),
    'B_WalkBL01_1': dict(src='OWA1016', face='travel', reverse=True, ground=True, twist=45, root=(-WALK_SPEED * .7071, -WALK_SPEED * .7071, 0), loop=True, kh3='1016 backwards, legs turned'),
    'B_WalkBR01_1': dict(src='OWA1016', face='travel', reverse=True, ground=True, twist=-45, root=(-WALK_SPEED * .7071, WALK_SPEED * .7071, 0), loop=True, kh3='1016 backwards, legs turned'),
    # ---- falling, guarding, dodging
    'B_Fall01_1':   dict(src='OWA0033', face='body', loop=True, kh3='0033 in the air'),
    'B_Fall01_2':   dict(src='OWA0034', face='body', ground=True, kh3='0034 landing'),
    'B_Guard01_0':  dict(src='OWABLOCK', frames=(0, 13), face='span', ground=True, kh3='block, into the guard'),
    'B_Guard01_1':  dict(src='OWABLOCK', frames=(28, 29), hold=1.3, face='body', ground=True, loop=True, kh3='block, guard held'),
    'B_Guard01_2':  dict(src='OWABLOCK', frames=(0, 13), reverse=True, face='span', ground=True, kh3='block, out of the guard'),
    'B_DmgGuard02': dict(src='OWABLOCKHIT', face='body', ground=True, kh3='block hit'),
    'B_Avoid01_0':  dict(src='OWADODGEGROUND', frames=(0, 6), face='travel', ground=True, kh3='dodge, start'),
    'B_Avoid01_1':  dict(src='OWADODGEGROUND', frames=(5, 16), face='travel', ground=True, kh3='dodge, dash'),
    'B_Avoid01_2':  dict(src='OWADODGEGROUND', frames=(15, None), ground=True, kh3='dodge, end'),
    'B_Avoid02_2':  dict(src='OWADODGEGROUND', frames=(15, None), ground=True, kh3='dodge, end'),
    # ---- getting hit
    'B_DmgF01':     dict(src='OWA0201', face='body', ground=True, kh3='0201 small damage'),
    'B_DmgB01':     dict(src='OWA0202', face='body', ground=True, kh3='0202 small damage'),
    'B_DmgL01':     dict(src='OWA0203', face='body', ground=True, kh3='0203 small damage'),
    'B_DmgR01':     dict(src='OWA0204', face='body', ground=True, kh3='0204 small damage'),
    'B_DmgF02':     dict(src='OWA0205', face='body', ground=True, kh3='0205 small damage'),
    'B_DmgB02':     dict(src='OWA0206', ground=True, kh3='0206 small damage'),
    'B_DmgBlowF01_0': dict(src='OWA0211', face='body', kh3='0211 knocked back'),
    'B_DmgBlowF01_1': dict(src='OWA0212', face='body', loop=True, kh3='0212 knocked back, flying'),
    'B_DmgBlowF01_2': dict(src='OWA0213', face='body', ground=True, kh3='0213 knocked back, landing'),
    'B_DmgBlowB01_0': dict(src='OWA0214', face='body', kh3='0214 knocked forward'),
    'B_DmgBlowB01_1': dict(src='OWA0215', face='body', loop=True, kh3='0215 knocked forward, flying'),
    'B_DmgBlowB01_2': dict(src='OWA0216', face='body', ground=True, kh3='0216 knocked forward, landing'),
    # ---- items, Meteor, victory
    'B_Item01':     dict(src='OWAITEMGROUND', ground=True, hits=[0.42], kh3='item'),
    'B_ItemCure01': dict(src='OWAITEMGROUND', ground=True, hits=[0.42], kh3='item'),
    # Meteor: MASAFINISH from his stance (frame 50) as he raises the Masamune to the sky (at the top 1.0 s in: the meteor is
    # called), held while it falls, then eased back into his KH2 stance.
    'B_AtkLimit03_0': dict(src='MASAFINISH', frames=(50, 585), then='OWA1015', then_frames=(0, 30), blend=20, ground=True, hits=[1.0],
                           notifies='B_MagAttack01_2', kh3='MASAFINISH: raises his sword to the sky (Meteor)'),
    'B_Win01':      dict(src='OWAFULLSL', ground=True, kh3='sword raised'),
    # ---- attacks (KH3 13xx slots)
    'B_NAttack01_0':  dict(src='OWA13056', ground=True, hits=[0.10, 0.47], kh3='1305/1306 speed slash'),
    'B_NAttack02_0':  dict(src='OWA1361', ground=True, hits=[0.10, 0.38, 0.57], kh3='1361 radial blaster'),
    'B_NAttack03_0':  dict(src='OWA1359', ground=True, hits=[0.14, 0.42], kh3='1359 quick slash'),
    'B_NAttack04_0':  dict(src='OWA1304', ground=True, hits=[0.23, 0.51, 0.76], kh3='1304 finisher'),
    'B_NPAttack01':   dict(src='OWA1319', ground=True, hits=[0.44], kh3='1319 rising spiral'),
    'B_NAttackJ01_0': dict(src='OWA13156', hits=[0.10, 0.46], kh3='1315/1316 air speed slash'),
    'B_NAttackJ02_0': dict(src='OWA1365', hits=[0.10, 0.38, 0.56], kh3='1365 air radial blaster'),
    'B_NAttackJ03_0': dict(src='OWA1314', hits=[0.23, 0.51, 0.68], kh3='1314 air finisher'),
    'B_NPAttackJ01':  dict(src='OWA1310', hits=[0.17, 0.47], kh3='1310 air downward slash'),
}

_cache = {}


def source(name):
    if name not in _cache:
        _cache[name] = Clip.from_fbx(FILES[name])
    return _cache[name].copy()


def make(key, s):
    c = source(s['src'])
    if 'frames' in s:
        c = c.frames_range(*s['frames'])
    if s.get('reverse'):
        c = c.reversed()
    if 'then' in s:
        if s.get('hold_between'):
            c.hold(s['hold_between'])
        nxt = source(s['then'])
        if 'then_frames' in s:
            nxt = nxt.frames_range(*s['then_frames'])
        c = c.then(nxt, blend_frames=s.get('blend', 0))
    if s.get('hold'):
        c.hold(s['hold'])
    if s.get('rate'):
        c = c.retimed(c.seconds / s['rate'])
    if s.get('face'):
        c.face_forward(s['face'])
    if s.get('twist'):
        c.twist_lower_body(s['twist'])
    if s.get('ground'):
        c.ground()
    if s.get('root'):
        c.root_motion(velocity=s['root'])
    c.name = 'KH2_' + key
    return c


def main(out):
    os.makedirs(out, exist_ok=True)
    manifest = {'import_folder': IMPORT_FOLDER, 'skeleton': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton',
                'fps': 60, 'moves': []}
    for key, s in SPEC.items():
        c = make(key, s).game_root()   # last: the root as the game's animations carry it
        path = os.path.join(out, c.name + '.cacanim')
        tracks = c.write(path, loop=bool(s.get('loop')))
        root = c.T[:, c.index['Trans']]
        item = dict(set=PACK, name=key, animation='%s/%s.%s' % (IMPORT_FOLDER, c.name, c.name), build=True,
                    notifies_from=OWN + '%s.%s' % (s.get('notifies', key), s.get('notifies', key)),
                    hits=s.get('hits', []), seconds=round(c.seconds, 3), frames=c.frames, source=s['src'], kh3=s.get('kh3', ''),
                    root_travel=[round(float(v), 1) for v in (root[-1] - root[0])], tracks=tracks)
        manifest['moves'].append(item)
        print('%-15s %-20s %4d frames %5.2fs  root %+6.0f %+6.0f %+6.0f  %4d tracks  %6.0f KB  hits %s' % (
            key, s['src'], c.frames, c.seconds, *item['root_travel'], tracks, os.path.getsize(path) / 1024, item['hits']))
    # Not built: the KH2 form's pack starts as his own Battle00 (sources), so it also needs what his normal form gets from
    # the other packs (Octaslash Prime, Heartless Angel); and every form casts Meteor with the KH2 sword raise.
    built = '/Game/RebirthSkelCompat/Built/SephirothForms/%s/%s.%s'
    transform = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle01/%s.%s'
    manifest['sources'] = [{'path': '/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', 'as_': PACK},
                           {'path': '/Game/Motion/Player/PC0010_Sephiroth/Battle00_Comp.Battle00_Comp', 'as_': PACK}]
    manifest['extra'] = [
        dict(set=PACK, name='B_AtkLimit02_0', animation=transform % ('B_AtkLimit02_0', 'B_AtkLimit02_0'), then=[transform % ('B_AtkLimit02_1', 'B_AtkLimit02_1')], build=False),
        dict(set=PACK, name='B_AtkTenshi01_0', animation=built % ('Battle02', 'B_AtkTenshi01_0', 'B_AtkTenshi01_0'), build=False),
        dict(set=PACK, name='B_AtkTenshi01_1', animation=built % ('Battle02', 'B_AtkTenshi01_1', 'B_AtkTenshi01_1'), build=False),
    ] + [dict(set=other, name='B_AtkLimit03_0', animation=built % (PACK, 'B_AtkLimit03_0', 'B_AtkLimit03_0'), build=False)
         for other in ('Battle00', 'Battle02', 'Battle03')]
    json.dump(manifest, open(os.path.join(out, 'kh2_moves.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
