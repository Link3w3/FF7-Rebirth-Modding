import sys, os, shutil, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))           # the fake unreal
sys.path.insert(1, '/work/fx1018/editor/Python')
import unreal
from rebirth_fx import iostore_write as W, matcore
pk = '/Game/Character/Player/PC0000_00_Cloud_Standard/Material/PC0000_00_TopsA'
data = open('/work/fx1018/pkgs/Character__Player__PC0000_00_Cloud_Standard__Material__PC0000_00_TopsA.uasset', 'rb').read()
par = '/Game/Renderer/MaterialInstance/Surface/RMI_Surface_Fabric_Wide'
unreal.GAME[pk] = data
# the parent is not in the editor; its game package says RM_Surface is its parent: fake one with a tiny MI (reuse TopsA's bytes is not a parent...)
# the editor has RM_Surface:
unreal.ASSETS['/Game/Renderer/Material/RM_Surface'] = unreal.Material('/Game/Renderer/Material/RM_Surface.RM_Surface',
    scalars=['RefractionDepthBias', 'EmissiveIntensity'], vectors=['BaseColorTint'], textures=['Color', 'Normal', 'Roughness', 'Diffusion', 'WideOcclusion'])
mi = matcore.MaterialInstance(data, 'TopsA')
graph = [g for g, a in matcore.graph_packages(data)]
hdr = W.container_header(1234, [dict(id=W.package_id(pk), size=len(data), export_count=1, export_bundle_count=1, imports=graph, load_order=7)])
unreal.HEADERS[pk] = hdr
# the parent package: give the game a fake one whose parent is RM_Surface (edit TopsA's parent import to RM_Surface for the test)
unreal.GAME[par] = data   # (its parent resolves to RMI_Surface_Fabric_Wide again; load_asset fails -> chain stops after 6)
unreal.HEADERS[par] = hdr
from rebirth_fx import materials as M
m = M.open_material(pk)
print('manifest parent', m['parent'], 'editor parent', m['editor_parent'], 'chain', m['chain'][:2])
print('names', m['names'])
print('baseline', m['baseline'])
mic = unreal.load_asset(m['asset'])
# the user edits: a new tint, a scalar, a texture swap to a game texture the package does not import
mic.vectors['BaseColorTint'] = unreal.LinearColor(0.2, 0.4, 1.0, 1.0)
mic.scalars['EmissiveIntensity'] = 3.0
unreal.ASSETS['/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Body_C'] = unreal.Obj('/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Body_C.PC0010_00_Body_C')
mic.textures['Color'] = unreal.ASSETS['/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Body_C']
print('changes', M._changes(m))
files = M.export_to_game()
print(files)
from rebirth_fx import fxcore
pk2, hdr2 = fxcore.read_container(files[0])
for k, v in pk2.items():
    mi2 = matcore.MaterialInstance(v, 'x')
    print([(p['kind'], p['name'], p['value']) for p in mi2.params])
from rebirth_fx.hdr import parse_header
cid, ents = parse_header(hdr2)
e = list(ents.values())[0]
print('entry imports', len(e['imports']), 'graph', len(matcore.graph_packages(list(pk2.values())[0])), 'size', e['size'])
# live: the change goes to the game as a material_params command
mod = os.path.join(unreal.ROOT, 'Game', 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthLiveLink', 'link')
os.makedirs(mod, exist_ok=True)
import json, time
open(os.path.join(mod, 'status.json'), 'w').write(json.dumps({'seq': 10**15, 'version': '1.2'}))
M.toggle_live()
mic.scalars['RefractionDepthBias'] = 0.25
M._state['next_check'] = 0
M._live_tick(0.1)
print(open(os.path.join(mod, 'command.lua')).read()[:600])
