import os
import unreal

saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
out = os.path.join(saved, 'RebirthMatExport', 'Materials__AnimeShaderEye')
m = unreal.load_asset('/Game/Shader/KadeMats/Materials/AnimeShaderEye')
lib = getattr(unreal, 'RebirthFxLinkLibrary', None) or getattr(unreal, 'RebirthFxLibrary')
r = lib.export_material_for_game(m, out)
files = {f: os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)} if os.path.isdir(out) else {}
result = dict(answer=str(r), dir=out, files=files)
