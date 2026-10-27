RebirthFrameGen - frame generation for FINAL FANTASY VII REBIRTH on an RTX 30 card
===================================================================================

What this is
------------
dlssg-to-fsr3 v0.130 by Nukem (https://github.com/Nukem9/dlssg-to-fsr3), built here from source. It is free
software under the GNU GPL v3 (dlssg\LICENSE.md).

The game's own "DLSS Frame Generation" option only works on RTX 40 and 50 cards. This mod makes the option work on
your RTX 3050: when the game asks NVIDIA Streamline for DLSS Frame Generation, it gets AMD FSR 3.1 Frame Generation
instead (AMD FidelityFX SDK, MIT licence, ffx\LICENSE.txt). DLSS upscaling and NVIDIA Reflex stay NVIDIA's.

This copy is built for Direct3D 12 only (the Vulkan parts are left out). Two files go into the game folder
(End\Binaries\Win64, next to ff7rebirth_.exe):
  version.dll                       loads with the game, lets the frame-generation option through on RTX 30 and
                                    hands Streamline the FSR 3 implementation instead of NVIDIA's
  dlssg_to_fsr3_amd_is_better.dll   the FSR 3.1 frame generation itself

Build and install
-----------------
1. Close the game.
2. Double-click build_and_install_framegen.cmd (in this folder). It finds Visual Studio 2022 and CMake, builds AMD's
   FidelityFX SDK libraries (first run only, several minutes: it compiles the GPU shaders), builds the two DLLs and
   copies them into the game folder. Anything already there under those two names is first moved into
   End\Binaries\Win64\ue4ss\_mod_backups\framegen_<date>_<time>\. The script installs nothing on Windows and
   changes no settings.
3. Read build\framegen_status.txt. It ends with RESULT: SUCCESS, or RESULT: FAILED with the reason and the end of
   the log of the step that failed (all step logs are in build\logs\).
Needs: Visual Studio 2022 with "Desktop development with C++", including "C++ CMake tools for Windows".

Turning it on
-------------
1. Windows: Settings > System > Display > Graphics > Hardware-accelerated GPU scheduling: ON (on Windows 11 it is
   under "Advanced graphics settings" / "Change default graphics settings"), then restart the PC. Frame generation
   does not work without it. You have to switch it yourself; the build script only reports the setting.
2. In the game's graphics options:
     DLSS                    on, quality Balanced or Performance (1080p on an RTX 3050)
     DLSS Frame Generation   on (if the game offers 2x/3x/4x: 2x - FSR 3 makes one frame between two)
     NVIDIA Reflex           on
     VSync                   off
3. dlssg_to_fsr3.log appears next to ff7rebirth_.exe (End\Binaries\Win64) when the mod is active. Its first lines
   say that AMD FSR 3.1 Frame Generation replaces DLSS-G. No log file means the mod did not load.

Turning it off
--------------
Close the game and move version.dll and dlssg_to_fsr3_amd_is_better.dll out of End\Binaries\Win64.
framegen_off.cmd does exactly that (it moves them into End\Binaries\Win64\ue4ss\_mod_backups\framegen_off_<stamp>\).
To turn it back on, run build_and_install_framegen.cmd again; it reuses the finished build.

Good to know
------------
- Frame generation roughly doubles the frames you see, but the game does not respond faster: aim for about 40 fps or
  more before frame generation (lower settings or DLSS Performance if needed). Reflex keeps the lag down.
- Frame-rate counters inside the game (and RebirthFPSBoost's Ctrl+F2) count only the frames the game renders. An
  overlay that counts presented frames (for example NVIDIA's) shows the generated ones too.
- dlssg_to_fsr3.ini next to ff7rebirth_.exe holds debug switches, all 0. EnableDebugOverlay=1 shows AMD's debug view;
  use it only to check that frame generation runs.
- ReShade (dxgi.dll) is in the game folder too. If the game crashes or the picture flickers with frame generation on,
  try once without ReShade (move dxgi.dll out) to see whether the two clash.
- If the DLSS Frame Generation option stays greyed out: check that build\framegen_status.txt says SUCCESS, that
  version.dll is in End\Binaries\Win64 and whether dlssg_to_fsr3.log was written.
- The upstream author says not to use dlssg-to-fsr3 in multiplayer games. Rebirth is single-player.

What's in this folder
---------------------
  build_and_install_framegen.cmd   the build and install script
  framegen_off.cmd                 moves the two DLLs out of the game folder
  dlssg\     dlssg-to-fsr3 v0.130 (upstream commit 0e253f6): source\maindll, source\wrapper_generic, resources, and
             the CMakeLists.txt that replaces upstream's vcpkg build
  deps\      Detours v4.0.1, DirectX-Headers, spdlog v1.14.1, QuickDllProxy 1e9cf65 (sources and licences)
  ffx\       the sdk folder of the AMD FidelityFX SDK copy that dlssg-to-fsr3 ships (with licence)
  build\     made by the script: build output, framegen_status.txt, logs\

Changes from upstream (GPL-3, section 5)
----------------------------------------
- dlssg\source\maindll\FFInterfaceWrapper.h and .cpp: the Vulkan include and the Vulkan code are compiled only when
  DLSSG_ENABLE_VULKAN is defined (it is not, here). FFFrameInterpolatorVK.cpp/.h and NGX\NvNGXVulkan.cpp are left
  out, as is the DLSSTweaks wrapper.
- dlssg\CMakeLists.txt: new. Builds Detours, dlssg_to_fsr3_amd_is_better.dll and the Universal wrapper as
  version.dll without vcpkg and without the Vulkan SDK (static CRT, as upstream).
- dlssg\resources\dlssg_to_fsr3.ini: EnableDebugOverlay=0 (upstream ships 1).
- ffx\sdk\libs\pix\CMakeLists.txt: when the WinPixEventRuntime binaries are absent (they are not part of the source
  tree), an empty stand-in target is used instead of stopping CMake; the DX12 backend loads PIX at run time anyway.
- build_and_install_framegen.cmd runs the same CMake options and build switches as ffx\sdk\BuildFidelityFXSDK.bat
  for the SDK, but Release only, in build\ffx_sdk_vs17, without turning compiler warnings into errors, and it stops
  at the first failing step.
