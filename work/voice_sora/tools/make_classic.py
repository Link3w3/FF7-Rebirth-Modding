"""Classic Sephiroth's voice bank (ClassicSephirothVoice_P, bank VO_PC0010_15_ClassicSephiroth): Sephiroth's own bank's
87 sounds (its cue names, volumes, categories and buses: the game's alias setting picks them as it does his), each given
a line of the Classic Sephiroth voice pack (a KH3 Battle_Sora project whose lines were replaced: 180 slots, 77 distinct
lines), chosen by what the slot was for in KH3 (attack shouts, damage, death, spells, heals, items) and by length,
resampled to the bank's 32 kHz and brought to the loudness of the line it stands in for.
    make_classic.py  ->  classic/<clip>.wav, classic/spec.txt, classic/mapping.txt"""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from math import gcd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'classic')
clips = {c['clip']: c for c in json.load(open(os.path.join(HERE, 'clips.json')))}
sounds = json.load(open(os.path.join(HERE, 'seph_sounds.json')))
RATE = 32000

# cue -> clip (None: silent, as the game's own sound for that cue is)
PLAN = {
    # Atk_Normal_01, Atk_Avoid_02: light grunts
    'bt021_001_001': 'C47', 'bt021_001_002': 'C49', 'bt021_001_003': 'C59', 'bt021_001_004': None,
    # Atk_Normal_02 (and the abilities' first efforts)
    'bt021_001_005': 'C12', 'bt021_001_006': 'C50', 'bt021_001_007': 'C55',
    # Atk_Normal_03, finishers, unique attacks
    'bt021_001_008': 'C14', 'bt021_001_009': 'C66', 'bt021_001_010': 'C10',
    'bt021_001_011': 'C40', 'bt021_001_012': 'C52', 'bt021_001_013': 'C64',
    # Atk_Ability_01 / _02: ability shouts
    'bt021_002_001': 'C11', 'bt021_002_002': 'C30', 'bt021_002_003': 'C36', 'bt021_002_004': 'C56', 'bt021_002_005': 'C70', 'bt021_002_006': 'C75',
    # Atk_Limit_01: limit break lines
    'bt021_003_001': 'C28', 'bt021_003_002': 'C29', 'bt021_003_003': 'C35',
    # Atk_Finish: finishing blows
    'bt021_003_004': 'C38', 'bt021_003_005': 'C25', 'bt021_003_006': 'C57',
    # Atk_Enemy_Down
    'bt021_003_007': 'C26', 'bt021_003_008': 'C31', 'bt021_003_009': 'C74',
    # Burst_Start: the enemy staggered
    'bt021_003_010': 'C27', 'bt021_003_011': 'C23', 'bt021_003_012': 'C32',
    # magic (every element), Atk_Normal_04, item_02, the combo support: the spell lines
    'bt021_004_001': 'C09', 'bt021_004_002': 'C16', 'bt021_004_003': 'C24', 'bt021_004_004': 'C13', 'bt021_004_005': 'C21', 'bt021_004_006': 'C22',
    # item_03, Field_Climb: items
    'bt021_005_001': 'C60', 'bt021_005_002': 'C61', 'bt021_005_003': 'C48', 'bt021_005_004': 'C51', 'bt021_005_005': 'C67',
    # Recover_04: healed
    'bt021_006_001': 'C46', 'bt021_006_002': 'C00', 'bt021_006_003': 'C73',
    # Damage_02 / _03 / _04 (and Dead_Self, the heavy ones)
    'bt021_021_001': 'C02', 'bt021_021_002': 'C06', 'bt021_021_003': 'C07',
    'bt021_021_004': 'C04', 'bt021_021_005': 'C05', 'bt021_021_006': 'C03',
    'bt021_021_007': 'C01', 'bt021_021_008': 'C04', 'bt021_021_009': 'C08',
    # Return_Dead: revived
    'bt021_021_010': 'C65', 'bt021_021_011': 'C45', 'bt021_021_012': 'C33',
    # Avoid_Start (and Field_Climb_End)
    'bt021_022_001': 'C71', 'bt021_022_002': 'C15', 'bt021_022_003': 'C13',
    # Guard_Success_01
    'bt021_022_004': 'C39', 'bt021_022_005': 'C63', 'bt021_022_006': 'C72',
    # Parry_01
    'bt021_022_007': 'C53', 'bt021_022_008': 'C58', 'bt021_022_009': 'C37',
    # Change_02: switched to him
    'bt021_031_001': 'C34', 'bt021_031_002': 'C43', 'bt021_031_003': 'C42',
    # Victory_01_Self / Victory_02_Dead
    'bt021_032_001': 'C76', 'bt021_032_002': 'C57', 'bt021_032_003': 'C32', 'bt021_032_004': 'C38', 'bt021_032_005': 'C35',
    # GameOver
    'bt021_033_001': 'C08', 'bt021_033_002': 'C65', 'bt021_033_003': 'C29',
    # (bt021_034: his own animations' notifies)
    'bt021_034_001': 'C17', 'bt021_034_002': 'C19',
    # Btl_Start_Monster_01: battle start
    'monS_21_SI_001': 'C25', 'monS_21_SI_002': 'C26', 'monS_21_SI_003': 'C28', 'monS_21_SI_004': 'C31', 'monS_21_SI_005': None,
    # the field's climbing efforts
    'Sep_wall_climb_01': 'C47', 'Sep_wall_climb_02': 'C59', 'Sep_wall_end_01': 'C49',
}

def cue(name):
    return name[:-6] if name.endswith('_sep_0') else name

def load(clip):
    f = os.path.join(HERE, 'wav', clips[clip]['files'][0])
    x, r = sf.read(f, dtype='float64', always_2d=True)
    x = x.mean(axis=1)
    g = gcd(RATE, r)
    return resample_poly(x, RATE // g, r // g) if r != RATE else x

def rms(x):
    loud = x[np.abs(x) > 10 ** (-40 / 20)]
    return float(np.sqrt(np.mean(loud ** 2))) if len(loud) else 0.0

os.makedirs(OUT, exist_ok=True)
missing = [cue(s['name']) for s in sounds if cue(s['name']) not in PLAN]
assert not missing, missing
# each clip once (its loudness: the mean of the original lines it stands in for)
targets = {}
for s in sounds:
    c = PLAN[cue(s['name'])]
    if c and s.get('orig_rms', 0) > 0:
        targets.setdefault(c, []).append(s['orig_rms'])
ids, lines, report = {}, [], []
silent_path = os.path.join(OUT, 'silent.wav')
sf.write(silent_path, np.zeros(int(0.2 * RATE)), RATE, subtype='FLOAT')
for c in sorted(set(v for v in PLAN.values() if v)):
    x = load(c)
    want = float(np.mean(targets.get(c, [0.19])))
    have = rms(x)
    gain = float(np.clip(want / have, 0.25, 4.0)) if have > 0 else 1.0
    y = x * gain
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    if peak > 0.97:
        y *= 0.97 / peak
    sf.write(os.path.join(OUT, c + '.wav'), y.astype(np.float32), RATE, subtype='FLOAT')
    report.append('%s %5.2fs gain %.2f (rms %.3f -> %.3f) from %s, KH3 %s' % (c, len(y) / RATE, gain, have, rms(y), clips[c]['files'][0], ','.join(sorted(clips[c]['cats'])) or '-'))
spec = ['container ClassicSephirothVoice_P', 'bank VO_PC0010_15_ClassicSephiroth', 'folder /Game/Sound/Voice/{language}/Character/Player',
        'alias /Game/Sound/Config/AliasSetting/VO_PC0010_00_Sephiroth', 'attenuation /Game/Sound/Config/Attenuation/player', 'kbps 85.25']
order = []
for s in sounds:
    c = PLAN[cue(s['name'])] or 'silent'
    if c not in ids:
        ids[c] = len(ids)
        order.append(c)
    path = silent_path if c == 'silent' else os.path.join(OUT, c + '.wav')
    spec.append('line %s volume=%r category=%d bus=%d US=%s JP=%s' % (s['name'], s['volume'], s['category'], s['bus'], path, path))
    report.append('  %-22s <- %s' % (s['name'], c))
open(os.path.join(OUT, 'spec.txt'), 'w').write('\n'.join(spec) + '\n')
open(os.path.join(OUT, 'mapping.txt'), 'w').write('\n'.join(report) + '\n')
print(len(sounds), 'sounds,', len(ids), 'materials')
