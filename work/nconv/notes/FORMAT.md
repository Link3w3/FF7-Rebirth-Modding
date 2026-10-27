# Rebirth Niagara cooked format (what the converter must write)

Rebirth's Niagara = UE 5.1-era Niagara (emitter versioning fields, LWC position sources, bDisableExperimentalVM,
VMExecutableData with compressed ByteCode + UncompressedSize, OptimizedByteCode struct, NumUserPtrs...) backported by
Square Enix into their 4.26 engine, plus SQEX fields/blocks. The End editor (UnrealEngine-CE) has stock 4.26 Niagara.

## Proven (2026-10-19)
- tools/nio.py: reader + exact writer for every cooked Niagara export; 86 game systems / 1902 exports round-trip
  byte-identical (`python3 nio.py roundtrip ../samples/*.uasset`). Tails after properties are copied raw for now.
- tools/nfrozen.py: FMemoryImage writer (sections in creation order depth-first, each aligned to its own alignment,
  merge only sections with identical bytes AND identical raw targets (in practice leaf sections), image size padded to
  its alignment) + KHCV codec; all 86 KHCV blocks re-encode identical.
- EVectorVMOp: identical in the game (usmap enum, 96 entries) and 4.26 -> End-compiled CPU bytecode uses the same ops.

## Unversioned properties
- schema index order: the class's own properties first, then its super's (usmap.prop_at / uwrite.schema).
- after the properties every UObject has u32 0 (no lazy-object GUID). NiagaraSpriteRendererProperties: +u32 0.
  NiagaraScript (CPU): u32 0 (669) or 8 zero bytes (78). GPU scripts: shader map data (not generated: CPU only).
- NiagaraSystem tail: u32 0, i32 N emitters, N x unversioned FNiagaraEmitterCompiledData (game schema: 8 NiagaraVariables
  incl. SQEX m_VfxMaterialIndependentParameter_InstanceSeedVar, then DataSetCompiledData).
- NiagaraSystem export starts with the KHCV block (before the properties).

## SQEX native blocks
- FNiagaraTypeDefinition: empty property stream (struct has no reflected properties: header 00 01) + 'VFX1' u32 hash,
  u16 ver (1), u16 underlying type (1 class/DI, 2 struct, 3 enum = 4.26 FUnderlyingType), u32 0.
  Type hashes (not CRC/FNV/City of the names tried): see TYPES in tools (table from game data).
- FNiagaraVariable: base (FName + typedef) + i32 size + data.  FNiagaraVariableWithOffset: base + i32 offset.
- FNiagaraScriptDataInterfaceInfo: properties, then (for frozen DIs) a 'VFX0' memory image of the DI.
- FNiagaraUserRedirectionParameterStore: properties, then 'KHCV' u32 n + n x ('VFX1' u32, u32) (n = user DIs).
- memory image: magic ('VFX0' | 'KHCV' u32 extra), u32 size, u16 align, u16 pad, pad, image, u32 nvtables,
  u32 nscriptnames, u32 nminimalnames, vtables (u64 type hash, u32 n, n x (u32,u32)), names (FName, u32 n, n x u32 off).

## KHCV (system block) = derived data, fully computable
4 TMemoryImageArrays: system dataset layouts, spawn instance params layouts, update instance params layouts,
emitters[] {TArray<FName> SpawnAttributes, TArray<FNiagaraVariableLayoutInfo> particle dataset layouts}.
FNiagaraVariableLayoutInfo (104 B): u16 FloatStart, Int32Start, HalfStart, u16 0; 6 x TArray<u16>
(FloatByteOffsets, FloatRegisterOffsets, IntByte, IntReg, HalfByte, HalfReg). Starts = running component counts in
variable order; offsets per type (14 types seen, no conflicts): float [0], int/bool/enums [0], vec2 F[0,4],
vec3 F[0,4,8], vec4/color/quat F[0,4,8,12], ID I[0,4], SpawnInfo F[4,8] I[0,12], MeshTriCoord I[0] F[4,8,12],
matrix F[0..60]. Register offsets = 0..n-1.

## Frozen DIs (VFX0), by vtable type hash
- curves: FloatCurve c9ebb81f6e949b4c (typedef 80877f55), ColorCurve bfd80ddd6a8ec2a8 (a634ab99),
  VectorCurve 0b17848a30d548bb (a7c132d1), Vector2DCurve 33d78a10f8c7489b (cb9b3865):
  [0] vtable (ff..ff, patched via vtables (hash, [(0,0)])), [8..24] 0, [24] TArray<float> ShaderLUT, [40] LUTMinTime,
  LUTMaxTime, LUTInvTimeRange, LUTNumSamplesMinusOne (floats), [56] u32 LUTOffset (0xffffffff on CPU scripts; GPU:
  offset into a global LUT), [60] u8 bUseLUT=1, pad; LUT section after (samples x components floats).
- 24-byte images (just vtable + 16 zero bytes): 90a548c14dd9a3c0 (typedef 8e6602cc, e.g. "System.VFX Light"),
  0cd924578feb11d2 (7b0059, CollisionQuery).  VectorField f5194476c0d9c909 (a9822962): 40 bytes.
- DIs that are separate exports (no image): ParticleRead, StaticMesh, ArrayFloat/Float3, SQEX ActorMaterialParameter,
  AppendixMesh, Trail, VolumetricFogProbe, VFX function library.

## Proven from the game's own data (2026-10-19, converter v1)
- Memory images (KHCV and every VFX0) start 8-aligned counted in SERIAL offsets (export map SerialOffset + position in
  the export = the export archive's Tell()), never in file positions: 2300/2300 game images. The cooker writes the pad
  (0..7 zero bytes, its count in the u16) to get there. nconvert.assemble pads ours the same way (align_images).
- VM byte code: UncompressedSize omitted = raw byte code (84 game scripts: all decode as plain VectorVM code ending in
  `done`); present (>0) = Oodle data of that size (585). Game ops = 4.26 ops: 669/669 game scripts decode with the
  4.26 table; every op and external function (SampleCurve/VectorCurve/Vector2DCurve) our scripts use is used by them.
- CPU scripts in the game have rapid iteration parameters baked to literals (none in their execution stores; RI store
  empty). Ours keep them as external constants, so their VALUES must be in the execution store: the editor's compiled
  parameter list carries the module defaults, the emitter's actual values are in the script's RapidIterationParameters
  (146 of 483 differed in APP0). nconvert takes them from there.
- Array elements and export-tail structs are serialized dense by the game's cooker (every property in the header,
  zero ones flagged). An omitted property loads as the C++ constructor default, so anything whose default is not what
  we want must be written: FNiagaraEmitterHandle.bIsEnabled (default true) is written as zero to disable.
- VMExecutableDataId: game writes bUsesRapidIterationParams false (default true), bDisableDebugSwitches, BaseScriptCompileHash.
- Emitters: GPUComputeScript written as null on every CPU emitter. EmitterCompiledData (system tail) per emitter:
  8 variables + DataSetCompiledData (VariableLayouts empty: layouts live in KHCV); the SQEX seed variable is
  'Engine.<emitter>.VfxMaterialIndependentParameterInstanceSeed' int32 (the End editor leaves it a nameless Vector4).
- Constant buffers (particle scripts): [G 32][S 48][O 512][E 32][Ext] (+ PREV copies when interpolated) [Literals];
  5.1 layouts: owner LWC tile appended at 496, system RandomSeed at 36, emitter InstanceSeed at 20, SQEX field at E+24.
  System scripts: [G][Ext][Literals] in both. Checked: 1414 constant operands of APP0 land on the same (table, offset).
