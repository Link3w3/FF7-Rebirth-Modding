RebirthFPSBoost 1.0 (UE4SS Lua mod)
Frame-rate presets for FINAL FANTASY VII REBIRTH: engine settings (console variables) put on as the game starts,
again after every map load, and when you switch.

  Ctrl+F1   next preset: Off -> Light -> Balanced -> Performance -> Max -> Off ... (remembered for the next launch)
  Ctrl+F2   measure the frame rate for 5 seconds; the result shows in the UE4SS console (and UE4SS.log)

  Off          the game's own values (the ones it had before the mod changed them)
  Light        motion blur, chromatic aberration and lens flares off; distant characters animate a little less often
  Balanced     Light + somewhat cheaper shadows, depth of field and screen-space reflections   (the default)
  Performance  Balanced + low-resolution shadows, no screen-space reflections, coarser volumetric fog, shorter
               view distance for foliage and props, thinner grass
  Max          everything cheap: no volumetric fog, minimal shadows, short view distance, fewer particles

presets.lua (next to this file) holds the presets: change values, add or remove lines, or set a frame cap (max_fps).
Each switch prints how many settings took; one the game does not have or will not change is named and skipped.
Files: Scripts/main.lua, presets.lua, enabled.txt; state.txt (made by the mod) remembers the chosen preset.
To turn the mod off: delete or rename enabled.txt.
