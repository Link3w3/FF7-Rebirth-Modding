Create a Character System Setup
===============================

CreateACharacterSystem-Setup-<version>.exe installs both parts of the system in one go:
  game mod       <game>\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\  (dlls\main.dll, README.txt, compat\example.json.txt, enabled.txt)
  editor plugin  <End project>\Plugins\RebirthSkelCompat\                 (RebirthSkelCompat.uplugin, Binaries\Win64, Source, README.txt)

Make a new Setup after a build
  1. Build the DLL (Tools\RebirthSkelCompat\run_build_dll.cmd, game closed) and the editor plugins
     (Tools\EndEditorPlugins\run_build_editor_plugins.cmd, editor closed).
  2. Double-click run_make_setup.cmd. The Setup and its file list go to Tools\Share; build\make_setup.log
     says what was packed, and warns when a DLL is older than its sources.

What Setup does
  - Finds the game through Steam (registry and libraryfolders.vdf) or Epic's manifests, and End projects through
    UE's recent projects, C:\FF7R2UProj and a short scan of fixed drives and the user's folders; Browse for others.
  - Checks UE4SS (build c0a8d4c) and the project's engine BuildId (the plugin is built for
    17c11882-043f-4330-9e21-2efa519533c5); refuses a project that already has the plugin in another folder.
  - Moves every file it replaces to a backup folder first: <mod>\Backups\<stamp> and
    <project>\CreateACharacterSystem-Backups\<stamp>. Works while the game or editor runs (they load the new
    files next start). Never touches compat files.
  - Uninstall needs Setup's CreateACharacterSystem.install.txt; it deletes only unchanged files and moves
    edited ones to the backup folder.
  - Log: CreateACharacterSystem-Setup.log in the mod folder and in %TEMP%.
  - Command line: /S (no window) /game:<folder> /project:<End.uproject> /nogame /noplugin /uninstall
    (a silent uninstall only touches the parts given).
  - Windows SmartScreen warns about an unsigned exe from the internet: More info > Run anyway.

Files here
  Setup.stub.exe      the Setup program without its payload (built from src\ with build_stub.sh: zig 0.17, clang + mingw-w64)
  make_setup.py       the packer (Python 3, standard library)
  run_make_setup.cmd  packs the latest builds into Tools\Share
  src\, res\          the Setup program's source and its icon / manifest
  tests\              setup_tests.cpp (payload, inflate, parsers) and wine_test.sh (installs, backups, uninstall under wine)
  third_party\puff\   inflate by Mark Adler (zlib license)
