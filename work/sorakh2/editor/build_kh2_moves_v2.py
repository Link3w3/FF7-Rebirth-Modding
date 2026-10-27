# Sora's KH2 moves v2 (swing sounds at the hits; built into Built/SoraKH2v2, the v1 build is left as it is), step 2: a Create a Character System data object (new: /Game/RebirthSkelCompat/SoraKH2/DO_SoraKH2)
# whose one animation set row builds his Operator-mode (Battle00) ground and air combos and battle idle from his KH2
# animations (Imported/KH2Sora, 60 fps, ACL), each with Cloud's gameplay notifies of the same name lined up on the KH2
# swing (Build Move Animations, the no-dialog version of Build Moves). Built into /Game/RebirthSkelCompat/Built/SoraKH2.
# No chunk label (Build Chunk 0), nothing else in the project changes. Writes Saved/ModExtract/sorakh2/build_report.txt.
import unreal, json, os
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'ModExtract', 'sorakh2')
DO_PATH = '/Game/RebirthSkelCompat/SoraKH2/DO_SoraKH2'
KH2 = '/Game/RebirthSkelCompat/Imported/KH2Sora/'
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/'
SKEL = '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_Skeleton.PC0000_00_S_Skeleton'
BUILD = '/Game/RebirthSkelCompat/Built/SoraKH2v2'
BANK = '/Game/Sound/SE/Character/Weapon/SE_WE0000_00_BusterSword.SE_WE0000_00_BusterSword'
MOVES = [  # Cloud's name, KH2 animation, hits (s, in the KH2 move at 60 fps; each with the swing sound Cloud's move plays)
    ('B_NAttack01_0', 'KH2_1301', [(0.15, 'se_B_NAttack01_0')]),        # lunge, overhead slash
    ('B_NAttack02_0', 'KH2_1302', [(0.33, 'se_B_NAttack02_0')]),        # lunge, low thrust then upward slash
    ('B_NAttack03_0', 'KH2_1303', [(0.28, 'se_B_NAttack03_0')]),        # spinning sweep
    ('B_NAttack04_0', 'KH2_1319', [(0.16, 'se_B_NAttack04_0')]),        # lunging horizontal slash
    ('B_NAttack05_0', 'KH2_1304', [(0.26, 'se_B_NAttack05_0')]),        # finisher: leap and slam
    ('B_NAttackJ01_0', 'KH2_1311', [(0.12, 'se_B_NAttack01_0')]),       # air: downward slash
    ('B_NAttackJ02_0', 'KH2_1312', [(0.13, 'se_B_NAttack02_0')]),       # air: overhead slash
    ('B_NAttackJ03_0', 'KH2_1313', [(0.12, 'se_B_NAttack03_0')]),       # air: horizontal spin
    ('B_NAttackJ04_0', 'KH2_1314', [(0.28, 'se_B_NAttack01_0'), (0.69, 'se_B_NAttack04_0')]), # air finisher: spinning slashes
    ('B_Idle01_1', 'KH2_1015', []),               # KH2 battle stance
]


def setp(obj, names, value):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return name
        except Exception as ex:
            last = ex
    raise last


def soft(path):
    try:
        return unreal.SoftObjectPath(path)
    except Exception:
        return unreal.EditorAssetLibrary.load_asset(path)


out = {}
if unreal.EditorAssetLibrary.does_asset_exist(DO_PATH):
    data = unreal.EditorAssetLibrary.load_asset(DO_PATH)
    out['data_object'] = 'loaded'
else:
    folder, name = DO_PATH.rsplit('/', 1)
    data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.EndSkeletonCompatDataObject, None)
    out['data_object'] = 'created'
row = unreal.EndAnimSetRow()
setp(row, ['enabled', 'b_enabled'], True)
setp(row, 'characters', ['PC0000_00_Cloud_Standard'])
src = unreal.EndAnimSetSource()
setp(src, 'path', '/Game/Motion/Player/PC0000_00_Sora_KH2')
setp(row, 'battle', [src])
skel = unreal.EditorAssetLibrary.load_asset(SKEL)
try:
    setp(row, 'character_skeleton', skel)
except Exception:
    setp(row, 'character_skeleton', soft(SKEL))
setp(row, 'build_folder', BUILD)
moves = []
for key, anim, hits in MOVES:
    m = unreal.EndAnimSetMove()
    setp(m, 'name', key)
    setp(m, 'set', 'Battle00')
    setp(m, 'animation', KH2 + anim + '.' + anim)
    setp(m, ['build', 'b_build'], True)
    setp(m, 'notifies_from', CLOUD + key + '.' + key)
    hl = []
    for t, cue in hits:
        h = unreal.EndMoveHit()
        setp(h, 'time', float(t))
        setp(h, 'sound_bank', BANK)
        setp(h, 'sound', cue)
        hl.append(h)
    setp(m, 'hits', hl)
    setp(m, ['keep_source_effects', 'b_keep_source_effects'], True)
    moves.append(m)
setp(row, 'moves', moves)
setp(data, 'animation_sets', [row])
setp(data, 'build_chunk', 0)
out['saved_data_object'] = unreal.EditorAssetLibrary.save_loaded_asset(data, False)
r = data.build_move_animations()
out['build'] = r if isinstance(r, (str, bool)) else [str(x) for x in r]
text = '\n'.join(str(x) for x in (r if isinstance(r, (list, tuple)) else [r]))
open(os.path.join(OUT, 'build_report_v2.txt'), 'w', encoding='utf-8').write(text)
reg = unreal.AssetRegistryHelpers.get_asset_registry()
out['built'] = sorted(str(a.object_path) for a in reg.get_assets_by_path(BUILD, recursive=True))
result = json.dumps(out, indent=1)[-8000:]
