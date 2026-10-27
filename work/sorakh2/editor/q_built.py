import unreal, os
B = '/Game/RebirthSkelCompat/Built/SoraKH2/Battle00/'
names = ['B_NAttack01_0', 'B_NAttack02_0', 'B_NAttack03_0', 'B_NAttack04_0', 'B_NAttack05_0',
         'B_NAttackJ01_0', 'B_NAttackJ02_0', 'B_NAttackJ03_0', 'B_NAttackJ04_0', 'B_Idle01_1']
d = unreal.EndSkeletonCompatDataObject.describe_animations([B + n + '.' + n for n in names])
open(os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'sorakh2', 'built_describe.json'), 'w', encoding='utf-8').write(d)
result = len(d)
