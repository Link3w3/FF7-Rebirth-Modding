# Sora's KH2 moves, step 3: the 10 built moves cooked for the game (no blend space uses them).
import unreal
B = '/Game/RebirthSkelCompat/Built/SoraKH2/Battle00/'
names = ['B_NAttack01_0', 'B_NAttack02_0', 'B_NAttack03_0', 'B_NAttack04_0', 'B_NAttack05_0',
         'B_NAttackJ01_0', 'B_NAttackJ02_0', 'B_NAttackJ03_0', 'B_NAttackJ04_0', 'B_Idle01_1']
pk = [B + n for n in names]
r = unreal.EndSkeletonCompatDataObject.cook_packages_for_game(pk, r'C:\FF7R2UProj\Saved\ModExtract\soracook_kh2a\End\Content')
result = r[-3000:]
