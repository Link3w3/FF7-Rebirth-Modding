"""An effect pack (EndAssetPack: AssetUserData = the effects and what they use, as the game's own
<character>_Effect__Pack packages list them) for converted effects, so a character's CharaSpec pack can list it next to
its own effect packs (RebirthSkelCompat "pack_assets"): the game finds the effects anim notifies name in the effect
packs of the character's pack.

    make_effect_pack.py <out run dir> <package> <object path>..."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nconvert as C
from gv import struct_ as S, obj, array


def main(out_dir, package, *objects):
    out = C.Out(package)
    refs = [obj(out.import_index(p)) for p in objects]
    name = package.rsplit('/', 1)[-1]
    out.add_export(name, None, '/Script/EndGame.EndAssetPack', S('EndAssetPack', {'AssetUserData': array(refs)}),
                   tail=b'\0' * 4, flags=11, filter_flags=0)
    data, entry = C.assemble(out, package)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, name + '.zen'), 'wb').write(data)
    json.dump({'package': package, 'entry': entry, 'report': {'objects': list(objects)}},
              open(os.path.join(out_dir, 'report.json'), 'w'), indent=1, default=str)
    print(package, len(data), 'bytes,', len(objects), 'objects; imported packages', len(entry['imports']))


if __name__ == '__main__':
    main(*sys.argv[1:])
