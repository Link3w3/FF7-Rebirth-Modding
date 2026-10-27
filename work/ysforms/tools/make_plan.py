"""The moves of the Fully Playable (Young) Sephiroth forms update (Create a Character System 3.12): the plan the editor
step (ysf_build.py, in an editor commandlet) builds from.

  * YOUNG SEPHIROTH (Battle07): his own Ever Crisis moves, built from the CH049 clips retargeted onto Sephiroth's
    skeleton (/Game/Motion/Player/PC0010_Sephiroth_CH049/PC0010_CH049_*), each a part of one of his skills around its
    blows (ys/make_ys_moves.py's choices), with the gameplay notifies of Sephiroth's move of that name lined up on his
    blows, and Sephiroth's sounds and effects of that move (swings, cloth, trails, slashes) moved onto his blows (a
    carrier per move, copied onto it). What he has no clip of is Sephiroth's own (the pack's Battle00 source).
  * WINGED (Battle02): the transformed Sephiroth's moves made again with his feelers ("whispers"): the effects his
    animations play only for a feeler ability (Branch Condition: Ability ID *_Feeler: the black feeler slashes, the
    feeler burst of Hell's Gate) play always and the plain ones they replace never; Zanshin's and Hell's Gate's feeler
    bullets (the feelers that burst out of the ground) are added as damage of their own, the boss's feeler rows
    (PC0010_10_*_Feeler_*). The casts the transformed abilities play (B_AtkMag01_*) get their effects for your abilities'
    IDs (Ground Feeler's feelers out of the ground, the spells' charge).
    make_plan.py <out plan.json>"""
import json, re, sys
sys.path.insert(0, '/work/ys')
import make_ys_moves as Y

DESC = {it['path']: it for it in json.load(open('/work/ys/seph_described.json'))}
CLIPS = json.load(open('/work/ch049anim/out/report.json'))['clips']
DAMAGE = json.load(open('/work/sephatb/damage_rows.json'))
CH = '/Game/Motion/Player/PC0010_Sephiroth_CH049/PC0010_CH049_%s'
SEPH, SEPH01, SEPHC, TR00, TR01 = Y.SEPH, Y.SEPH01, Y.SEPHC, Y.TR00, Y.TR01
path = Y.path

# moves of his Battle00 that Battle07 keeps as they are (the JSON copies their entries): Skewer's composite (the stab, then
# the lift and throw, which ForceGrabs' carry follows)
KEEP_FROM_BATTLE00 = ['B_AtkStab01']
# the moves of the plan with no sounds or effects of Sephiroth's moved onto them (his own motion, timed otherwise)
NO_EXTRAS = re.compile(r'^B_(Idle|Run|Walk|Turn|Step|Dmg|Die|Down|Fall|Win|Guard)')


def clip_length(clip):
    c = CLIPS['anim_ch049_' + clip]
    return (c['frames'] - 1) / c['fps']


def niagara(text):
    def num(m):
        return [float(v) for v in m.groups()] if m else None
    t = re.search(r'm_Template=([^,)]*)', text)
    s = re.search(r'm_SocketName="?([^",)]*)', text)
    loc = num(re.search(r'm_LocationOffset=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)', text))
    rot = num(re.search(r'm_RotationOffset=\(Pitch=([-\d.]+),Yaw=([-\d.]+),Roll=([-\d.]+)\)', text))
    return (t.group(1) if t else ''), (s.group(1) if s else ''), loc, rot


def time_map(old_len, new_len, anchors):
    def f(t):
        t = min(max(t, 0.0), old_len)
        po, pn = 0.0, 0.0
        for o, n in anchors:
            if t <= o:
                return pn + (t - po) * (n - pn) / (o - po) if o - po > 1e-6 else n
            po, pn = o, n
        return pn + (t - po) * (new_len - pn) / (old_len - po) if old_len - po > 1e-6 else pn
    return f


def extras_for(nf, new_hits, new_len):
    """Sephiroth's sounds and effects of the move nf, in the built move's time: those within 0.4 s of one of its hits keep
    their place relative to it (on the move's hit there), the rest follow the build's time map."""
    it = DESC.get(nf)
    if it is None:
        return [], 'not described'
    old_len = float(it['length'])
    groups = sorted(it.get('hits') or [])
    anchors = [(g, h) for g, h in zip(groups, new_hits)]
    f = time_map(old_len, new_len, anchors)
    out = []
    for n in it.get('notifies', []):
        if not n.get('motion'):
            continue
        cls = n.get('class', '')
        s = n.get('settings') or {}
        t = float(n.get('time', 0.0))
        near = [(abs(t - g), g, h) for g, h in anchors if abs(t - g) <= 0.4]
        at = (min(near)[2] + (t - min(near)[1])) if near else f(t)
        at = round(min(max(at, 0.0), max(new_len - 0.02, 0.0)), 4)
        if cls == 'EndAnimNotifyPlayCharacterSound':
            e = {'kind': 'sound', 'time': at, 'bank': s.get('SoundRef', ''), 'cue': s.get('SoundName', '')}
            if s.get('AttachPointName'):
                e['attach'] = s['AttachPointName']
            if e['bank'] and e['cue']:
                out.append(e)
        elif cls == 'AnimNotifyState_EndTimedNiagaraEffect':
            if s.get('m_BranchConditionType'):
                continue   # (an effect for some abilities only)
            template, socket, loc, rot = niagara(s.get('m_NiagaraCreateParams', ''))
            if not template:
                continue
            e = {'kind': 'effect', 'time': at, 'effect': template, 'socket': socket or 'Trans',
                 'duration': round(max(0.05, float(n.get('duration') or 0.3)), 4),
                 'on': 'Weapon1' if s.get('m_AttachType') == 'Weapon1' else 'Character'}
            if loc and any(abs(v) > 1e-4 for v in loc):
                e['loc'] = loc
            if rot and any(abs(v) > 1e-4 for v in rot):
                e['rot'] = rot
            out.append(e)
    return out, '%d of %s\'s sounds and effects' % (len(out), nf.rsplit('.', 1)[-1])


def battle07():
    moves, notes = [], []
    for name, (clip, t0, t1, speed, blows, nf) in Y.ATTACKS.items():
        if name in KEEP_FROM_BATTLE00:
            continue
        nf = path(nf or (SEPH + name))
        length = clip_length(clip)
        end = t1 if t1 > 0 else length
        new_len = (end - t0) / speed
        hits = [round(max(0.0, (b - t0) / speed), 4) for b in blows]
        m = {'set': 'Battle07', 'name': name, 'animation': path(CH % clip), 'notifies_from': nf,
             'hits': [{'time': h} for h in hits], 'source': clip}
        if t0 > 0 or t1 > 0:
            m['clip'] = [t0, t1]
        if abs(speed - 1.0) > 1e-6:
            m['speed'] = speed
        if not NO_EXTRAS.match(name):
            ex_from = nf if nf in DESC else path(SEPH + name.replace('_Comp', ''))
            extras, why = extras_for(ex_from, hits, new_len)
            if extras:
                m['extras'] = extras
            notes.append('%s: %s' % (name, why))
        m['notes'] = 'his %s %.2f - %.2f s at %.2fx (%.2f s), blows %s' % (clip, t0, end, speed, new_len, hits)
        moves.append(m)
    return moves, notes


# ---- WINGED (Battle02): the transformed Sephiroth's moves as built in 3.6 (Notifies From your Sephiroth's move of that
# name, Keep Source Effects), made again with their feeler branches decided and the feeler bullets added
FEELERS = {'*_Feeler': '*'}
CAST = {'PC0010_10_Fire3': '*'}            # your spells in WINGED: the transformed Sephiroth's arm charge
REBUILD = {
    # name: (transformed animation, branches)
    'B_NAttack01_0': ('B_NAttack01_0', FEELERS), 'B_NAttack02_0': ('B_NAttack02_0', FEELERS),
    'B_NAttack03_0': ('B_NAttack03_0', FEELERS), 'B_NAttack04_0': ('B_NAttack04_0', FEELERS),
    'B_NAttackJ01_0': ('B_NAttackJ01_0', FEELERS), 'B_NAttackJ02_0': ('B_NAttackJ02_0', FEELERS),
    'B_NAttackJ03_0': ('B_NAttackJ03_0', FEELERS),
    'B_SAttack01_0': ('B_SAttack01_0', FEELERS), 'B_SAttack02_0': ('B_SAttack02_0', FEELERS),
    'B_SAttack06_0': ('B_SAttack06_0', FEELERS), 'B_SAttack07_0': ('B_SAttack06_0', FEELERS),
    'B_SAttack09_0': ('B_SAttack10_0', FEELERS), 'B_SAttack10_0': ('B_SAttack10_0', FEELERS),
    'B_AtkBurst01_0': ('B_AtkBurst01_0', FEELERS), 'B_AtkBurst01_1': ('B_AtkBurst01_1', FEELERS),
    'B_AtkBurstA01_0': ('B_AtkBurst01_0', FEELERS), 'B_AtkBurstA01_1': ('B_AtkBurst01_1', FEELERS),
    'B_AtkBurst02_0': ('B_AtkBurst02_0', FEELERS), 'B_AtkBurst02_1': ('B_AtkBurst02_1', FEELERS),
    'B_AtkLimit01_1': ('B_AtkLimit01_5', {'PC0010_10_Hattou02_Feeler': '*'}),
    'B_MagAttack01_0': ('B_AtkMag01_0', CAST), 'B_MagAttack01_1': ('B_AtkMag01_1', CAST), 'B_MagAttack01_2': ('B_AtkMag01_2', CAST),
    'B_MagCure01_0': ('B_AtkMag01_0', CAST), 'B_MagCure01_1': ('B_AtkMag01_1', CAST), 'B_MagCure01_2': ('B_AtkMag01_2', CAST),
}
for side in 'LR':
    for k in range(1, 5):
        REBUILD['B_ParryAttack%s%02d' % (side, k)] = ('B_NAttack%02d_0' % k, FEELERS)
# the boss's abilities of the animations with feeler bullets: (its plain damage prefix, its feeler one)
FEELER_DAMAGE = {'B_AtkBurst01_0': 'PC0010_10_Zanshin01', 'B_AtkBurst01_1': 'PC0010_10_Zanshin02',
                 'B_AtkBurst02_0': 'PC0010_10_Gokumon01', 'B_AtkBurst02_1': 'PC0010_10_Gokumon02'}
# the transformed casts your T abilities play: built from themselves (all their notifies) with their ability branches
# pointed at your abilities (wildcards: the double casts of the weapons too)
SPELLS = {'PC0010_10_Fire3': 'PC0010_*Fira*', 'PC0010_10_Wind3': 'PC0010_*Aero*', 'PC0010_10_Thunder3': 'PC0010_*Thund*',
          'PC0010_10_Blizzard3': 'PC0010_*Blizz*', 'PC0010_10_ShadowFlare': 'PC0010_*ShadowFlare'}
CASTS = {'Battle02': {'B_AtkMag01_1': SPELLS, 'B_AtkMag01_2': {}, 'B_AtkMag01_3': {'PC0010_10_GroundFeeler': 'PC0010_*GroundFeeler'},
                      'B_AtkMag01_4': {}},
         'Battle00': {'B_AtkMag01_1': SPELLS}}


def damage_ids(text):
    return re.findall(r'"([^"]*)"', text or '')


def source_damage(anim):
    """The feeler bullets of a transformed animation: its damage notifies' IDs that only the feeler ability has rows for,
    each as the boss's feeler row's full ID."""
    prefix = FEELER_DAMAGE.get(anim)
    if not prefix:
        return []
    it = DESC[path(TR00 + anim)]
    out = []
    for n in it['notifies']:
        if not n.get('hit'):
            continue
        ids = damage_ids((n.get('settings') or {}).get('DamageSourceIDs', ''))
        new = []
        for i in ids:
            if not i.startswith('?_'):
                continue
            plain, feeler = prefix + i[1:], prefix + '_Feeler' + i[1:]
            if plain not in DAMAGE and feeler in DAMAGE:
                new.append(feeler)
        if new:
            out.append({'time': round(float(n['time']), 4), 'duration': round(float(n.get('duration') or 0.0), 4),
                        'state': 'State' in n['class'], 'ids': new})
    return out


def branches_found(anim_path, rules):
    """The rules that match a branch of the animation (to report them, and to leave out rules that match nothing)."""
    it = DESC.get(anim_path, {})
    have = set()
    for n in it.get('notifies', []):
        s = n.get('settings') or {}
        if s.get('m_BranchConditionType') == 'AbilityID':
            have.add(s.get('m_BranchConditionName', ''))
    return {k: v for k, v in rules.items() if k in have}, sorted(have)


def battle02():
    moves, notes = [], []
    for name, (anim, rules) in REBUILD.items():
        src = path(TR00 + anim)
        used, have = branches_found(src, rules)
        m = {'set': 'Battle02', 'name': name, 'animation': src, 'notifies_from': path(SEPH + name), 'hits': [],
             'branches': used, 'source': anim}
        sd = source_damage(anim)
        if sd:
            m['source_damage'] = sd
        if not used and not sd:
            notes.append('%s (%s): left as built (no feeler branch: %s)' % (name, anim, have))
            continue
        moves.append(m)
        notes.append('%s (%s): branches %s of %s%s' % (name, anim, used, have,
                                                       ('; feeler damage ' + '; '.join('%.2f s %s' % (x['time'], ', '.join(x['ids'])) for x in sd)) if sd else ''))
    for st, casts in CASTS.items():
        for name, rules in casts.items():
            src = path(TR00 + name)
            used, have = branches_found(src, rules)
            if not used:
                notes.append('%s/%s: left as the game has it (branches %s work as they are)' % (st, name, have))
                continue
            m = {'set': st, 'name': name, 'animation': src, 'notifies_from': src, 'hits': [], 'branches': used, 'source': name,
                 'all_notifies': True}
            moves.append(m)
            notes.append('%s/%s: its own notifies; branches %s of %s' % (st, name, used, have))
    return moves, notes


def main(out):
    m7, n7 = battle07()
    m2, n2 = battle02()
    plan = {'version': 1, 'moves': m7 + m2, 'chains': Y.CHAINS, 'keep_from_battle00': KEEP_FROM_BATTLE00}
    keys = [m['set'] + '/' + m['name'] for m in plan['moves']]
    assert len(keys) == len(set(keys)), 'a move twice'
    json.dump(plan, open(out, 'w'), indent=1)
    extras = sum(len(m.get('extras', [])) for m in m7)
    print('%d moves: Battle07 %d (%d with carriers, %d sounds and effects), Battle02 %d, Battle00 %d' % (
        len(plan['moves']), len(m7), sum(1 for m in m7 if m.get('extras')), extras,
        sum(1 for m in m2 if m['set'] == 'Battle02'), sum(1 for m in m2 if m['set'] == 'Battle00')))
    for line in n7 + n2:
        print('  ' + line)


if __name__ == '__main__':
    main(sys.argv[1])
