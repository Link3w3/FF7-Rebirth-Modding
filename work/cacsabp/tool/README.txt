Create a Character System: Rebirth AnimBlueprint Maker 1.0.0
=============================================================

Makes a character's AnimBlueprint for FINAL FANTASY VII REBIRTH from one of the game's own (a template), made for the
character's skeleton: the template's cooked package under the new name, its skeleton the character's, written as a
~mods container. Everything the template does stays (field and battle locomotion, the moves player the game's actions
and abilities play through, inertialization, slots, facial, the movement and sword expressions). The animations come
from the character's animation sets (CharaSpec packs) by name, as for the game's own characters.

In the editor: Window > Rebirth AnimBlueprint Maker, or right-click a Skeleton or Skeletal Mesh > Make a Rebirth
AnimBlueprint... (Create a Character System editor 1.18).

On its own (Python 3):

    py -3 make_cacs_abp.py --skeleton /Game/Character/Player/PC0099_00_Hero/Model/PC0099_00_Skeleton
    py -3 make_cacs_abp.py --skeleton <path> --name PC0099_00_Hero_Standard_Animation --template cloud --install
    py -3 make_cacs_abp.py --list

  --skeleton      the character's skeleton, as the editor shows its path (it must be in the game: cooked into the
                  character's mod)
  --name          the AnimBlueprint's name (default: the skeleton's character folder + _Animation)
  --folder        where it goes (default /Game/BluePrint/Animation/Player)
  --template      cloud (default) | sephiroth | vincent | monster | a cooked AnimBlueprint .uasset of the game's
  --control-rig   off (default: the template's common human Control Rig passes the pose through) | keep (only for a
                  character on a Rebirth human skeleton, with the game's bone names)
  --container     the container's name (default CACS_<name>_P); --out where it goes (default .\out)
  --install       also copies it into the game's ~mods\CACS_AnimBlueprints (--mods-folder, --game); refused while
                  the game runs

It prints the AnimBlueprint's class: use it as a form's "anim_class", a skin's "anim_blueprint", or a character
blueprint's AnimClass.

templates\ holds the game's own AnimBlueprints (taken from your game): they are not for sharing.
