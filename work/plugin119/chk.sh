#!/bin/bash
# chk.sh [plugin root]: UHT stand-ins for every reflected header of the plugin, then a clang syntax check of every .cpp
P=${1:-/work/plugin119/src}
W=/work/uehdr
S=/tmp/scratch
INCDIR=$W/Proj/Plugins/RebirthSkelCompat/Intermediate/Build/Win64/UE4Editor/Inc/RebirthSkelCompatEditor
M=$P/Source/RebirthSkelCompatEditor
for H in $(grep -l "GENERATED_BODY" $M/Public/*.h $M/Private/*.h); do
  rel=${H#$P/}
  id="FF7R2UProj_Plugins_RebirthSkelCompat_$(echo ${rel%.h}_h | tr '/' '_')"
  base=$(basename ${H%.h})
  python3 /work/plugin118/gen_uht117.py "$H" "$id" REBIRTHSKELCOMPATEDITOR_API "$INCDIR/$base.generated.h" >/dev/null || { echo "UHT stand-in failed: $H"; exit 1; }
done
RESP=/data/uploads/FF7R2UProj/Saved/ModExtract/skelcompat-editor.response
INC=$(tr -d '\r' < "$RESP" | python3 -c "
import sys
W='$W'; P='$P'
out=[]
for line in sys.stdin:
    line=line.strip()
    if not line.startswith('/I '): continue
    p=line[3:].strip().strip('\"')
    if p.startswith('C:\\\\Program Files') : continue
    if p.startswith('C:\\\\FF7R2UProj\\\\Plugins\\\\RebirthSkelCompat\\\\Intermediate'):
        p=W+'/Proj/Plugins/RebirthSkelCompat/Intermediate'+p[len('C:\\\\FF7R2UProj\\\\Plugins\\\\RebirthSkelCompat\\\\Intermediate'):]
    elif p.startswith('C:\\\\FF7R2UProj\\\\Plugins\\\\RebirthSkelCompat'):
        p=P+p[len('C:\\\\FF7R2UProj\\\\Plugins\\\\RebirthSkelCompat'):]
    elif p.startswith('..\\\\'):
        p=W+'/Engine/'+p[3:]
    elif p=='.':
        p=W+'/Engine/Source'
    else:
        p=W+'/Engine/Source/'+p
    out.append('-I'+p.replace('\\\\','/'))
print(' '.join(out))
")
# (modules 1.17 adds: their Public folders, and the ones they include)
for extra in Editor/ContentBrowser/Public Editor/ContentBrowserData/Public Editor/AdvancedPreviewScene/Public Editor/EditorWidgets/Public Editor/UnrealEd/Classes Editor/UnrealEd/Public Developer/AssetTools/Public Editor/MainFrame/Public Editor/ContentBrowser/Private \
             Editor/AnimGraph/Classes Editor/AnimGraph/Public Runtime/AnimGraphRuntime/Public Editor/BlueprintGraph/Classes Editor/BlueprintGraph/Public Editor/KismetCompiler/Public Runtime/PropertyAccess/Public; do
  [ -d "$W/Engine/Source/$extra" ] && INC="$INC -I$W/Engine/Source/$extra"
done
# (1.19) the engine modules' generated headers the anim graph classes need
for m in AnimGraph AnimGraphRuntime BlueprintGraph PropertyAccess; do
  [ -d "$W/Engine/Intermediate/Build/Win64/UE4Editor/Inc/$m" ] && INC="$INC -I$W/Engine/Intermediate/Build/Win64/UE4Editor/Inc/$m"
done
SYS="-I$W/check/stubs -I$W/niagara -DNIAGARA_API=__declspec(dllimport) -isystem $S/sdk/msvc/include -isystem $S/sdk/kits/ucrt -isystem $S/sdk/kits/shared -isystem $S/sdk/kits/um"
UNITY=/work/plugin119/Module.RebirthSkelCompatEditor.cpp
{
  for C in $M/Private/*.cpp; do
    echo '#pragma clang diagnostic warning "-Wshadow"'
    echo "#include \"$C\""
  done
} > $UNITY
clang++ -ivfsoverlay $S/vfs.yaml -ivfsoverlay $W/check/ue_vfs.json --target=x86_64-pc-windows-msvc -fms-compatibility -fms-extensions -fms-compatibility-version=19.44 \
  -fsyntax-only -std=c++17 -fno-rtti -fexceptions -fcxx-exceptions -ferror-limit=0 \
  -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH -D_CRT_STDIO_LEGACY_WIDE_SPECIFIERS=1 -D_SILENCE_STDEXT_HASH_DEPRECATION_WARNINGS=1 \
  -D_CRT_USE_BUILTIN_OFFSETOF -D_WINDLL -D_DISABLE_EXTENDED_ALIGNED_STORAGE -D_MT -D_DLL \
  -Wno-everything -Wshadow-all -Wunused-variable -Wunused-but-set-variable -Wuninitialized -Wsometimes-uninitialized \
  -Wreturn-type -Wdangling -Wreorder -Winconsistent-missing-override \
  $SYS $INC \
  -include $W/check/shadowfix.h -include $W/check/SharedPCH.UnrealEd.h -include /work/plugin119/Definitions.RebirthSkelCompatEditor119.h \
  "$UNITY" 2>&1
