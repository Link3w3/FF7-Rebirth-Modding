HairDitherFix 1.0 - smoother hair in FINAL FANTASY VII REBIRTH (UE4SS 3.0.1 Lua mod + a small pak)

Why hair looks grainy: the game cuts hair strands out per pixel against a moving blue-noise pattern and relies on TAA
to blend that pattern into soft strand edges. At 1080p, or with TAAU, DLSS or FSR, the blend breaks down and the
pattern shows as grain that crawls. This mod swaps the noise the engine uses for a calmer one (only its red channel,
the one the coverage test reads; the other channels, used for other effects, are the game's).

Install
  1. HairDitherFix_P.pak, HairDitherFix_P.ucas, HairDitherFix_P.utoc -> <game>\End\Content\Paks\~mods\
  2. the HairDitherFix folder -> <game>\End\Binaries\Win64\ue4ss\Mods\   (it has enabled.txt, so UE4SS starts it)

Modes (Ctrl+H cycles them in game; the choice is saved in mode.txt)
  Soft    (default) only coverage near 50% still dithers: soft edges, much less grain
  Stable  the game's pattern frozen in time: no crawling, a fine fixed pattern
  Off     no dither at all: a clean cut-out (sharpest; the thinnest strand tips thin out)
  Game    the game's own look

Remove: delete the three HairDitherFix_P files and the HairDitherFix folder.
