#!/bin/bash
# Syntax-check a KawaiiPhysics (End editor, UE 4.26) plugin source file the way UBT compiles it (MSVC-mode clang, the
# RebirthSkelCompatEditor module's include dirs plus the anim graph / Persona ones, the UnrealEd shared PCH).
# usage: check_kawaii.sh <source file> [extra clang args]
SDK=/work/uesdk
WIN=/tmp/scratch/sdk
PLUG=/work/kawaii426/Plugins/KawaiiPhysics/Source
RESP=$SDK/Project/Plugins/RebirthSkelCompat/Intermediate/Build/Win64/UE4Editor/Development/RebirthSkelCompatEditor/Module.RebirthSkelCompatEditor.cpp.obj.response
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
E=$SDK/Engine
G=$E/Intermediate/Build/Win64/UE4Editor/Inc
INC+=("-I$E/Source/Runtime/AnimGraphRuntime/Public" "-I$G/AnimGraphRuntime"
      "-I$E/Source/Editor/AnimGraph/Public" "-I$E/Source/Editor/AnimGraph/Classes" "-I$G/AnimGraph"
      "-I$E/Source/Editor/Persona/Public" "-I$G/Persona"
      "-I$E/Source/Editor/SkeletonEditor/Public" "-I$G/SkeletonEditor"
      "-I$E/Source/Editor/AdvancedPreviewScene/Public" "-I$G/AdvancedPreviewScene"
      "-I$PLUG/KawaiiPhysics/Public" "-I$PLUG/KawaiiPhysics/Private" "-I$PLUG/KawaiiPhysics/Private/Solver"
      "-I$PLUG/KawaiiPhysicsEd/Public" "-I$PLUG/KawaiiPhysicsEd/Private" "-I$SDK/genkawaii")
clang++ -ivfsoverlay /work/uesdk/vfs.yaml --target=x86_64-pc-windows-msvc -fms-compatibility -fms-extensions -fms-compatibility-version=19.44 -std=c++17 -fsyntax-only -D_CRT_USE_BUILTIN_OFFSETOF -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH \
  -fdelayed-template-parsing -Wno-everything -ferror-limit=50 \
  -isystem $WIN/msvc/include -isystem $WIN/kits/ucrt -isystem $WIN/kits/shared -isystem $WIN/kits/um \
  -include $SDK/Project/Intermediate/Build/Win64/EndEditor/Development/UnrealEd/SharedPCH.UnrealEd.ShadowErrors.Cpp17.h \
  -include $SDK/genkawaii/Definitions.Kawaii.h \
  "${INC[@]}" "$@"
