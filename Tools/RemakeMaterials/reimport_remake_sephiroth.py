# Re-imports Remake Sephiroth's three models in the open End editor (no restart) from the FBX files in
# _build\remake_models, and puts his material instances back on their slots: import_remake_sephiroth.py, without
# closing the editor afterwards. Closes those meshes' editor tabs first.
# In the editor: Output Log > Cmd:  py "C:/FF7R2UProj/Tools/RemakeMaterials/reimport_remake_sephiroth.py"
# Results: Saved\RemakeMaterials\sephiroth_result.json
import os
import runpy
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
MESHES = ['/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00',
          '/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Body',
          '/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Wing']

# (replacing a mesh under its own open editor tab can take the editor down)
closed = 0
try:
    sub = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    for path in MESHES:
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            asset = unreal.load_asset(path)
            if asset is not None:
                closed += sub.close_all_editors_for_asset(asset)
except Exception as ex:
    unreal.log_warning('REMAKESEPH could not close the mesh editor tabs: %s' % ex)
unreal.log('REMAKESEPH re-import in the open editor: closed %d mesh editor tab(s)' % closed)
os.environ['REMAKESEPH_QUIT'] = '0'
runpy.run_path(os.path.join(HERE, 'import_remake_sephiroth.py'), run_name='__main__')
