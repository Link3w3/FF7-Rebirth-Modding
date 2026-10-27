-- armed capture: waits until you control a character in the world (and the world runs) for 8 seconds, then captures once
local function capture()
    -- Rebirth game lighting capture (RebirthLiveLink "lua" command, game thread).
    -- Reads the live lights, sky light, fog, atmosphere, clouds, reflection captures, post process (volumes, components,
    -- the active camera) and the renderer's console variables, and writes link\lighting_capture.json.
    local LINK = link and link.dir or "."
    local MAX_DEPTH = 4
    local out = { version = 1, time = os.time(), notes = {} }

    local function note(s) out.notes[#out.notes + 1] = tostring(s) end
    local function valid(o)
        if o == nil then return false end
        local ok, v = pcall(function() return o:IsValid() end)
        return ok and v
    end
    local function fname(o) local ok, v = pcall(function() return o:GetFName():ToString() end) return ok and v or nil end
    local function full(o) local ok, v = pcall(function() return o:GetFullName() end) return ok and v or nil end
    local function clsname(o) local ok, v = pcall(function() return o:GetClass():GetFName():ToString() end) return ok and v or "?" end

    local SIMPLE = { FloatProperty = true, DoubleProperty = true, IntProperty = true, Int8Property = true, Int16Property = true,
        Int64Property = true, UInt16Property = true, UInt32Property = true, UInt64Property = true, ByteProperty = true,
        EnumProperty = true, BoolProperty = true }

    local readValue   -- forward

    local function readStruct(sv, st, depth)
        if depth > MAX_DEPTH then return "(deep)" end
        local t = {}
        local s = st
        local guard = 0
        while valid(s) and guard < 8 do
            guard = guard + 1
            pcall(function()
                s:ForEachProperty(function(p)
                    local n = fname(p)
                    if n then
                        local ok, v = pcall(function() return readValue(sv[n], p, depth + 1) end)
                        if ok and v ~= nil then t[n] = v end
                    end
                end)
            end)
            local ok, sup = pcall(function() return s:GetSuperStruct() end)
            s = ok and sup or nil
        end
        return t
    end

    readValue = function(v, p, depth)
        local kind = "?"
        pcall(function() kind = p:GetClass():GetFName():ToString() end)
        if SIMPLE[kind] then
            if type(v) == "number" or type(v) == "boolean" then return v end
            return nil
        elseif kind == "NameProperty" or kind == "StrProperty" or kind == "TextProperty" then
            local ok, s = pcall(function() return v:ToString() end)
            return ok and s or nil
        elseif kind == "ObjectProperty" or kind == "ClassProperty" or kind == "WeakObjectProperty" then
            if valid(v) then return full(v) end
            return false
        elseif kind == "SoftObjectProperty" or kind == "SoftClassProperty" then
            local ok, s = pcall(function() return v:ToString() end)
            return ok and s or nil
        elseif kind == "StructProperty" then
            local st = nil
            pcall(function() st = p:GetStruct() end)
            if not valid(st) then return nil end
            return readStruct(v, st, depth)
        elseif kind == "ArrayProperty" then
            local inner = nil
            pcall(function() inner = p:GetInner() end)
            local arr = {}
            local num = 0
            pcall(function() num = v:GetArrayNum() end)
            if num == 0 then return {} end
            if inner == nil then return { count = num } end
            pcall(function()
                v:ForEach(function(i, el)
                    if #arr < 48 then
                        local ok, x = pcall(function() return readValue(el:get(), inner, depth + 1) end)
                        arr[#arr + 1] = ok and x or false
                    end
                end)
            end)
            if num > #arr then arr[#arr + 1] = string.format("(%d more)", num - #arr) end
            return arr
        end
        return nil
    end

    -- every property of `o` declared on its class chain from the most derived class up to (not including) `stopAt`
    local function readObject(o, stopAt, skip)
        local t = {}
        local cls = nil
        pcall(function() cls = o:GetClass() end)
        local guard = 0
        while valid(cls) and guard < 24 do
            guard = guard + 1
            local cn = fname(cls)
            if stopAt[cn] then break end
            pcall(function()
                cls:ForEachProperty(function(p)
                    local n = fname(p)
                    if n and not (skip and skip[n]) and t[n] == nil then
                        local ok, v = pcall(function() return readValue(o[n], p, 1) end)
                        if ok and v ~= nil then t[n] = v end
                    end
                end)
            end)
            local ok, sup = pcall(function() return cls:GetSuperStruct() end)
            cls = ok and sup or nil
        end
        return t
    end

    -- the post process settings that are switched on (bOverride_X), with their values
    local function overridden(pp)
        if type(pp) ~= "table" then return pp end
        local t = {}
        for k, v in pairs(pp) do
            local name = k:match("^bOverride_(.+)$")
            if name and v == true then t[name] = pp[name] == nil and true or pp[name] end
        end
        for _, k in ipairs({ "WeightedBlendables" }) do
            if pp[k] ~= nil then t[k] = pp[k] end
        end
        return t
    end

    local function vec(v)
        if v == nil then return nil end
        local ok, r = pcall(function() return { v.X, v.Y, v.Z } end)
        return ok and r or nil
    end
    local function rot(v)
        if v == nil then return nil end
        local ok, r = pcall(function() return { v.Pitch, v.Yaw, v.Roll } end)
        return ok and r or nil
    end

    local function placement(c)
        local t = {}
        pcall(function() t.location = vec(c:K2_GetComponentLocation()) end)
        pcall(function() t.rotation = rot(c:K2_GetComponentRotation()) end)
        pcall(function() t.scale = vec(c:K2_GetComponentScale()) end)
        pcall(function() t.visible = c:IsVisible() end)
        pcall(function() t.registered = c:IsRegistered() end)
        local owner = nil
        pcall(function() owner = c:GetOwner() end)
        if valid(owner) then
            t.owner = full(owner)
            t.owner_class = clsname(owner)
            pcall(function() t.owner_hidden = owner.bHidden end)
        end
        return t
    end

    local seen = {}
    local function gather(classNames, stopAt, skip, kind, maxN)
        local list = {}
        for _, cn in ipairs(classNames) do
            local ok, found = pcall(function() return FindAllOf(cn) end)
            if ok and found then
                for _, o in ipairs(found) do
                    local key = full(o)
                    if key and not seen[key] and valid(o) and not key:find("Default__", 1, true) and #list < (maxN or 400) then
                        seen[key] = true
                        local rec = { name = key, class = clsname(o), kind = kind }
                        local okP, pl = pcall(placement, o)
                        if okP then rec.placement = pl end
                        local okR, props = pcall(readObject, o, stopAt, skip)
                        rec.props = okR and props or ("error " .. tostring(props))
                        list[#list + 1] = rec
                    end
                end
            end
        end
        return list
    end

    local STOP_COMPONENT = { SceneComponent = true, ActorComponent = true, Object = true }
    local SKIP = { AttachChildren = true, ClientAttachedChildren = true, AssetUserData = true, ComponentTags = true,
        OnComponentActivated = true, OnComponentDeactivated = true, PhysicsVolumeChangedEvent = true }

    -- the area
    pcall(function()
        local pc = FindFirstOf("PlayerController")
        if valid(pc) then
            local pawn = pc.Pawn
            if valid(pawn) then
                out.player = { pawn = full(pawn) }
                pcall(function() out.player.location = vec(pawn:K2_GetActorLocation()) end)
            end
            local pcm = pc.PlayerCameraManager
            if valid(pcm) then
                out.camera = { manager = full(pcm), class = clsname(pcm) }
                pcall(function() out.camera.location = vec(pcm:GetCameraLocation()) end)
                pcall(function() out.camera.rotation = rot(pcm:GetCameraRotation()) end)
                pcall(function() out.camera.fov = pcm:GetFOVAngle() end)
                local vt = nil
                pcall(function() vt = pcm.ViewTarget.Target end)
                if valid(vt) then out.camera.view_target = full(vt) end
            end
            local w = nil
            pcall(function() w = pc:GetWorld() end)
            if valid(w) then out.world = full(w) end
        end
    end)
    pcall(function()
        local levels = {}
        for _, cn in ipairs({ "LevelStreamingDynamic", "LevelStreamingAlwaysLoaded", "LevelStreaming" }) do
            local ok, found = pcall(function() return FindAllOf(cn) end)
            if ok and found then
                for _, ls in ipairs(found) do
                    local rec = nil
                    pcall(function()
                        local loaded = ls:GetLoadedLevel()
                        if valid(loaded) then
                            local nm = full(loaded)
                            rec = nm
                        end
                    end)
                    if rec and #levels < 300 then levels[#levels + 1] = rec end
                end
            end
        end
        out.loaded_levels = levels
    end)

    local t0 = os.clock()
    -- the sun, the moon, the sky light: everything they have
    out.lights = gather({ "DirectionalLightComponent", "SkyLightComponent" }, STOP_COMPONENT, SKIP, "light", 40)
    out.timing = { main_lights_ms = math.floor((os.clock() - t0) * 1000) }
    -- local lights near the camera: the fields that light a model
    local camLoc = out.camera and out.camera.location or (out.player and out.player.location)
    local LOCAL_FIELDS = { "Intensity", "IntensityUnits", "LightColor", "Temperature", "bUseTemperature", "AttenuationRadius",
        "SourceRadius", "SoftSourceRadius", "SourceLength", "InnerConeAngle", "OuterConeAngle", "SourceWidth", "SourceHeight",
        "BarnDoorAngle", "BarnDoorLength", "CastShadows", "bAffectsWorld", "Mobility", "IndirectLightingIntensity",
        "VolumetricScatteringIntensity", "SpecularScale", "bUseInverseSquaredFalloff", "LightFalloffExponent", "LightingChannels",
        "bCastShadowsFromCinematicObjectsOnly", "MaxDrawDistance", "MaxDistanceFadeRange", "ShadowBias", "ContactShadowLength",
        "bVisible", "bHiddenInGame" }
    out.local_lights = {}
    out.local_lights_total = 0
    pcall(function()
        local cand = {}
        for _, cn in ipairs({ "PointLightComponent", "SpotLightComponent", "RectLightComponent" }) do
            local ok, found = pcall(function() return FindAllOf(cn) end)
            if ok and found then
                for _, o in ipairs(found) do
                    local key = full(o)
                    if key and not seen[key] and not key:find("Default__", 1, true) and valid(o) then
                        seen[key] = true
                        out.local_lights_total = out.local_lights_total + 1
                        local loc = nil
                        pcall(function() loc = vec(o:K2_GetComponentLocation()) end)
                        local d = 1e30
                        if loc and camLoc then
                            local dx, dy, dz = loc[1] - camLoc[1], loc[2] - camLoc[2], loc[3] - camLoc[3]
                            d = math.sqrt(dx * dx + dy * dy + dz * dz)
                        end
                        cand[#cand + 1] = { o = o, key = key, d = d }
                    end
                end
            end
        end
        table.sort(cand, function(a, b) return a.d < b.d end)
        for i = 1, math.min(#cand, 96) do
            local c = cand[i]
            local rec = { name = c.key, class = clsname(c.o), distance = c.d < 1e29 and c.d or nil, props = {} }
            local okP, pl = pcall(placement, c.o)
            if okP then rec.placement = pl end
            local cls = nil
            pcall(function() cls = c.o:GetClass() end)
            for _, f in ipairs(LOCAL_FIELDS) do
                pcall(function()
                    local prop = nil
                    local s = cls
                    local g = 0
                    while valid(s) and not prop and g < 12 do
                        g = g + 1
                        pcall(function() s:ForEachProperty(function(p) if fname(p) == f then prop = p end end) end)
                        local ok2, sup = pcall(function() return s:GetSuperStruct() end)
                        s = ok2 and sup or nil
                    end
                    if prop then rec.props[f] = readValue(c.o[f], prop, 1) end
                end)
            end
            out.local_lights[#out.local_lights + 1] = rec
        end
    end)
    out.timing.local_lights_ms = math.floor((os.clock() - t0) * 1000)
    out.fog = gather({ "ExponentialHeightFogComponent", "AtmosphericFogComponent", "SkyAtmosphereComponent",
        "VolumetricCloudComponent" }, STOP_COMPONENT, SKIP, "fog", 50)
    out.timing.fog_ms = math.floor((os.clock() - t0) * 1000)
    -- reflection captures: where they are and how bright
    out.reflection_captures = {}
    pcall(function()
        for _, cn in ipairs({ "SphereReflectionCaptureComponent", "BoxReflectionCaptureComponent", "PlaneReflectionCaptureComponent" }) do
            local ok, found = pcall(function() return FindAllOf(cn) end)
            if ok and found then
                for _, o in ipairs(found) do
                    local key = full(o)
                    if key and not key:find("Default__", 1, true) and valid(o) and #out.reflection_captures < 300 then
                        local rec = { name = key, class = clsname(o) }
                        pcall(function() rec.location = vec(o:K2_GetComponentLocation()) end)
                        for _, f in ipairs({ "Brightness", "InfluenceRadius", "BoxTransitionDistance", "CaptureOffset", "Mobility", "ReflectionSourceType", "Cubemap", "SourceCubemapAngle" }) do
                            pcall(function()
                                local x = o[f]
                                if type(x) == "number" or type(x) == "boolean" then rec[f] = x
                                elseif valid(x) then rec[f] = full(x)
                                elseif x ~= nil then local ok3, vv = pcall(function() return vec(x) end); if ok3 and vv then rec[f] = vv end end
                            end)
                        end
                        out.reflection_captures[#out.reflection_captures + 1] = rec
                    end
                end
            end
        end
    end)
    out.timing.reflections_ms = math.floor((os.clock() - t0) * 1000)

    -- post process volumes (their settings: only what they switch on)
    out.post_process = {}
    pcall(function()
        for _, cn in ipairs({ "PostProcessVolume" }) do
            local ok, found = pcall(function() return FindAllOf(cn) end)
            if ok and found then
                for _, v in ipairs(found) do
                    local key = full(v)
                    if key and not key:find("Default__", 1, true) and valid(v) and #out.post_process < 200 then
                        local rec = { name = key, class = clsname(v) }
                        for _, f in ipairs({ "BlendWeight", "BlendRadius", "Priority", "bEnabled", "bUnbound", "bHidden" }) do
                            pcall(function() rec[f] = v[f] end)
                        end
                        pcall(function()
                            local p = v:GetClass():GetPropertyByNameInChain("Settings")
                            if p then rec.settings = overridden(readValue(v.Settings, p, 1)) end
                        end)
                        if rec.settings == nil then
                            pcall(function()
                                local st = StaticFindObject("/Script/Engine.PostProcessSettings")
                                rec.settings = overridden(readStruct(v.Settings, st, 1))
                            end)
                        end
                        pcall(function() rec.location = vec(v:K2_GetActorLocation()) end)
                        out.post_process[#out.post_process + 1] = rec
                    end
                end
            end
        end
    end)
    -- post process components (and the camera components) the same way
    local function ppComponents(cn, kind, limit)
        local list = {}
        local ok, found = pcall(function() return FindAllOf(cn) end)
        if ok and found then
            local st = StaticFindObject("/Script/Engine.PostProcessSettings")
            for _, c in ipairs(found) do
                local key = full(c)
                if key and not key:find("Default__", 1, true) and valid(c) and #list < limit then
                    local rec = { name = key, class = clsname(c), kind = kind }
                    for _, f in ipairs({ "BlendWeight", "BlendRadius", "Priority", "bEnabled", "bUnbound", "PostProcessBlendWeight", "FieldOfView", "bIsActive" }) do
                        pcall(function() local x = c[f]; if type(x) == "number" or type(x) == "boolean" then rec[f] = x end end)
                    end
                    pcall(function() rec.settings = overridden(readStruct(c.Settings, st, 1)) end)
                    if rec.settings == nil or next(rec.settings) == nil then
                        pcall(function() rec.settings = overridden(readStruct(c.PostProcessSettings, st, 1)) end)
                    end
                    pcall(function() rec.placement = placement(c) end)
                    list[#list + 1] = rec
                end
            end
        end
        return list
    end
    out.post_process_components = ppComponents("PostProcessComponent", "component", 100)
    out.cameras = ppComponents("CameraComponent", "camera", 40)

    -- the renderer's console variables that shape the look
    out.cvars = {}
    pcall(function()
        local ksl = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        for _, name in ipairs({ "r.Tonemapper.Sharpen", "r.TonemapperGamma", "r.TonemapperFilm", "r.Tonemapper.GrainQuantization",
            "r.Tonemapper.Quality", "r.Color.Min", "r.Color.Mid", "r.Color.Max", "r.Bloom.Cross", "r.BloomQuality",
            "r.DefaultFeature.AutoExposure", "r.DefaultFeature.AutoExposure.Method", "r.DefaultFeature.AutoExposure.Bias",
            "r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange", "r.DefaultFeature.Bloom", "r.DefaultFeature.AmbientOcclusion",
            "r.DefaultFeature.AmbientOcclusionStaticFraction", "r.DefaultFeature.MotionBlur", "r.DefaultFeature.LensFlare",
            "r.EyeAdaptationQuality", "r.EyeAdaptation.ExponentialTransitionDistance", "r.EyeAdaptation.MethodOverride",
            "r.EyeAdaptation.ExposureOffset", "r.EyeAdaptation.LensAttenuation", "r.EyeAdaptation.BlackHistogramBucketInfluence",
            "r.EyeAdaptation.PreExposureOverride", "r.UsePreExposure", "r.SceneColorFormat", "r.SceneColorFringeQuality",
            "r.SkyLightingQuality", "r.SupportSkyAtmosphere", "r.SkyAtmosphere", "r.VolumetricFog", "r.VolumetricFog.GridPixelSize",
            "r.VolumetricFog.GridSizeZ", "r.SSR.Quality", "r.SSR.MaxRoughness", "r.AmbientOcclusionLevels", "r.AmbientOcclusion.Intensity",
            "r.Shadow.CSM.MaxCascades", "r.Shadow.DistanceScale", "r.ContactShadows", "r.CapsuleShadows", "r.LightFunctionQuality",
            "r.DiffuseIndirect.Denoiser", "r.ReflectionEnvironment", "r.ReflectionEnvironmentLightmapMixing",
            "r.ReflectionEnvironmentLightmapMixBasedOnRoughness", "r.ReflectionEnvironmentBeginMixingRoughness",
            "r.ReflectionEnvironmentEndMixingRoughness", "r.SkylightIntensityMultiplier", "r.Mobile.TonemapperFilm",
            "r.DOF.Kernel.MaxForegroundRadius", "r.PostProcessAAQuality", "r.TemporalAA.Upsampling", "r.ScreenPercentage",
            "r.Upscale.Quality", "r.HDR.EnableHDROutput", "r.HDR.Display.OutputDevice", "r.HDR.UI.CompositeMode", "r.Gamma",
            "r.DisplayGamma", "r.ColorGrading", "r.SSGI.Enable", "r.SSGI.Quality", "r.LightMaxDrawDistanceScale", "r.SubsurfaceScattering",
            "r.SSS.Quality", "r.SSS.Scale", "r.HairStrands.Enable", "r.ToneMapping", "r.AllowStaticLighting",
            "r.DistanceFieldAO", "r.DistanceFieldShadowing", "r.GenerateMeshDistanceFields" }) do
            local okf, f = pcall(function() return ksl:GetConsoleVariableFloatValue(name) end)
            local oki, i = pcall(function() return ksl:GetConsoleVariableIntValue(name) end)
            out.cvars[name] = { f = okf and f or nil, i = oki and i or nil }
        end
    end)

    -- JSON
    local function esc(s)
        return (s:gsub('[%c"\\]', function(c)
            if c == '"' then return '\\"' elseif c == '\\' then return '\\\\' elseif c == '\n' then return '\\n'
            elseif c == '\t' then return '\\t' else return string.format('\\u%04x', c:byte()) end
        end))
    end
    local function enc(v, depth)
        depth = depth or 0
        local t = type(v)
        if t == "nil" then return "null"
        elseif t == "boolean" then return v and "true" or "false"
        elseif t == "number" then
            if v ~= v or v == math.huge or v == -math.huge then return "null" end
            if math.type and math.type(v) == "integer" then return tostring(v) end
            return string.format("%.9g", v)
        elseif t == "string" then return '"' .. esc(v) .. '"'
        elseif t == "table" then
            if depth > 12 then return '"(deep)"' end
            local n = #v
            local isArr = n > 0 or next(v) == nil
            if isArr then
                for k, _ in pairs(v) do if type(k) ~= "number" then isArr = false break end end
            end
            local parts = {}
            if isArr then
                for i = 1, n do parts[#parts + 1] = enc(v[i], depth + 1) end
                return "[" .. table.concat(parts, ",") .. "]"
            end
            local keys = {}
            for k, _ in pairs(v) do keys[#keys + 1] = tostring(k) end
            table.sort(keys)
            for _, k in ipairs(keys) do
                local x = v[k]
                if x == nil then x = v[tonumber(k)] end
                parts[#parts + 1] = '"' .. esc(k) .. '":' .. enc(x, depth + 1)
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
        return '"' .. esc(tostring(v)) .. '"'
    end

    local text = enc(out)
    local path = LINK .. "/lighting_capture.json"
    local f = io.open(path, "wb")
    if f then f:write(text); f:close() end
    return { written = path, bytes = #text, lights = #out.lights, local_lights = #out.local_lights, local_lights_total = out.local_lights_total, fog = #out.fog, reflection_captures = #out.reflection_captures, timing = out.timing,
        post_process = #out.post_process, post_process_components = #out.post_process_components, cameras = #out.cameras,
        world = out.world }

end

local st = { since = nil, tries = 0 }
link.every("lighting_capture", function()
    st.tries = st.tries + 1
    local ok, ready = pcall(function()
        local pc = FindFirstOf("PlayerController")
        if not (pc and pc:IsValid()) then return false end
        local pawn = pc.Pawn
        if not (pawn and pawn:IsValid()) then return false end
        local cls = pawn:GetClass():GetFName():ToString()
        return cls ~= "DefaultPawn" and cls ~= "SpectatorPawn"
    end)
    if not (ok and ready) then st.since = nil return end
    st.since = st.since or os.clock()
    if os.clock() - st.since < 8.0 then return end
    link.cancel("lighting_capture")
    local okc, res = pcall(capture)
    local f = io.open(link.dir .. "/lighting_capture_status.txt", "wb")
    if f then
        if okc and type(res) == "table" then
            f:write("ok " .. tostring(res.written) .. " bytes=" .. tostring(res.bytes) .. " lights=" .. tostring(res.lights) .. " local=" .. tostring(res.local_lights) .. " pp=" .. tostring(res.post_process) .. " world=" .. tostring(res.world) .. "\n")
        else
            f:write("error " .. tostring(res) .. "\n")
        end
        f:close()
    end
end, 1.0)
return "armed: captures 8 s after you control a character in the world"
