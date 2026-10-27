Chaos Vincent wing Bonamik (PC0011_10_BNM)

Wing physics for Chaos Vincent, made from Sephiroth's transformed form (PC0010_10_BNM, its "Wing" group).
Only the numbered wing bones 2F..58 get physics. No hair, cape or collar.

HOW TO MAKE IT
  End editor open:  File > Execute Python Script... > make_chaos_vincent_wing_bonamik.py
  Editor closed:    double-click make_chaos_vincent_wing_bonamik.cmd
  It creates /Game/Character/Player/PC011_10_Chaos/Model/PC0011_10_BNM, adds it to the PC0011_10 mesh
  (Asset Details > Asset User Data > SQEX_KBD_AssetUserData > Bonamik Data List), checks every value it wrote,
  saves both and writes C:\FF7R2UProj\Saved\ChaosVincentBonamik\report.json. Running it again rebuilds the asset.
  Package the project as usual; the mesh brings the Bonamik asset into the cook.

WHAT MOVES (each wing, the right wing is the same bones + 0x15)
  32 > 33            root 32 follows the animation, 33 swings
  36 > 37 > 38       root 36, 37 and 38 swing
  3B > 3C            root 3B, 3C swings
  3E > 3F > 40       root 3E, 3F and 40 swing
  41 > 42 > 43       root 41, 42 and 43 swing
  2F 30 31 34 35 39 3A 3D (44 45 46 49 4A 4E 4F 52) keep following the animation.
  Sephiroth's feather values: swinging bodies mass 0.05, damping 1.0, links 0.8, cones 0.3 inner / 0.8 outer.
  No collisions (Sephiroth's feathers mostly have none either).

TUNING (top of the .py, then run it again)
  LIMIT_Y / LIMIT_Z   how far the wing bones may swing from the animated pose, in degrees, for the bone's Y and
                      Z axes (Z is the wing surface's normal). Sephiroth's 10 / 25, swapped because his feather
                      bones have Y as the normal. Smaller numbers = stiffer wings.
  CHAINS              which bones get physics.

NOTES
  The asset is Bonamik 2.x data like Sephiroth's. The editor's Bonamik preview only shows 3.x data, so check the
  wings in game.
  To remove it: delete PC0011_10_BNM and the SQEX_KBD_AssetUserData entry on the PC0011_10 mesh.
