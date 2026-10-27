HairDitherFix 1.2 (UE4SS Lua mod) for FINAL FANTASY VII REBIRTH

The game cuts hair out pixel by pixel against a moving blue-noise pattern (the engine's
SpatiotemporalBlueNoiseVolume) and counts on TAA to blend it into soft strands. At 1080p, or with an
upscaler, that shows as grain. This mod switches the engine to a calmer pattern while you play:

  Ctrl+F3   next mode: Soft -> Stable -> Off -> Game -> Soft ... (remembered in mode.txt)

  Soft    (default) only strand edges near half coverage still dither: far less grain
  Stable  the game's pattern, frozen: the same every frame, no crawling
  Off     no dither at all: a clean cut-out (sharpest, edges can look jagged)
  Game    the game's own pattern

The UE4SS console and UE4SS.log say "[HairDitherFix] hair dither: Soft (the game's noise kept by the
singleton)" once it is on, and name each mode you switch to.

Files
  ue4ss\Mods\HairDitherFix\Scripts\main.lua, enabled.txt, mode.txt
  Content\Paks\~mods\HairDitherFixUE4SS_P.pak / .ucas / .utoc   (the three patterns, /Game/HairDitherFix)

Don't install it together with HairDitherFix_P (the pak-only 1.1): that one replaces the game's own
pattern, so "Game" would not be the game's look.

Safety: before the engine is pointed at another pattern, the game's own is kept referenced (in the
engine's empty GameSingleton slot, else in the asset manager's keep-alive list), so it is never unloaded
while something might still use it. If neither can hold it, the mod changes nothing and says so in the log.

To turn it off: choose Game, or rename enabled.txt.
