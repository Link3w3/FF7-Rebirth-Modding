import sys, os, struct, shutil
sys.path.insert(0, '/work/charaspecmod'); sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
from build_charaspec import rebuild
from iostore_write import write_container, container_header, package_id, container_id_from_name
from iostore import Toc
from zen import Zen
import zenrename

def wstr(s): return (s + '\0').encode('utf-16-le')

def cloud_to_vincent(keys, fields, rows):
    fi = {f[0][0]: i for i, f in enumerate(fields)}
    row = rows[keys.index(('PC0000_00_Cloud_Standard', 0))]
    row[fi['ContentsModel']] = ('PC0011_00_Vincent_Standard', 0)
    row[fi['AnimationSetParentFolder']] = ('PC0011_Vincent', 0)
    row[fi['AnimationSetList_Array']] = [('Battle00', 0), ('Neutral00', 0), None, None, ('Facial00', 0)]
    row[fi['OverrideAnimationSetString_Array']] = []
    row[fi['SharedCharaSpecList_Array']] = [('PC0011_00_Vincent_Standard', 0)]
    row[fi['EquipmentCharaSpecList_Array']] = [('WE0011_00_Vincent_Quiksilver', 0)]
    row[fi['OverrideWeaponSocketNames_Array']] = [('Attach_Weapon_Right02', 0)]
    row[fi['NoBattleCharaSpec']] = ('PC0000_00_Cloud_Standard', 0)
    row[fi['ReserveCharaSpec']] = ('PC0000_00_Cloud_Standard', 0)
    row[fi['ContentsSoundAutoSE_Array']] = [wstr('AS_PC0011_00_Vincent_Standard')]

OUT = '/work/charaspecmod/out2'
os.makedirs(OUT, exist_ok=True)
dataobject, _ = rebuild(cloud_to_vincent)
open(os.path.join(OUT, 'CharaSpec.uasset'), 'wb').write(dataobject)

# Cloud's per-character data asset, with Vincent's content (its entries are named after the row's ContentsModel).
vin = open('/work/gameextract/CharaSpec_PC0011_00_Vincent_Standard.uasset', 'rb').read()
cloud = open('/work/gameextract/CharaSpec_PC0000_00_Cloud_Standard.uasset', 'rb').read()
cloud_global = Zen(cloud).exports[0]['global_import']
asset = zenrename.rebuild(vin, {
    '/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0011_00_Vincent_Standard': '/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard',
    'CharaSpec_PC0011_00_Vincent_Standard': 'CharaSpec_PC0000_00_Cloud_Standard'}, {0: cloud_global})
open(os.path.join(OUT, 'CharaSpec_PC0000_00_Cloud_Standard.uasset'), 'wb').write(asset)
za = Zen(asset)
print('data asset:', len(asset), 'names', [n for n in za.names if 'CharaSpec' in n or n.endswith('_Class') or n.endswith('_Data')], 'export', za.exports[0]['name'], '%016x' % za.exports[0]['global_import'])
asset_imports = zenrename.graph_imports(asset)
print('data asset imports', ['%016x' % x for x in asset_imports])

NAME = 'VincentReplacesCloud_Test_P'
pid_do = package_id('/Game/DataObject/Resident/CharaSpec')
pid_da = package_id('/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard')
assert pid_da == 0xefb01e22a1c82bd2, '%016x' % pid_da
cid = container_id_from_name(NAME)
hdr = container_header(cid, [
    dict(id=pid_do, size=len(dataobject), export_count=1, export_bundle_count=1, imports=[], load_order=0),
    dict(id=pid_da, size=len(asset), export_count=1, export_bundle_count=1, imports=asset_imports, load_order=1)])
chunks = [dict(id64=pid_do, type=2, data=dataobject, path='DataObject/Resident/CharaSpec.uasset'),
          dict(id64=pid_da, type=2, data=asset, path='DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.uasset'),
          dict(id64=cid, type=10, data=hdr, path=None)]
base = os.path.join(OUT, NAME)
write_container(base, NAME, chunks)
shutil.copy('/work/vincentmod/FullyPlayableVincentAssets_P.pak', base + '.pak')
t = Toc(base + '.utoc')
print('container %016x flags %d entries %d files %s' % (t.container_id, t.flags, t.entries, t.files))
for i in range(t.entries):
    d = t.read(i)
    print(i, '%016x' % t.chunk_id64(i), 'type', t.chunk_type(i), len(d), 'same' if d == chunks[i]['data'] else 'DIFFERENT')
for f in sorted(os.listdir(OUT)): print(f, os.path.getsize(os.path.join(OUT, f)))
