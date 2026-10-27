RebirthLiveLink 1.6 - the game side of Rebirth FX Live Link (UE4SS Lua mod for FINAL FANTASY VII REBIRTH)

The editor's Rebirth FX menu (the Rebirth FX Live Link plugin in your End project) sends commands here: play an
effect in front of your character, change its curves live, change the materials your character wears, and more.

  Scripts\main.lua      the mod (commands and what they do are listed at the top)
  enabled.txt           UE4SS starts mods that have it
  link\                 made at the first start: command.lua (from the editor), status.json and log.txt (answers),
                        tool.lua / tool_status.json (a second channel for other tools)

Needs UE4SS 3.0.1 (c0a8d4c). Live edits of curves and materials also need Create a Character System 3.7.9 or newer
(ue4ss\Mods\RebirthSkelCompat): it gives the link memory access and an every-frame update. Without it effects still
play and the link answers every 250 ms.
