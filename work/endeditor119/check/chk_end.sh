#!/bin/bash
# chk_end.sh [src root]: UHT stand-ins for the End editor module's new headers (and the lip sync plugin's), then a clang
# syntax check of the new .cpp files against the engine headers, End's EndGame headers and their generated headers.
P=${1:-/work/endeditor119/src}
W=/work/uehdr
C=/work/endeditor119/check
S=/tmp/scratch
U=/data/uploads/FF7R2UProj
GEN=$C/gen
mkdir -p $GEN
for H in $P/Public/*.h; do
  grep -q GENERATED_BODY "$H" || continue
  base=$(basename ${H%.h})
  python3 /work/plugin118/gen_uht117.py "$H" "FF7R2UProj_Source_ENDEditor_Public_${base}_h" ENDEDITOR_API "$GEN/$base.generated.h" >/dev/null || { echo "UHT stand-in failed: $H"; exit 1; }
done
HSF=$U/Plugins/HappySadFaceLipSync/Source/HSFLipSyncRuntime/Public
for H in $HSF/*.h; do
  grep -q "GENERATED_BODY\|UENUM" "$H" || continue
  base=$(basename ${H%.h})
  python3 /work/plugin118/gen_uht117.py "$H" "FF7R2UProj_Plugins_HappySadFaceLipSync_Source_HSFLipSyncRuntime_Public_${base}_h" HSFLIPSYNCRUNTIME_API "$GEN/$base.generated.h" >/dev/null || { echo "UHT stand-in failed: $H"; exit 1; }
done
RESP=/data/uploads/FF7R2UProj/Saved/ModExtract/skelcompat-editor.response
INC=$(tr -d '\r' < "$RESP" | python3 -c "
import sys
W='$W'
out=[]
for line in sys.stdin:
    line=line.strip()
    if not line.startswith('/I '): continue
    p=line[3:].strip().strip('\"')
    if p.startswith('C:\\\\Program Files') or p.startswith('C:\\\\FF7R2UProj'): continue
    if p.startswith('..\\\\'):
        p=W+'/Engine/'+p[3:]
    elif p=='.':
        p=W+'/Engine/Source'
    else:
        p=W+'/Engine/Source/'+p
    out.append('-I'+p.replace('\\\\','/'))
print(' '.join(out))
")
for extra in Editor/AnimGraph/Classes Editor/AnimGraph/Public Runtime/AnimGraphRuntime/Public Editor/BlueprintGraph/Classes Editor/BlueprintGraph/Public \
             Editor/UnrealEd/Classes Editor/UnrealEd/Public Editor/KismetCompiler/Public Editor/Kismet/Public Editor/GraphEditor/Public \
             Developer/AssetTools/Public Editor/Persona/Public Runtime/PropertyAccess/Public Editor/MovieSceneTools/Public Runtime/MovieScene/Public; do
  [ -d "$W/Engine/Source/$extra" ] && INC="$INC -I$W/Engine/Source/$extra"
done
for m in AnimGraph AnimGraphRuntime BlueprintGraph UnrealEd Engine PropertyAccess KismetCompiler Kismet GraphEditor; do
  [ -d "$W/Engine/Intermediate/Build/Win64/UE4Editor/Inc/$m" ] && INC="$INC -I$W/Engine/Intermediate/Build/Win64/UE4Editor/Inc/$m"
done
INC="$INC -I$P/Public -I$P/Private -I$GEN -I$U/Source/EndGame/Public -I$U/Intermediate/Build/Win64/UE4Editor/Inc/EndGame -I$HSF"
SYS="-I$W/check/stubs -isystem $S/sdk/msvc/include -isystem $S/sdk/kits/ucrt -isystem $S/sdk/kits/shared -isystem $S/sdk/kits/um"
UNITY=$C/Module.ENDEditor.cpp
{
  for F in ${FILES:-$P/Private/*.cpp}; do
    echo '#pragma clang diagnostic warning "-Wshadow"'
    echo "#include \"$F\""
  done
} > $UNITY
clang++ -ivfsoverlay $S/vfs.yaml -ivfsoverlay $W/check/ue_vfs.json --target=x86_64-pc-windows-msvc -fms-compatibility -fms-extensions -fms-compatibility-version=19.44 \
  -fsyntax-only -std=c++17 -fno-rtti -fexceptions -fcxx-exceptions -ferror-limit=0 \
  -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH -D_CRT_STDIO_LEGACY_WIDE_SPECIFIERS=1 -D_SILENCE_STDEXT_HASH_DEPRECATION_WARNINGS=1 \
  -D_CRT_USE_BUILTIN_OFFSETOF -D_WINDLL -D_DISABLE_EXTENDED_ALIGNED_STORAGE -D_MT -D_DLL \
  -Wno-everything -Wshadow-all -Wunused-variable -Wunused-but-set-variable -Wuninitialized -Wsometimes-uninitialized \
  -Wreturn-type -Wdangling -Wreorder -Winconsistent-missing-override \
  $SYS $INC \
  -include $W/check/shadowfix.h -include $W/check/SharedPCH.UnrealEd.h -include $C/Definitions.ENDEditor.h \
  "$UNITY" 2>&1
