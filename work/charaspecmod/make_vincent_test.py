import sys, os, struct, shutil
sys.path.insert(0, '/work/charaspecmod'); sys.path.insert(0, '/work/iostore')
from build_charaspec import rebuild
from iostore_write import write_container, container_header, package_id, container_id_from_name
from iostore import Toc

def wstr(s): return (s + '\0').encode('utf-16-le')

def cloud_to_vincent(keys, fields, rows):
    fi = {f[0][0]: i for i, f in enumerate(fields)}
    row = rows[keys.index(('PC0000_00_Cloud_Standard', 0))]
    row[fi['ContentsModel']] = ('PC0011_00_Vincent_Standard', 0)
    row[fi['AnimationSetParentFolder']] = ('PC0011_Vincent', 0)
    row[fi['AnimationSetList_Array']] = [('Battle00', 0), ('Neutral00', 0), None, None, ('Facial00', 0)]
    row[fi['OverrideAnimationSetString_Array']] = []
    row[fi['EquipmentCharaSpecList_Array']] = [('WE0011_00_Vincent_Quiksilver', 0)]
    row[fi['OverrideWeaponSocketNames_Array']] = [('Attach_Weapon_Right02', 0)]
    row[fi['NoBattleCharaSpec']] = ('PC0011_00_Vincent_Standard', 0)
    row[fi['ReserveCharaSpec']] = ('PC0011_00_Vincent_Standard', 0)
    row[fi['ContentsSoundAutoSE_Array']] = [wstr('AS_PC0011_00_Vincent_Standard')]

OUT = '/work/charaspecmod/out'
os.makedirs(OUT, exist_ok=True)
pkg, _ = rebuild(cloud_to_vincent)
open(os.path.join(OUT, 'CharaSpec_cloud_to_vincent.uasset'), 'wb').write(pkg)
NAME = 'VincentReplacesCloud_Test_P'
pid = package_id('/Game/DataObject/Resident/CharaSpec')
assert pid == 0x726ef95c69149a89
cid = container_id_from_name(NAME)
hdr = container_header(cid, [dict(id=pid, size=len(pkg), export_count=1, export_bundle_count=1, imports=[], load_order=0)])
hdr = hdr + b'\0' * (65536 - len(hdr))
chunks = [dict(id64=cid, type=10, data=hdr, path=None),
          dict(id64=pid, type=2, data=pkg, path='DataObject/Resident/CharaSpec.uasset')]
base = os.path.join(OUT, NAME)
write_container(base, NAME, chunks)
shutil.copy('/work/vincentmod/FullyPlayableVincentAssets_P.pak', base + '.pak')
# read back
t = Toc(base + '.utoc')
print('container %016x flags %d entries %d methods %s files %s' % (t.container_id, t.flags, t.entries, t.methods, t.files))
for i in range(t.entries):
    d = t.read(i)
    print(i, '%016x' % t.chunk_id64(i), 'type', t.chunk_type(i), len(d), 'same' if d == chunks[i]['data'] else 'DIFFERENT')
for f in sorted(os.listdir(OUT)): print(f, os.path.getsize(os.path.join(OUT, f)))
