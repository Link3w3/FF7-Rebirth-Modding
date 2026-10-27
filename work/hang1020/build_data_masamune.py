"""Test data pak: FullyPlayableYoungSephirothDataAssets_P as built, but Cloud's weapon packs keep the Masamune's
blueprint (FPS's): only the character packs name Young Sephiroth's blueprint."""
import sys
sys.path.insert(0, '/work/fpys/tools')
import build_fpys_data as B
B.WEAPON_PACKS = []
B.main(*sys.argv[1:])
