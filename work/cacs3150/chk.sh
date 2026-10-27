#!/bin/sh
# Syntax check of the runtime with clang against the MSVC / Windows / UE4SS headers of the PC build (header pack).
H=/tmp/scratch/sdk
cd /work/cacs3150/src
INC="-I$H/shims -I$H/deps/fmt-10.2.1 -I$H/deps/zydis-4.1.0 -I$H/deps/zycore-zydis4.1.0-gitlink -I$H/ue4ss/UE4SS/include -I$H/ue4ss/UE4SS/generated_include"
for d in $(ls $H/ue4ss/deps/first | sort); do for r in include generated_include; do [ -d $H/ue4ss/deps/first/$d/$r ] && INC="$INC -I$H/ue4ss/deps/first/$d/$r"; done; done
INC="$INC -I$H/ue4ss/deps/first/Unreal/include/Unreal -I$H/ue4ss/deps/first/Unreal/include/Unreal/Core"
SYS="-isystem $H/msvc/include -isystem $H/kits/ucrt -isystem $H/kits/shared -isystem $H/kits/um"
exec clang++ --target=x86_64-pc-windows-msvc -ivfsoverlay /tmp/scratch/vfs.yaml -fms-compatibility -fms-extensions -fms-compatibility-version=19.44 -fdelayed-template-parsing -std=c++20 -fsyntax-only -fexceptions -fcxx-exceptions -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH -D_WIN32 -DWIN32 -D_WINDOWS -DNDEBUG -D_ITERATOR_DEBUG_LEVEL=0 -DUE_BUILD_SHIPPING=1 -DUE_GAME=1 -DPLATFORM_WINDOWS=1 -DPLATFORM_MICROSOFT=1 -DOVERRIDE_PLATFORM_HEADER_NAME=Windows -DUBT_COMPILED_PLATFORM=Win64 -DUNICODE -D_UNICODE -D_MT -D_DLL -nostdinc++ -nostdlibinc $SYS $INC -Wno-everything -Wunused-variable -Wuninitialized -Wreturn-type -Wsometimes-uninitialized -Wshadow-uncaptured-local -ferror-limit=40 "${1:-RebirthSkelCompat.cpp}"
