# Post-process materials: parked 2026-10-18 02:28 (user: "skip pp for now")

Built: AnimeCelPostProcess_P (DefaultPostProcessMaterial override, cel PS res 69 + SceneTexturesStruct at UB 3,
GraphUniformBuffers {3,8}); in ~mods (md5 utoc 0ad00b00, ucas f2dfb152). anime_pp_on/off.cmd, anime_pp_mod_off/on.cmd
in C:\FF7R2UProj\Tools. Live link 1.4 pp_apply / pp_clear / pp_status (1.5 adds tool.lua channel).

Findings in game (Junon, EndGame persistent world):
- pp_apply spawned an unbound volume (EndGame PersistentLevel) and AddOrUpdateBlendable worked (1 blendable).
- User: "it applied but didnt do nothing".
- 45 s later NO MaterialInstanceDynamic with Parent = DefaultPostProcessMaterial exists: UMaterialInterface::
  OverrideBlendableSettings (which always makes one via View.State->GetReusableMID) never ran for that blendable.
  So the view setup never took the blendable (game-thread side), before any shader question.
- r.PostProcessing.DisableMaterials 0, ShowFlag.PostProcessMaterial 2, material domain 4, location 0 (after tonemap).
- Only 20 UMaterials loaded, only one PP-domain material (DefaultPostProcessMaterial); level volumes have no blendables.
- View target: EndCameraActor (CameraComponent PostProcessBlendWeight 1, no blendables); EndPlayerCameraManager.
- Grayscale test (ColorSaturation W=0 on our spawned volume) was sent; result not reported (user parked PP).
- The game stops ticking while not the foreground window although t.IdleWhenNotForeground is 0.
- Exe has FPostProcessMaterialMS (SQEX draws PP materials with a mesh shader) and '-PostProcessingMaterial=' string.
- UE4SS GetWorld() returns a streamed level's own world (not the owning world).

Next when resumed: ask whether the grayscale showed. If yes -> SQEX's view setup drops blendables (try camera
PostProcessSettings / PlayerCameraManager blends, or look at '-PostProcessingMaterial='). If no -> spawned volumes are
not part of their volume list: test on a level's own unbound volume (GrassSky_Day_PostProcessVolume14).
