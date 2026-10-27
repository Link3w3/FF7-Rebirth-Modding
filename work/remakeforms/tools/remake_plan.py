"""The REMAKE (Battle08) and REMAKE WINGED (Battle09) forms' moves, made from FINAL FANTASY VII REMAKE's Sephiroth boss
animations (EB0021, converted into the End project under /Game/GameContents/Motion/Enemy/EB0021_Sephiroth) with the
Create a Character System editor's Build Moves, and what each one gets besides:
  * hits: Remake's own damage windows (read from the Remake paks: notifies_eb0021.json) or its swing sounds, with the
    damage of the move the gameplay notifies come from ("notifies_from": Sephiroth's own move of that name for his combo,
    the game's player abilities for the new ones), or a damage source of its own (PC0010_RM_*),
  * extras: Remake's sounds (its SE_EB0021 cues are in Sephiroth's own bank, SE_PC0010_00_Sephiroth_Standard, which his
    rows load), sword trails and its effects as Rebirth's versions of them (FX_PC0010_*, each Rebirth's remake of the
    Remake effect, Effect2SoundTable names the Remake sound), put on the built animations after the build.
Locomotion, guard, dodges and reactions stay Sephiroth's own (Rebirth's are the same captures as Remake's).
    remake_plan.py <notifies_eb0021.json> <out plan.json>"""
import json, sys

S0 = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth/Battle00/'
S1 = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth/Battle01/'
P = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
T = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/'
T1 = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle01/'   # (Heartless Angel's animations are in Battle01)
BUILD = '/Game/RebirthSkelCompat/Built/SephirothForms'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
FX = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/'
FX10 = '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/'

def fx(name):
    base = FX10 if name.startswith('FX_PC0010_10_') else FX
    return base + name + '.' + name

# Remake's sound cues -> the same sounds in Sephiroth's own bank (SE_PC0010_00_Sephiroth_Standard has Remake's cues;
# the few it names otherwise, its nearest)
CUE = {'EB0021_sword_swishL': 'sword_swishL', 'EB0021_sword_scapeL': 'EB0021_sword_scapeLL', 'EB0021_foot': 'B_Avoid01_0_foot',
       'EB0021_footbody': 'EB0021_bodyfall', 'B_AtkIchijin01_body': 'EB0021_bodyfall', 'B_AtkIchijin01_jump': 'B_AtkGokumon01_1_jump',
       'B_AtkVision01_whoosh': 'EB0021_whoosh03'}
SKIP_CUES = {'FX_EB0021_AtkYaiba_Exp_01'}
TRAIL = (fx('FX_PC0010_Weapon_Trail_01'), 'C_TrailA_b')
TRAIL_OCTA = (fx('FX_PC0010_Limit01_Trail_01'), 'C_TrailA_b')
# Rebirth's Octaslash (B_AtkLimit01_0, made from Remake's B_AtkHattou01_2 1.61 s in) places its slashes so: location,
# rotation (pitch, yaw, roll) at Trans; the two Remake has after them take the last ones'
OCTA_SLASH = [((40, 0, 100), (0, 0, 70)), ((40, 0, 100), (0, 20, -20)), ((0, 0, 170), (-5, 0, 95)), ((0, 0, 100), (0, 0, 8)),
              ((0, 0, 160), (0, 0, 200)), ((0, 0, 180), (0, 0, 120)), ((0, 0, 160), (0, 0, 160)), ((0, 0, 100), (0, 0, 90)),
              ((0, 0, 90), (-10, 0, 85))]


def load(path):
    return json.load(open(path))


class Move:
    def __init__(self, set_, key, src, nf, clip=None, speed=1.0, notes=''):
        self.set, self.key, self.src, self.nf, self.clip, self.speed, self.notes = set_, key, src, nf, clip, speed, notes
        self.hits, self.extras = [], []

    def t(self, source_time):
        """A time of the source animation in the built move (its clip and speed)."""
        start = self.clip[0] if self.clip else 0.0
        return round(max(0.0, (source_time - start) / self.speed), 4)

    def inside(self, source_time):
        if not self.clip:
            return True
        return self.clip[0] - 0.001 <= source_time <= self.clip[1] + 0.001

    def hit(self, source_time, window=0.0, damage=None):
        h = {'time': self.t(source_time)}
        if window:
            h['window'] = round(window / self.speed, 4)
        if damage:
            h['damage'] = damage
        self.hits.append(h)
        return h

    def sound(self, source_time, cue, attach=None):
        if cue in SKIP_CUES or not self.inside(source_time):
            return
        e = {'kind': 'sound', 'time': self.t(source_time), 'bank': SE, 'cue': CUE.get(cue, cue)}
        if attach:
            e['attach'] = attach
        self.extras.append(e)

    def effect(self, source_time, duration, path, socket, on='Character', loc=None, rot=None):
        if not self.inside(source_time):
            return
        end = source_time + duration
        if self.clip:
            end = min(end, self.clip[1])
        e = {'kind': 'effect', 'time': self.t(source_time), 'duration': round(max(0.05, (end - source_time) / self.speed), 4),
             'effect': path, 'socket': socket, 'on': on}
        if loc:
            e['loc'] = list(loc)
        if rot:
            e['rot'] = list(rot)
        self.extras.append(e)

    def trail(self, source_time, duration, which=TRAIL):
        self.effect(source_time, duration, which[0], which[1], on='Weapon1')

    def remake_sounds(self, N, name, skip=()):
        """Every sound notify of the Remake animation (its swing, cloth, katana, step sounds), mapped to Sephiroth's bank."""
        for n in N[name]['notifies']:
            if n['cls'] == 'EndAnimNotifyPlayCharacterSound':
                cue = n['props']['SoundName']
                if cue in skip:
                    continue
                self.sound(n['time'], cue, n['props'].get('AttachPointName'))

    def remake_trails(self, N, name, which=TRAIL):
        for n in N[name]['notifies']:
            if n['cls'] == 'EndAnimNotifyStateEffectCharaProperty':
                self.trail(n['time'], n['dur'], which)

    def json(self):
        out = {'set': self.set, 'name': self.key, 'animation': self.src, 'notifies_from': self.nf, 'hits': self.hits,
               'extras': sorted(self.extras, key=lambda e: e['time'])}
        if self.clip:
            out['clip'] = list(self.clip)
        if self.speed != 1.0:
            out['speed'] = self.speed
        if self.notes:
            out['notes'] = self.notes
        return out


def damage_windows(N, name):
    return [(round(n['time'], 4), round(n['dur'], 4)) for n in N[name]['notifies'] if 'BattleDamage' in n['cls']]


def plan(N):
    moves = []

    def add(m):
        moves.append(m)
        return m

    # ---- his combo (Remake's Assault chain, then Engetsu's full-moon slash), hold Square (Ichijin) ---------------------
    for key, src, at, notes in (('B_NAttack01_0', 'B_AtkAssault01', 0.30, 'Remake\'s Assault chain, 1st'),
                                ('B_NAttack02_0', 'B_AtkAssault02', 0.27, 'Assault chain, 2nd'),
                                ('B_NAttack03_0', 'B_AtkAssault04', 0.37, 'Assault chain, 4th')):
        m = add(Move('Battle08', key, S0 + src, P + key, notes=notes))
        m.hit(at, 0.10)
        m.remake_sounds(N, 'Battle00/' + src)
        m.trail(at - 0.06, 0.24)
    m = add(Move('Battle08', 'B_NAttack04_0', S0 + 'B_AtkEngetsu01', P + 'B_NAttack04_0', notes='Engetsu, finisher'))
    m.hit(0.94, 0.07)
    m.remake_sounds(N, 'Battle00/B_AtkEngetsu01')
    m.remake_trails(N, 'Battle00/B_AtkEngetsu01')
    m.effect(0.906, 0.189, fx('FX_PC0010_SAttack_Slash_01'), 'Trans', loc=(60, 0, 100), rot=(0, 0, 0))
    # ---- his hold Square (PC0010_NPAtk_1: B_NPAttack01 on the ground, B_NPAttackJ01 in the air): Ichijin, each of its
    # two slashes loosing one of Bizarro Sephiroth's Zanshin waves (PC0010_RM_NPAtk_1_01, the right one, then _02, the
    # left, in the order Bizarro's own Zanshin looses them), with the gameplay notifies of his own hold Square there
    for key, notes in (('B_NPAttack01', 'Ichijin: dash, two slashes, a Zanshin wave each'),
                       ('B_NPAttackJ01', 'Ichijin in the air: two slashes, a Zanshin wave each')):
        m = add(Move('Battle08', key, S0 + 'B_AtkIchijin02', P + key, notes=notes))
        m.hit(0.50, 0.22, 'PC0010_RM_NPAtk_1_01')
        m.hit(0.96, 0.12, 'PC0010_RM_NPAtk_1_02')
        m.remake_sounds(N, 'Battle00/B_AtkIchijin02')
        m.remake_trails(N, 'Battle00/B_AtkIchijin02')
        m.effect(0.478, 0.189, fx('FX_PC0010_SAttack_Slash_01'), 'Trans', loc=(60, 0, 120), rot=(0, 0, 70))
        m.effect(0.934, 0.189, fx('FX_PC0010_SAttack_Slash_01'), 'Trans', loc=(60, 0, 120), rot=(0, 0, 210))

    # ---- casting: his spells (B_MagAttack01) and the casts of his forms' abilities (B_AtkMag01) -----------------------
    for i in range(3):
        for key, nf in (('B_MagAttack01_%d' % i, P + 'B_MagAttack01_%d' % i), ('B_AtkMag01_%d' % i, T + 'B_AtkMag01_%d' % i)):
            m = add(Move('Battle08', key, S0 + 'B_AtkMagic01_%d' % i, nf, notes='Remake\'s casting'))
            if i == 2:
                m.hit(0.37)
            m.remake_sounds(N, 'Battle00/B_AtkMagic01_%d' % i)

    # ---- Octaslash (PC0010_RM_Octaslash): B_AtkHattou01 = _0 (its charge, faster), _1 (the dash), _2 (eight slashes) --
    m = add(Move('Battle08', 'B_AtkHattou01_0', S0 + 'B_AtkHattou01_0', T + 'B_AtkMag01_0', speed=1.5, notes='Octaslash: charge'))
    m.remake_sounds(N, 'Battle00/B_AtkHattou01_0')
    m.effect(0.887, 3.0 - 0.887, fx('FX_PC0010_Limit01_BodyAura_01'), 'Trans')
    m = add(Move('Battle08', 'B_AtkHattou01_1', S0 + 'B_AtkHattou01_1', T + 'B_AtkMag01_1', notes='Octaslash: dash'))
    m.remake_sounds(N, 'Battle00/B_AtkHattou01_1')
    m.effect(0.0, 0.77, fx('FX_PC0010_Limit01_BodyAura_01'), 'Trans')
    m = add(Move('Battle08', 'B_AtkHattou01_2', S0 + 'B_AtkHattou01_2', P + 'B_AtkLimit01_0', notes='Octaslash: eight slashes'))
    for k, (t, w) in enumerate(damage_windows(N, 'Battle00/B_AtkHattou01_2'), 1):
        m.hit(t, w, 'PC0010_RM_Hattou_%02d' % k)
    m.remake_trails(N, 'Battle00/B_AtkHattou01_2', TRAIL_OCTA)
    slashes = [n for n in N['Battle00/B_AtkHattou01_2']['notifies'] if n['cls'] == 'AnimNotify_EndPlayParticleEffect'
               and 'WeaponSlash' in str(n['props'].get('m_PSTemplate'))]
    for (n, (loc, rot)) in zip(slashes, OCTA_SLASH):
        m.effect(n['time'], n['dur'], fx('FX_PC0010_Limit01_WeaponSlash_01'), 'Trans', loc=loc, rot=rot)
        m.sound(n['time'], 'FX_EB0021_AtkHattou_WeaponSlash_01')
    m.effect(2.784, 0.58, fx('FX_PC0010_Limit01_Finish_01'), 'Trans', loc=(300, 0, 0))
    m.effect(0.0, 2.9, fx('FX_PC0010_Limit01_BodyAura_01'), 'Trans')

    # ---- Scintilla (PC0010_RM_Scintilla): Remake's B_AtkSenkou02, its flash through the enemy and a storm of slashes ---
    m = add(Move('Battle08', 'B_AtkSenkou02', S0 + 'B_AtkSenkou02', P + 'B_AtkBurst01_0', notes='Scintilla'))
    for k, t in enumerate([0.07, 1.41, 1.53, 1.65, 1.77, 1.89], 1):
        m.hit(t, 0.10, 'PC0010_RM_Senkou_%02d' % k)
    m.remake_sounds(N, 'Battle00/B_AtkSenkou02')
    m.remake_trails(N, 'Battle00/B_AtkSenkou02')
    m.effect(1.59, 0.6, fx('FX_PC0010_Limit01_SlashStorm_01'), 'Trans', loc=(150, 0, 100))
    m.effect(1.59, 0.196, fx('FX_PC0010_SAttack_Slash_01'), 'Trans', loc=(60, 0, 120), rot=(0, 0, 70))

    # ---- Shadow Flare (PC0010_RM_ShadowFlare, T_ShadowFlare's flow): B_AtkSFlare01_0 (raise), _1 (charge), _2 (orbs) --
    def flare(set_, srcset, src, nf_i, hits, clip=None):
        m = add(Move(set_, 'B_AtkSFlare01_%d' % nf_i, srcset + src, T + 'B_AtkMag01_%d' % nf_i, clip=clip, notes='Shadow Flare %d' % nf_i))
        for t in hits:
            m.hit(t)
        name = ('Battle01/' if srcset == S1 else 'Battle00/') + src
        m.remake_sounds(N, name)
        for n in N[name]['notifies']:
            if n['cls'] == 'AnimNotify_EndPlayParticleEffect' and 'SFlare_Charge' in str(n['props'].get('m_PSTemplate')):
                m.effect(n['time'], n['dur'], fx('FX_PC0010_10_ShadowFlare_Charge_01'), 'VFX_Magic02')
        return m
    flare('Battle08', S0, 'B_AtkSFlare01_0', 0, [])
    flare('Battle08', S0, 'B_AtkSFlare01_1', 1, [])
    flare('Battle08', S0, 'B_AtkSFlare01_2', 2, [0.17, 0.25, 0.33, 0.41])
    # (winged: Remake's sixteen-orb Shadow Flare of the winged phase)
    flare('Battle09', S1, 'B_AtkSFlare02_0', 0, [])
    flare('Battle09', S1, 'B_AtkSFlare02_1', 1, [])
    flare('Battle09', S1, 'B_AtkSFlare02_2', 2, [t for t, _ in damage_windows(N, 'Battle01/B_AtkSFlare02_2')], clip=(0.0, 7.2))

    # ---- Hell's Gate (PC0010_RM_HellsGate): B_AtkGokumon01 = _0 (crouch), _1 (the leap), _2 (the plunge, cut where he
    # reaches the ground), _4 (the impact and the shockwave) -------------------------------------------------------------
    m = add(Move('Battle08', 'B_AtkGokumon01_0', S0 + 'B_AtkGokumon01_0', T + 'B_AtkMag01_0', notes='Hell\'s Gate: crouch'))
    m.remake_sounds(N, 'Battle00/B_AtkGokumon01_0')
    m = add(Move('Battle08', 'B_AtkGokumon01_1', S0 + 'B_AtkGokumon01_1', T + 'B_AtkMag01_1', notes='Hell\'s Gate: leap'))
    m.remake_sounds(N, 'Battle00/B_AtkGokumon01_1')
    m = add(Move('Battle08', 'B_AtkGokumon01_2', S0 + 'B_AtkGokumon01_2', T + 'B_AtkMag01_1', clip=(0.0, 0.62), notes='Hell\'s Gate: plunge'))
    m.remake_sounds(N, 'Battle00/B_AtkGokumon01_2')
    m.trail(0.25, 0.37)
    m = add(Move('Battle08', 'B_AtkGokumon01_4', S0 + 'B_AtkGokumon01_4', P + 'B_AtkBurst02_0', notes='Hell\'s Gate: impact'))
    m.hit(0.17, 0.25, 'PC0010_RM_Gokumon_01')
    m.hit(0.94, 0.45, 'PC0010_RM_Gokumon_02')
    m.remake_sounds(N, 'Battle00/B_AtkGokumon01_4')
    m.effect(0.119, 1.48, fx('FX_PC0010_Burst02_SwordImpact_01'), 'Trans', loc=(100, 0, 0))
    m.effect(0.94, 0.5, fx('FX_PC0010_Burst01_Shokwave_01'), 'Trans')

    # ---- Heartless Angel (PC0010_T_HeartlessAngel as it is): B_AtkTenshi01_0 / _1 -------------------------------------
    def angel(set_, srcset, clip_end, hits):
        name0 = ('Battle01/' if srcset == S1 else 'Battle00/') + 'B_AtkTenshi01_0'
        name1 = ('Battle01/' if srcset == S1 else 'Battle00/') + 'B_AtkTenshi01_1'
        m = add(Move(set_, 'B_AtkTenshi01_0', srcset + 'B_AtkTenshi01_0', T1 + 'B_AtkTenshi01_0', notes='Heartless Angel: rise'))
        m.remake_sounds(N, name0)
        m = add(Move(set_, 'B_AtkTenshi01_1', srcset + 'B_AtkTenshi01_1', T1 + 'B_AtkTenshi01_1', clip=(0.0, clip_end), notes='Heartless Angel'))
        for (t, w), dmg in zip(hits, ('PC0010_T_HeartlessAngel_01', 'PC0010_T_HeartlessAngel_02')):
            m.hit(t, w, dmg)
        m.remake_sounds(N, name1)
        m.effect(0.0, 1.6, fx('FX_PC0010_10_Tenshi_Charge_01'), 'Trans')
        m.effect(1.62, 1.71, fx('FX_PC0010_10_Tenshi_Hit_01'), 'C_Body_a', loc=(200, 0, 0), rot=(180, 0, 0))
    angel('Battle08', S0, 6.6, damage_windows(N, 'Battle00/B_AtkTenshi01_1'))
    angel('Battle09', S1, 8.0, damage_windows(N, 'Battle01/B_AtkTenshi01_1'))
    return moves


# the JSON's animation for each key of each pack: the built move, or (Battle09) Battle08's of the same key, or a chain
def key_animations(moves):
    built = {(m.set, m.key): '%s/%s/%s.%s' % (BUILD, m.set, m.key, m.key) for m in moves}
    out = {'Battle08': {}, 'Battle09': {}}
    for (s, k), path in built.items():
        out[s][k] = path
    for k, path in list(out['Battle08'].items()):
        out['Battle09'].setdefault(k, path)
    for s in out:
        out[s]['B_AtkHattou01'] = [out[s]['B_AtkHattou01_%d' % i] for i in range(3)]
        out[s]['B_AtkGokumon01'] = [out[s]['B_AtkGokumon01_%d' % i] for i in (0, 1, 2, 4)]
    return out


if __name__ == '__main__':
    N = load(sys.argv[1])
    moves = plan(N)
    keys = key_animations(moves)
    json.dump({'moves': [m.json() for m in moves], 'keys': keys}, open(sys.argv[2], 'w'), indent=1)
    for m in moves:
        print('%-9s %-18s <- %-26s nf %-28s hits %-2d extras %-2d%s' % (m.set, m.key, m.src.rsplit('/', 1)[1], m.nf.rsplit('/', 1)[1],
                                                                       len(m.hits), len(m.extras), (' clip %s' % (m.clip,)) if m.clip else ''))
