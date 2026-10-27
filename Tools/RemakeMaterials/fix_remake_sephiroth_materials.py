# Puts Sephiroth's Remake material instances on his models' slots, by slot name (the import left the slots empty:
# it changed copies of the slot list). Safe to run in the open End editor:
#   Output Log, Cmd:  py "C:/FF7R2UProj/Tools/RemakeMaterials/fix_remake_sephiroth_materials.py"
import unreal

EAL = unreal.EditorAssetLibrary
STD = '/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard'
TRN = '/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform'
MESHES = [(STD + '/Model/EB0021_00', STD + '/Material'),
          (TRN + '/Model/EB0021_01_Body', TRN + '/Material'),
          (TRN + '/Model/EB0021_01_Wing', TRN + '/Material')]


def assign(mesh_path, folder):
    sm = unreal.load_asset(mesh_path)
    if sm is None:
        return '%s: no mesh' % mesh_path
    mats = sm.get_editor_property('materials')
    done, missing = [], []
    for i in range(len(mats)):
        m = mats[i]                      # a copy: change it, then put it back
        slot = str(m.get_editor_property('material_slot_name'))
        path = '%s/%s' % (folder, slot)
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
        if mi is None:
            missing.append(slot)
            continue
        m.set_editor_property('material_interface', mi)
        mats[i] = m
        done.append(slot)
    sm.set_editor_property('materials', mats)
    sm.modify()
    EAL.save_loaded_asset(sm, False)
    # check what the asset now holds
    held = [str(x.get_editor_property('material_interface').get_name()) if x.get_editor_property('material_interface') else 'None'
            for x in sm.get_editor_property('materials')]
    return '%s: %d slots set %s%s' % (mesh_path.split('/')[-1], len(done), held, (' missing ' + ', '.join(missing)) if missing else '')


for mesh, folder in MESHES:
    try:
        unreal.log('REMAKESEPH fix: ' + assign(mesh, folder))
    except Exception as ex:
        unreal.log_error('REMAKESEPH fix failed for %s: %s' % (mesh, ex))
