# Remake Sephiroth skin, step 1: puts his model and Remake skeleton into their own cook chunk (61), so the next
# Package Project cooks them into pakchunk61-WindowsNoEditor (the skin's uassets are taken from there; don't install
# that chunk as a mod). Their materials are not needed from it: the game-ready ones are in your materials mod.
# In the editor: Output Log > Cmd:  py "C:/FF7R2UProj/Tools/CreateACharacterSkins/make_remake_skin_label.py"
import unreal

EAL = unreal.EditorAssetLibrary
FOLDER = '/Game/CreateACharacterSkins/RemakeSephiroth'
NAME = 'PAL_Skin_RemakeSephiroth_Chunk61'
CHUNK = 61
ASSETS = ['/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00',
          '/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton']

path = '%s/%s' % (FOLDER, NAME)
if EAL.does_asset_exist(path):
    label = unreal.load_asset(path)
else:
    factory = unreal.DataAssetFactory()
    factory.set_editor_property('data_asset_class', unreal.PrimaryAssetLabel)
    label = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, FOLDER, unreal.PrimaryAssetLabel, factory)
if label is None:
    raise RuntimeError('could not make ' + path)

assets = []
for p in ASSETS:
    a = unreal.load_asset(p) if EAL.does_asset_exist(p) else None
    if a is None:
        raise RuntimeError('no %s: import Remake Sephiroth first (run_import_remake_sephiroth.cmd)' % p)
    assets.append(a)

rules = label.get_editor_property('rules')
rules.set_editor_property('chunk_id', CHUNK)
rules.set_editor_property('priority', 1)
rules.set_editor_property('apply_recursively', True)
rules.set_editor_property('cook_rule', unreal.PrimaryAssetCookRule.ALWAYS_COOK)
label.set_editor_property('rules', rules)
label.set_editor_property('label_assets_in_my_directory', False)
label.set_editor_property('explicit_assets', assets)
EAL.save_loaded_asset(label, False)
unreal.log('REMAKESKIN %s: chunk %d with %s' % (path, CHUNK, ', '.join(a.get_name() for a in assets)))
