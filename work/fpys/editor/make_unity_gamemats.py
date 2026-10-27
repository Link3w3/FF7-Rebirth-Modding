# His Unity materials (mat_ch049_001_* on M_UnityToon) and the Nameless's WE1021_49_Mat00 made game materials with the
# Game Materials converter (rebirth_fx.gamematerials), not installed: the report, and what the mod holds.
import unreal, json
import rebirth_fx.gamematerials as gm
U = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed/Material/Unity/'
paths = [U + 'mat_ch049_001_%s.mat_ch049_001_%s' % (n, n) for n in ('body', 'head', 'hair', 'hair_tp', 'eyelash', 'eye_shadow', 'eye')] + \
        ['/Game/Character/Weapon/WE1021_49_Nameless/Material/WE1021_49_Mat00.WE1021_49_Mat00']
r = gm.make(paths, install=False, quiet=True)
result = json.dumps(r, indent=1, default=str)
