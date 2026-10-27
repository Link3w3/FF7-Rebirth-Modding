#!/bin/bash
# Syntax-check the KawaiiPhysics plugin (runtime + editor module) against RebirthEngineV5's headers with clang (MSVC target).
#   kawaii_check.sh <plugin-root> [rt|ed|both]
W=/work/uehdr
S=/tmp/scratch
C=/work/kawaii_import/check
PLUGIN=${1:-/work/kawaii_import/new}
WHICH=${2:-both}
RESP=/data/uploads/FF7R2UProj/Saved/ModExtract/skelcompat-editor.response
INC=$(tr -d '\r' < "$RESP" | python3 -c "
import sys
W='$W'
out=[]
for line in sys.stdin:
    line=line.strip()
    if not line.startswith('/I '): continue
    p=line[3:].strip().strip('\"')
    if p.startswith('C:\\\\'): continue          # the project's / VS paths (the plugin's own come below)
    if p.startswith('..\\\\'):
        p=W+'/Engine/'+p[3:]
    elif p=='.':
        p=W+'/Engine/Source'
    else:
        p=W+'/Engine/Source/'+p
    out.append('-I'+p.replace('\\\\','/'))
print(' '.join(out))
")
# the modules KawaiiPhysics(Ed) adds to RebirthSkelCompatEditor's set (with UBT's legacy public include paths: every folder of Public)
EXTRA=""
for m in Editor/AnimGraph Runtime/AnimGraphRuntime Editor/Persona Editor/SkeletonEditor Editor/AdvancedPreviewScene \
         Developer/DesktopPlatform Editor/AnimationEditor Editor/AnimationBlueprintEditor Editor/KismetWidgets Editor/SequencerWidgets; do
  n=${m##*/}
  EXTRA="$EXTRA -I$W/Engine/Intermediate/Build/Win64/UE4Editor/Inc/$n"
  for d in $(find $W/Engine/Source/$m/Public -type d 2>/dev/null) $W/Engine/Source/$m/Classes; do [ -d $d ] && EXTRA="$EXTRA -I$d"; done
done
SYS="-isystem $S/sdk/msvc/include -isystem $S/sdk/kits/ucrt -isystem $S/sdk/kits/shared -isystem $S/sdk/kits/um"

# UnrealHeaderTool stand-ins
G=$C/Inc
mkdir -p $G/KawaiiPhysics $G/KawaiiPhysicsEd
for h in AnimNode_KawaiiPhysics KawaiiPhysicsLimitsDataAsset; do
  python3 $C/gen_uht.py "$PLUGIN/Source/KawaiiPhysics/Public/$h.h" FF7R2UProj_Plugins_KawaiiPhysics_Source_KawaiiPhysics_Public_${h}_h KAWAIIPHYSICS_API $G/KawaiiPhysics/$h.generated.h >/dev/null || exit 1
done
for h in AnimGraphNode_KawaiiPhysics KawaiiPhysicsGameImport; do
  python3 $C/gen_uht.py "$PLUGIN/Source/KawaiiPhysicsEd/Public/$h.h" FF7R2UProj_Plugins_KawaiiPhysics_Source_KawaiiPhysicsEd_Public_${h}_h KAWAIIPHYSICSED_API $G/KawaiiPhysicsEd/$h.generated.h >/dev/null || exit 1
done
PINC="-I$G/KawaiiPhysics -I$G/KawaiiPhysicsEd -I$PLUGIN/Source/KawaiiPhysics/Public -I$PLUGIN/Source/KawaiiPhysicsEd/Public"

run() {  # run <module> <defs header> <files...>
  local mod=$1 defs=$2; shift 2
  local unity=$C/Module.$mod.cpp
  : > $unity
  for f in "$@"; do
    echo '#pragma clang diagnostic warning "-Wshadow"' >> $unity
    echo "#include \"$f\"" >> $unity
  done
  echo "=== $mod"
  clang++ -ivfsoverlay $S/vfs.yaml -ivfsoverlay $W/check/ue_vfs.json --target=x86_64-pc-windows-msvc -fms-compatibility -fms-extensions -fms-compatibility-version=19.44 \
    -fsyntax-only -std=c++17 -fno-rtti -fexceptions -fcxx-exceptions -ferror-limit=0 \
    -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH -D_CRT_STDIO_LEGACY_WIDE_SPECIFIERS=1 -D_SILENCE_STDEXT_HASH_DEPRECATION_WARNINGS=1 \
    -D_CRT_USE_BUILTIN_OFFSETOF -D_WINDLL -D_DISABLE_EXTENDED_ALIGNED_STORAGE -D_MT -D_DLL \
    -Wno-everything -Wshadow-all -Wunused-variable -Wunused-but-set-variable -Wuninitialized -Wsometimes-uninitialized \
    -Wreturn-type -Wdangling -Wreorder -Winconsistent-missing-override \
    $SYS $INC $EXTRA $PINC $MODINC \
    -include $W/check/shadowfix.h -include $W/check/SharedPCH.UnrealEd.h -include $defs \
    "$unity" 2>&1
}
R=$PLUGIN/Source/KawaiiPhysics
E=$PLUGIN/Source/KawaiiPhysicsEd
if [ "$WHICH" != ed ]; then
  MODINC="-I$R/Private -I$R/Private/Solver" run KawaiiPhysics $C/Definitions.KawaiiPhysics.h \
    $R/Private/KawaiiPhysics.cpp $R/Private/KawaiiPhysicsLimitsDataAsset.cpp $R/Private/AnimNode_KawaiiPhysics.cpp
fi
if [ "$WHICH" != rt ]; then
  MODINC="-I$E/Private" run KawaiiPhysicsEd $C/Definitions.KawaiiPhysicsEd.h \
    $E/Private/KawaiiPhysicsEd.cpp $E/Private/AnimGraphNode_KawaiiPhysics.cpp $E/Private/KawaiiPhysicsEditModeBase.cpp \
    $E/Private/KawaiiPhysicsEditMode.cpp $E/Private/KawaiiPhysicsGameImport.cpp
fi
