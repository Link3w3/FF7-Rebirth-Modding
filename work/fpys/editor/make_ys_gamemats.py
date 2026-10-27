# Young Sephiroth's Unity materials (body, head, hair, hair_tp, eye: mat_ch049_001_* on M_UnityToon) and the Nameless's
# WE1021_49_Mat00 made game materials with the Game Materials converter (rebirth_fx.gamemat.convert, reloaded), into a
# mod of their own, YoungSephirothMaterials_P (its own store: the user's RebirthGameMaterials_P store is not touched).
# His eyelash and eye shadow (translucent Unity materials, which the converter cannot carry) get his game-native
# PC0010_13_Eyelash / _EyeShadow instead (same textures). Not installed.
import unreal, json, os, importlib, traceback
import rebirth_fx.gamemat.convert as convert
importlib.reload(convert)
import rebirth_fx.gamematerials as gm
importlib.reload(gm)
from rebirth_fx.gamemat import env
env.vendor()
U = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed/Material/Unity/'
paths = [U + 'mat_ch049_001_%s.mat_ch049_001_%s' % (n, n) for n in ('body', 'head', 'hair', 'hair_tp', 'eye')] + \
        ['/Game/Character/Weapon/WE1021_49_Nameless/Material/WE1021_49_Mat00.WE1021_49_Mat00']
native = gm._native()
game = convert.GameData(native)
editor = gm._Editor(native)
conv = convert.Converter(game, editor)
env.dxc()
game.library()
store = convert.Store()
store.root = env.work('made_fpys')
store.manifest_path = os.path.join(store.root, 'manifest.json')
store.manifest = {}
made, failed = [], []
for p in paths:
    try:
        packages, info = conv.convert(p)
        store.put(p, packages, info)
        made.append(dict(material=p.rsplit('.', 1)[-1], kind=info['kind'], carrier=info['carrier'], textures=len(info['textures']),
                         missing=info.get('missing'), shading=info.get('shading_models'), blend=info.get('blend')))
    except Exception as e:
        failed.append((p.rsplit('.', 1)[-1], traceback.format_exc()[-1500:]))
out = {'made': made, 'failed': failed}
if made and not failed:
    convert.MOD_NAME = 'YoungSephirothMaterials_P'
    try:
        mod_paths, entries, notes = convert.build_mod(store, game, editor.cook, out_dir=env.work('mod_fpys'))
        out['mod'] = mod_paths
        out['notes'] = [n[-400:] for n in notes]
    except Exception:
        out['build_error'] = traceback.format_exc()[-2000:]
    finally:
        convert.MOD_NAME = 'RebirthGameMaterials_P'
# his translucent two: the game-native instances
YS = '/Game/Character/Player/PC0010_13_Young_Sephiroth/'
sm = unreal.load_asset(YS + 'Model/PC0010_13')
mats = sm.get_editor_property('materials')
for i in range(len(mats)):
    m = mats[i]
    slot = str(m.get_editor_property('material_slot_name'))
    if slot in ('mat_ch049_001_eyelash', 'mat_ch049_001_eye_shadow'):
        m.set_editor_property('material_interface', unreal.load_asset(YS + 'Material/PC0010_13_' + ('Eyelash' if 'lash' in slot else 'EyeShadow')))
        mats[i] = m
sm.set_editor_property('materials', mats)
sm.modify()
unreal.EditorAssetLibrary.save_loaded_asset(sm, False)
out['slots'] = {str(m.get_editor_property('material_slot_name')): m.get_editor_property('material_interface').get_path_name().split('.')[0].rsplit('/', 1)[-1]
                for m in unreal.load_asset(YS + 'Model/PC0010_13').get_editor_property('materials')}
result = json.dumps(out, indent=1, default=str)
