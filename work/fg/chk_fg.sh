#!/bin/bash
# Syntax check of RebirthFrameGen's C++ with clang in MSVC mode against the PC's MSVC 14.44 / Windows SDK 10.0.26100
# headers (header pack). Usage: chk_fg.sh [errors|warn]   (warn: also a curated set of warnings)
SP=/tmp/scratch
H=$SP/sdk
T=/work/fg/tree/RebirthFrameGen
MODE=${1:-errors}
SYS="-isystem $H/msvc/include -isystem $H/kits/ucrt -isystem $H/kits/shared -isystem $H/kits/um"
BASE="--target=x86_64-pc-windows-msvc -ivfsoverlay $SP/vfs.yaml -fms-compatibility -fms-extensions -ivfsoverlay $SP/fg_vfs_ffx.yaml -fms-compatibility-version=19.44 -fno-delayed-template-parsing -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH -fsyntax-only -fexceptions -fcxx-exceptions -nostdinc++ -nostdlibinc $SYS -D_WIN32 -DWIN32 -D_WINDOWS -DNDEBUG -D_MT -ferror-limit=50"
if [ "$MODE" = warn ]; then
	WARN="-Wno-everything -Wuninitialized -Wsometimes-uninitialized -Wreturn-type -Wunused-variable -Wformat -Wdangling -Wreturn-stack-address -Wimplicit-fallthrough -Wshadow-uncaptured-local -Wint-to-pointer-cast -Wunused-value -Wmismatched-new-delete -Wsizeof-pointer-memaccess"
else
	WARN="-Wno-everything"
fi
COMMON_DEFS="-DNOMINMAX -DVC_EXTRALEAN -DWIN32_LEAN_AND_MEAN -DBUILD_GIT_COMMIT_HASH=\"0e253f6-rfg-d3d12\""
fail=0; n=0
run() { # name, args...
	local name=$1; shift
	n=$((n+1))
	if out=$(clang++ $BASE $WARN "$@" 2>&1); then
		if [ -n "$out" ]; then echo "--- $name: OK with diagnostics"; echo "$out" | head -40; else echo "ok   $name"; fi
	else
		fail=$((fail+1)); echo "--- $name: FAILED"; echo "$out" | grep -E "error|note: " | head -30
	fi
}

# maindll (C++23, PCH.h force-included as CMake's target_precompile_headers does)
M=$T/dlssg/source/maindll
MINC="-isystem $SP/fg_shims -I$M -I$T/deps/spdlog/include -I$T/deps/DirectX-Headers/include -I$T/ffx/sdk/include -I$T/ffx/sdk/src/components"
for f in DllMain.cpp FFFrameInterpolator.cpp FFFrameInterpolatorDX.cpp FFInterfaceWrapper.cpp FFInterpolator.cpp Util.cpp NGX/NvNGXCuda.cpp NGX/NvNGXDirectX11.cpp NGX/NvNGXDirectX12.cpp NGX/NvNGXExports.cpp; do
	run "maindll/$f" -std=c++23 $COMMON_DEFS -DBUILD_VERSION_MAJOR=0 -DBUILD_VERSION_MINOR=130 $MINC -include $M/PCH.h $M/$f
done

# wrapper_generic -> version.dll (C++23, PCH.h force-included)
W=$T/dlssg/source/wrapper_generic
mkdir -p $SP/fg_detours_include/detours
cp $T/deps/Detours/src/detours.h $T/deps/Detours/src/detver.h $SP/fg_detours_include/detours/
# check-only copy of QuickDllProxy: clang rejects "__declspec(allocate) alignas(...)" (MSVC accepts it), so the copy
# puts alignas first; the shipped header is unchanged
WINC="-I$W -I$SP/fg_qdp -I$SP/fg_detours_include"
for f in DllMain.cpp NvAPI.cpp Proxies.cpp Hooking/Hooks.cpp Hooking/Memory.cpp; do
	run "wrapper_generic/$f" -std=c++23 $COMMON_DEFS $WINC -include $W/PCH.h $W/$f
done

# Detours static library (MSVC default language mode, Detours' Makefile defines)
D=$T/deps/Detours/src
for f in detours.cpp modules.cpp disasm.cpp image.cpp creatwth.cpp disolx86.cpp disolx64.cpp disolia64.cpp disolarm.cpp disolarm64.cpp; do
	run "detours/$f" -std=c++14 -DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x501 $D/$f
done

# FidelityFX SDK C++ that does not need the generated shader headers (the SDK build compiles all of it on the PC)
S=$T/ffx/sdk
FDEFS="-D_UNICODE -DUNICODE -D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR -DNOMINMAX -DWIN32_LEAN_AND_MEAN -DFFX_FI -DFFX_OF"
FINC="-isystem $SP/fg_shims -I$S/include -I$S/libs -I$S/src/components -I$S/src/shared -I$S/src/backends/shared"
for f in src/components/frameinterpolation/ffx_frameinterpolation.cpp src/components/opticalflow/ffx_opticalflow.cpp src/backends/dx12/ffx_dx12.cpp $(cd $S && ls src/shared/*.cpp src/backends/dx12/FrameInterpolationSwapchain/*.cpp 2>/dev/null); do
	run "ffx/$f" -std=c++14 $FDEFS $FINC $S/$f
done

echo "checked $n translation units, $fail failed"
[ $fail -eq 0 ]
