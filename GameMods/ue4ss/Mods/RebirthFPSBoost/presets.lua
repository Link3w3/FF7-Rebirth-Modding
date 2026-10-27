-- RebirthFPSBoost presets. Edit freely: each preset is a list of { console variable, value }.
-- Ctrl+F1 steps through `order` (the choice is remembered for the next launch); Ctrl+F2 measures the frame rate for
-- 5 seconds and prints it to the UE4SS console. "Off" puts back the values the game had before the mod changed them.
-- A variable this game does not have (or will not change) is skipped and named in the console.
return {
    default = "Balanced",          -- the preset used the first time (afterwards: the last one chosen)
    order = { "Off", "Light", "Balanced", "Performance", "Max" },
    max_fps = 0,                   -- a frame cap (t.MaxFPS); 0 leaves the game's own

    presets = {
        Off = {},

        -- no visible loss: motion blur, chromatic aberration and lens flares off, cheaper animation updates far away
        Light = {
            { "r.MotionBlurQuality", 0 },
            { "r.MotionBlur.Max", 0 },
            { "r.SceneColorFringeQuality", 0 },
            { "r.LensFlareQuality", 0 },
            { "a.URO.Enable", 1 },
        },

        -- Light, plus somewhat cheaper shadows, depth of field and reflections
        Balanced = {
            { "r.MotionBlurQuality", 0 },
            { "r.MotionBlur.Max", 0 },
            { "r.SceneColorFringeQuality", 0 },
            { "r.LensFlareQuality", 0 },
            { "a.URO.Enable", 1 },
            { "r.Shadow.MaxCSMResolution", 2048 },
            { "r.Shadow.CSM.MaxCascades", 3 },
            { "r.Shadow.DistanceScale", 0.85 },
            { "r.DepthOfFieldQuality", 1 },
            { "r.SSR.Quality", 1 },
        },

        -- Balanced, plus low-resolution shadows, no screen-space reflections, coarser volumetric fog, shorter view
        -- distance for foliage and props, thinner grass
        Performance = {
            { "r.MotionBlurQuality", 0 },
            { "r.MotionBlur.Max", 0 },
            { "r.SceneColorFringeQuality", 0 },
            { "r.LensFlareQuality", 0 },
            { "a.URO.Enable", 1 },
            { "r.Shadow.MaxCSMResolution", 1024 },
            { "r.Shadow.MaxResolution", 1024 },
            { "r.Shadow.CSM.MaxCascades", 2 },
            { "r.Shadow.DistanceScale", 0.7 },
            { "r.DepthOfFieldQuality", 0 },
            { "r.SSR.Quality", 0 },
            { "r.VolumetricFog.GridPixelSize", 16 },
            { "r.VolumetricFog.GridSizeZ", 64 },
            { "r.AmbientOcclusionLevels", 1 },
            { "r.ViewDistanceScale", 0.8 },
            { "foliage.LODDistanceScale", 0.8 },
            { "grass.DensityScale", 0.7 },
        },

        -- everything cheap: no volumetric fog, minimal shadows, short view distance, fewer particles
        Max = {
            { "r.MotionBlurQuality", 0 },
            { "r.MotionBlur.Max", 0 },
            { "r.SceneColorFringeQuality", 0 },
            { "r.LensFlareQuality", 0 },
            { "a.URO.Enable", 1 },
            { "r.Shadow.MaxCSMResolution", 512 },
            { "r.Shadow.MaxResolution", 512 },
            { "r.Shadow.CSM.MaxCascades", 1 },
            { "r.Shadow.DistanceScale", 0.5 },
            { "r.DepthOfFieldQuality", 0 },
            { "r.SSR.Quality", 0 },
            { "r.VolumetricFog", 0 },
            { "r.AmbientOcclusionLevels", 0 },
            { "r.ViewDistanceScale", 0.6 },
            { "foliage.LODDistanceScale", 0.6 },
            { "grass.DensityScale", 0.4 },
            { "r.EmitterSpawnRateScale", 0.75 },
            { "r.MaxAnisotropy", 4 },
        },
    },
}
