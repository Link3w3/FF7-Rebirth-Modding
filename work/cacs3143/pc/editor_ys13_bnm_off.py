# Young Sephiroth on KawaiiPhysics only (Create a Character System 3.14.0): his model PC0010_13 in the End project without
# its two BNMs (Asset User Data > SQEX_KBD_AssetUserData > Bonamik Data List emptied: PC0010_13_BNM, his body's, and
# PC0010_13_Wing_BNM, his wing's), its KDI kept (Kine Driver Data List: PC0010_13_KDI), as YoungSephiroth_P's cooked
# copy has it now. The BNM assets themselves stay in the project. Saves the mesh; refuses when it has unsaved changes.
import unreal, json

EAL = unreal.EditorAssetLibrary
MESH = '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13'
out = {'mesh': MESH}
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
assert MESH not in dirty, 'the model has unsaved changes: save or revert them first (nothing changed)'
mesh = unreal.load_asset(MESH)
assert mesh is not None, 'the model is not in the project'
kbds = [d for d in (mesh.get_editor_property('asset_user_data') or []) if d is not None and isinstance(d, unreal.SQEX_KBD_AssetUserData)]
assert len(kbds) == 1, '%d SQEX_KBD_AssetUserData on the model (expected one)' % len(kbds)
kbd = kbds[0]
before = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
kdis = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('KineDriverDataList') or []) if d is not None]
out.update(bonamik_before=before, kdi=kdis, others_dirty=dirty)
if before:
    mesh.modify()
    kbd.modify()
    kbd.set_editor_property('BonamikDataList', [])
    after = [d for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
    assert not after, 'the list did not empty'
    kept = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('KineDriverDataList') or []) if d is not None]
    assert kept == kdis, 'the KDI list changed'
    assert EAL.save_loaded_asset(mesh, False), 'could not save ' + MESH
    out['action'] = 'emptied its Bonamik list and saved the model'
else:
    out['action'] = 'its Bonamik list was empty already'
out['bonamik_after'] = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
out['kdi_after'] = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('KineDriverDataList') or []) if d is not None]
result = out
