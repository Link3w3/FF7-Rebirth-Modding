Safer Sephiroth's Bonamik (PC0010_999_BNM_Regular), a regular Bonamik

A regular Bonamik like the game's own characters' (Sephiroth's PC0010_00_BNM): no v2 data, so the editor's
Bonamik preview shows it. Every value is Sephiroth's own, sized to Safer.

WHAT MOVES
  Hair     his three locks: C_HairM a..j (the long one), L_HairE a..h, R_HairD a..h. The first bone of each follows
           his head; the rest swing like Sephiroth's long hair, with gravity turned well down so it keeps floating
           the way his animations show it and trails behind him when he moves.
  Feathers the 30 feathers of his six wings (each feather's a_Phy follows the wing, its b/c/d swing), stiff like
           Sephiroth's collar, following the wings' animation.
  Collisions his head, neck, back, shoulders and arms push his hair away so it never passes through him.
  The wing arms (WingA/B/C), the arm wing (R_HandWing), the cloud and the halo keep following the animation.

HOW TO MAKE IT
  Editor closed:  double-click run_safer_bonamik.cmd. It makes the Bonamik and then packages the project
                  (status in build\bonamik_status.txt).
  Editor open:    File > Execute Python Script... > make_safer_bonamik.py (then package as usual).
  It creates /Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999_BNM_Regular and puts it on the
  PC0010_999 mesh (Asset Details > Asset User Data > SQEX_KBD_AssetUserData > Bonamik Data List) in place of
  PC0010_999_BNM. The old v2 PC0010_999_BNM is left in the folder, unused: delete it whenever you like.
  Report: C:\FF7R2UProj\Saved\SaferBonamik\report.json. Running it again rebuilds the same asset.

TUNING (the top of make_safer_bonamik.py, then run it again)
  HAIR_GRAVITY       0.05   how much his hair sags (Sephiroth's hair 0.35; 0 = none)
  HAIR_LIMIT_SCALE   1.0    how far the hair may swing from the animation (smaller = stiffer)
  FEATHER_INNER      0.5    how hard a feather is pulled back to the wing's animation
  FEATHER_LIMIT      12     how far a feather may swing, in degrees
  FEATHER_GRAVITY    0.1
  HAIR_RADIUS        6      a hair body's thickness for collisions
  COLLIDER_RADIUS, SKULL_RADIUS, SKULL_OFFSET   the size of his body's collision shapes
You can also change any value in the asset itself in the editor; running the script again puts its values back.
