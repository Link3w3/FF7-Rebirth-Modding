import unreal, json, os
B = '/Game/Motion/Player/PC0000_Cloud/Battle00/'
names = ['B_NAttack01_0','B_NAttack01_1','B_NAttack01_1_0','B_NAttack01_1_1','B_NAttack01_1_2','B_NAttack02_0','B_NAttack03_0','B_NAttack04_0','B_NAttack05_0','B_NAttack06_0','B_NAttack07_0','B_NAttack07_1','B_NAttack07_2','B_NAttack20_0',
         'B_NAttackJ01_0','B_NAttackJ02_0','B_NAttackJ03_0','B_NAttackJ04_0','B_NAttackJ05_0','B_NAttackJ05_1','B_NAttackJ05_2','B_AAttack01_0','B_AAttack01_1','B_WAttack01_0','B_WAttack02_0',
         'B_Ability01_0','B_Ability01_1','B_Ability01_2','B_Ability02_0','B_Ability02_1','B_Ability02_2','B_Ability03_0','B_Ability03_1','B_Ability03_2','B_Ability04_0','B_Ability04_1','B_Ability04_2','B_Ability05_0','B_Ability06_0','B_Ability06_1','B_Ability06_2',
         'B_AtkBurst01_0','B_AtkBurst02_0','B_AtkBurst04_0','B_AtkBurst05_0','B_AtkBurst09_0','B_AtkBurst07_0','B_AtkBurst07_1','B_AtkBurst08_0','B_AtkBurst08_1','B_AtkBurst08_2','B_AtkBurst10_0','B_AtkBurst06_0','B_AtkBurstJ01_0','B_AtkBurstJ06_0',
         'B_AtkLimit01_0','B_AtkLimit02_0','B_AtkLimit03_0','B_Avoid01','B_Avoid02','B_AvoidJ01','B_Jump01_0','B_Fall01_1','B_Fall01_2','B_Fall01_3','B_Guard01_0','B_Guard01_1','B_Guard01_2']
d = unreal.EndSkeletonCompatDataObject.describe_animations([B + n + '.' + n for n in names])
open(os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'sorarig', 'cloud_attacks_describe.json'), 'w', encoding='utf-8').write(d)
result = len(d)
