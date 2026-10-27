"""The CLOUD moveset (pack Battle11) of the Sephiroth forms: Cloud's own Rebirth battle motions, built with Create a
Character System's Build Moves onto Sephiroth's skeleton (Retarget: proportions), each with the gameplay notifies of
Sephiroth's move of that name (damage, combo, cancel and dodge windows, states, voice, face) lined up on Cloud's blows,
and Cloud's own sounds and effects (Buster Sword swings, trails, footsteps: Keep Source Effects).

  every name both have      Cloud's animation of that name (idles, walks, runs, turns, combo, air combo, guard, damage,
                            knock-downs, falls, death, victory)
  dodge (Sephiroth's warp)  Cloud's roll in its three pieces: start, roll, recovery (B_Avoid01_0 / _1 / _2)
  air dodge                 Cloud's air dodge (B_Avoid02_2, B_StepAB01); back step: Cloud's back step (B_StepB01)
  turning while guarding    Cloud's guard hold, as long as Sephiroth's turn (Cloud turns in his guard)
  the enemy book's idle     Cloud's idle
Left Sephiroth's: his Triangle, hold-Square and parry attacks, his stagger and a few damage pieces Cloud has no motion
for, the additive flinch (B_Dmg01_Add: Build Moves makes moves of whole-body animations), and the blend spaces (strafing
walk, turn: the mod 3.15.1 makes them play the set's own walks and turns).
    make_cloud_moveset.py <sets_seph_cloud.json> <cloud_moveset_describe.json> <out plan.json>"""
import json
import sys

SET = 'Battle11'
BUILD = '/Game/RebirthSkelCompat/Built/SephirothForms'
# Sephiroth's name -> (Cloud's name, clip start, clip end (0: its end), speed, notifies from (None: Sephiroth's own of the name),
#                      clip to the length of Notifies From, what it is)
EXTRA = {
    'B_Avoid01_0': ('B_Avoid01', 0.0, 0.1667, 1.0, None, False, "dodge: the roll's start"),
    'B_Avoid01_1': ('B_Avoid01', 0.1667, 0.5, 0.6667, None, False, 'dodge: the roll (as long as the warp)'),
    'B_Avoid01_2': ('B_Avoid01', 0.5, 0.0, 1.0, None, False, "dodge: the roll's recovery"),
    'B_Avoid02_2': ('B_AvoidJ01', 0.0, 0.0, 1.0, None, False, 'air dodge'),
    'B_StepB01': ('B_AvoidStpB01', 0.0, 0.0, 1.0, None, False, 'back step'),
    'B_StepAB01': ('B_AvoidJ01', 0.0, 0.0, 1.0, None, False, 'back step in the air'),
    'B_GuardTurn01_L90': ('B_Guard01_1', 0.0, 0.0, 1.0, None, True, 'turning while guarding: the guard hold'),
    'B_GuardTurn01_L180': ('B_Guard01_1', 0.0, 0.0, 1.0, None, True, 'turning while guarding: the guard hold'),
    'B_GuardTurn01_R90': ('B_Guard01_1', 0.0, 0.0, 1.0, None, True, 'turning while guarding: the guard hold'),
    'B_GuardTurn01_R180': ('B_Guard01_1', 0.0, 0.0, 1.0, None, True, 'turning while guarding: the guard hold'),
    'B_Idle01_1_EnemyBook': ('B_Idle01_1', 0.0, 0.0, 1.0, None, False, "the enemy book's idle"),
}
# Sephiroth's B_Run01_0_R90 is empty (no frames): its notifies from the mirrored run start
NOTIFIES_FROM = {'B_Run01_0_R90': 'B_Run01_0_L90'}
COMMANDS = ('B_Ability', 'B_AtkBurst', 'B_AtkLimit', 'B_AtkMag', 'B_Mag', 'B_Item', 'B_Chain', 'B_BurstChain', 'B_Comp',
            'B_EleBurst', 'B_Summon')


def main(sets_path, describe_path, out):
    sets = json.load(open(sets_path, encoding='utf-8-sig'))
    seph = sets[0]['animations']
    cloud = {k.lower(): (k, v) for k, v in sets[1]['animations'].items()}
    described = {x['path'].lower(): x for x in json.load(open(describe_path, encoding='utf-8-sig'))}
    moves, kept, keys = [], [], {}

    def about(path):
        return described.get(path.lower(), {})

    for name in sorted(seph, key=str.lower):
        if name.startswith(COMMANDS):
            continue
        spath = seph[name]
        if name in EXTRA:
            cname, t0, t1, speed, notifies, clip_like, note = EXTRA[name]
        elif name.lower() in cloud:
            cname, t0, t1, speed, notifies, clip_like, note = cloud[name.lower()][0], 0.0, 0.0, 1.0, None, False, 'the same move'
        else:
            kept.append((name, "Cloud has no motion for it"))
            continue
        cpath = cloud[cname.lower()][1]
        c, s = about(cpath), about(spath)
        if c.get('class') != 'AnimSequence' or s.get('class') not in ('AnimSequence', None) and s.get('class') != 'AnimSequence':
            kept.append((name, 'a %s (the mod makes it play the set\'s own moves)' % (c.get('class') or s.get('class'))))
            continue
        if c.get('additive'):
            kept.append((name, 'additive (Build Moves makes moves of whole-body animations)'))
            continue
        nfrom = notifies or (seph[NOTIFIES_FROM[name]] if name in NOTIFIES_FROM else spath)
        m = {'set': SET, 'name': name, 'animation': cpath, 'notifies_from': nfrom, 'source': cname, 'notes': note}
        # Cloud's blows (inside the clip, in the move's time): Sephiroth's damage lands on them
        length = float(c.get('length') or 0.0)
        end = t1 if t1 > 0 else length
        blows = [float(h if isinstance(h, (int, float)) else h.get('time', 0.0)) for h in (c.get('hits') or [])]
        blows = [round((b - t0) / speed, 4) for b in blows if t0 - 1e-4 <= b <= end + 1e-4]
        if blows and name not in EXTRA:   # (Cloud's dodges deal no damage of Sephiroth's: his warp's timing in proportion)
            m['hits'] = [{'time': b} for b in blows]
        if t0 > 0 or t1 > 0:
            m['clip'] = [t0, t1]
        if abs(speed - 1.0) > 1e-6:
            m['speed'] = speed
        if clip_like:
            m['clip_like_notifies_from'] = True
        m['length'] = round((end - t0) / speed, 4)
        moves.append(m)
        keys[name] = '%s/%s/%s.%s' % (BUILD, SET, name, name)
    plan = {'set': SET, 'moves': moves, 'keys': {SET: keys}, 'kept_sephiroths': kept}
    with open(out, 'w') as f:
        json.dump(plan, f, indent=1)
    for m in moves:
        print('%-22s <- %-18s %-14s speed %-6s hits %s' % (m['name'], m['source'], m.get('clip', '-'), m.get('speed', 1),
                                                          [h['time'] for h in m.get('hits', [])]))
    print('%d moves; kept Sephiroth\'s: %d' % (len(moves), len(kept)))
    for name, why in kept:
        print('   %-24s %s' % (name, why))


if __name__ == '__main__':
    main(*sys.argv[1:4])
