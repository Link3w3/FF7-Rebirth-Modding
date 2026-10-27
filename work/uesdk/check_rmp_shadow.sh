#!/bin/bash
# Syntax-check a RebirthSkelCompatEditor source file the way UBT compiles it (MSVC mode clang, same include dirs and PCH header).
# usage: check_plugin.sh <plugin Source dir> [extra clang args]
SDK=/work/uesdk
WIN=/tmp/scratch/sdk
SRC="$1"; shift
RESP=$SDK/rmp/Module.RebirthMaterialPreview.1_of_3.cpp.obj.response
INC=()
while IFS= read -r line; do
  line="${line%$'\r'}"
  case "$line" in
    "/I "*) p="${line#/I }"; p="${p//\"/}"
      case "$p" in
        *:*) continue;;
        ..\\Intermediate*) p="$SDK/Engine/${p#..\\}";;
        .) p="$SDK/Engine/Source";;
        *) p="$SDK/Engine/Source/$p";;
      esac
      p="${p//\\//}"
      INC+=("-I$p");;
  esac
done < "$RESP"
INC+=("-I$SRC" "-I$SDK/genrmp")
clang++ -ivfsoverlay /work/uesdk/vfs.yaml --target=x86_64-pc-windows-msvc -fms-compatibility -fms-extensions -fms-compatibility-version=19.44 -std=c++14 -fsyntax-only -D_CRT_USE_BUILTIN_OFFSETOF -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH \
  -fdelayed-template-parsing -Wno-everything -Wshadow-all -ferror-limit=50 \
  -isystem $WIN/msvc/include -isystem $WIN/kits/ucrt -isystem $WIN/kits/shared -isystem $WIN/kits/um \
  -include $SDK/Project/Intermediate/Build/Win64/EndEditor/Development/UnrealEd/SharedPCH.UnrealEd.ShadowErrors.h \
  -include $SDK/rmp/Definitions.RebirthMaterialPreview.h \
  "${INC[@]}" "$@"
