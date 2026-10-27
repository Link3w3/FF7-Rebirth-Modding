"""skins/SeraphWeapon: Seraph Sephiroth's weapon blueprint (make_seraph_weapon.py's copy of the game's playable Masamune
blueprint, pointed at the Essence Shard) as a skin folder of its own ("part": true: nobody wears it; its package goes into
the skins container for the Seraph Sephiroth skins' weapon). skin.json written as SkinCore's WriteSkinJson writes it.
    make_weapon_part.py <out dir> <skin folder>"""
import json, os, shutil, sys, time
src = open('/work/anime1025/masamune/make_part_skin.py').read()
exec(src[src.index('def q('):src.index('entries = json.load')])
SRC, DST = sys.argv[1], sys.argv[2]
entries = json.load(open(os.path.join(SRC, 'store_entries.json')))
skin = dict(name='Seraph Sephiroth Weapon', author='',
            description="Seraph Sephiroth's Essence Shard: the game's playable (cut-scale) Masamune blueprint holding the "
                        "Essence Shard (its model, cooked into the Seraph Sephiroth skins). Its package only: the weapon of the "
                        "Seraph Sephiroth skins.",
            characters=[], model='', skeleton='', family='', voice='', weapon='', worn=False, part=True,
            packages=entries, built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            built_with="make_seraph_weapon.py (the game's package copied to a new path)")
if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST)
for p in entries:
    for f in [p['file']] + [b['file'] for b in p['bulk']]:
        os.makedirs(os.path.dirname(os.path.join(DST, f)), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, f), os.path.join(DST, f))
open(os.path.join(DST, 'skin.json'), 'w', newline='\n').write(write_skin_json(skin))
print(open(os.path.join(DST, 'skin.json')).read())
