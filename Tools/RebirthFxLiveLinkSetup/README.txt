Rebirth FX Live Link Setup
==========================

RebirthFxLiveLink-Setup-<version>.exe installs both parts of the live link in one go, for anyone with the End project:
  editor plugin  <End project>\Plugins\RebirthFxLiveLink\                 (RebirthFxLiveLink.uplugin, Binaries\Win64, Source,
                                                                          Content\Python\rebirth_fx_link: the Rebirth FX menu)
  game mod       <game>\End\Binaries\Win64\ue4ss\Mods\RebirthLiveLink\    (Scripts\main.lua, README.txt, enabled.txt)

The plugin is the shareable part of the Rebirth FX tools: only engine modules (no EndDataObject, Bonamik or engine
additions), so it loads in any End project on RebirthEngineV5 (engine build 17c11882-043f-4330-9e21-2efa519533c5). In a
project that has its own Content\Python\rebirth_fx (yours), the plugin leaves the menu to that copy.

Make a new Setup after a change
  1. Editor plugin: Tools\EndEditorPlugins\run_build_fxlink.cmd (End editor closed) builds Plugins\RebirthFxLiveLink.
  2. Game mod: put the new main.lua in mod\RebirthLiveLink\Scripts\ (and bump  local VERSION  in it).
  3. Double-click run_make_setup.cmd. The Setup and its file list go to Tools\Share; build\make_setup.log says what was packed.

What Setup does (the same program as the Create a Character System Setup, see src\)
  - Finds the game through Steam (registry and libraryfolders.vdf) or Epic's manifests, and End projects through UE's
    recent projects, C:\FF7R2UProj and a short scan of fixed drives and the user's folders; Browse for others.
  - Checks UE4SS (build c0a8d4c), the project's engine BuildId, and Create a Character System 3.7.9+ in the game (live
    edits need its memory access; Setup only says so, it never installs or changes that mod).
  - Moves every file it replaces to a backup folder first: <mod>\Backups\<stamp> and <project>\RebirthFxLiveLink-Backups\<stamp>.
    Never touches the link's own files (link\command.lua, status.json, log.txt).
  - Uninstall needs Setup's RebirthFxLiveLink.install.txt; it deletes only unchanged files and moves edited ones to the
    backup folder.
  - Log: RebirthFxLiveLink-Setup.log in the mod folder and in %TEMP%.
  - Command line: /S (no window) /game:<folder> /project:<End.uproject> /nogame /noplugin /uninstall
  - Windows SmartScreen warns about an unsigned exe from the internet: More info > Run anyway.

Files here
  Setup.stub.exe      the Setup program without its payload (built from src\ with build_stub.sh: zig 0.17)
  tools\make_setup.py the packer (Python 3, standard library)
  run_make_setup.cmd  packs the current plugin and mod into Tools\Share
  mod\RebirthLiveLink the game mod as it is packed
  src\, res\          the Setup program's source and its icon / manifest
  tests\              setup_tests.cpp (payload, inflate, parsers) and wine_test.sh (installs, backups, uninstall under wine)
  third_party\puff\   inflate by Mark Adler (zlib license)
