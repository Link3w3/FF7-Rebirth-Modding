-- MeteorStrike: your Sephiroth's Meteor (the ATB move PC0010_T_Meteor and his limit level 3) as a cinematic.
--   He flies high up into the sky in a glowing pink aura (his own body aura turned pink, and a pink light), raises his
--   sword and calls it (his cast: KH2's MASAFINISH). A giant meteor (the game's
--   FA0260_01 Sephiroth meteor) appears high in the sky beyond his target and slowly comes down on it while a cinematic
--   camera watches, first from below as he rises, then from up beside him in the sky. It crashes in a great explosion,
--   more explosions ripple out all around, Titan's rocks burst up out of the ground around a cracked crater (it stays a
--   while, then sinks back), and the impact hits every enemy near it (PC0010_Meteor_Impact). He comes back down, then
--   the camera goes back to you. He can't be hurt from the cast until the camera is back (EndBattleAPI
--   SetDisableDamageHit). The flight lifts his model (CONFIG.flight); where the game has him (his capsule) stays on the
--   ground.
-- The call comes when his cast makes PC0010_Meteor (a damage source that hits nothing, FullyPlayableSephirothDataAssets_P),
-- or CONFIG.callAfter seconds into the move. The meteor, the explosions and the crater are preloaded by Create a
-- Character System (compat\SephirothForms.json "preload").
-- UE4SS.log lines start with "meteor:". An error inside a UE4SS call ends only that step; the cinematic always cleans
-- up (camera back, actors gone, invincibility off) when it is over, the battle ends or he is gone.
local M = {}

local CONFIG = {
    enabled = true,
    stepSeconds = 0.016,    -- how often it moves the meteor and the camera while the cinematic plays
    moves = { PC0010_T_Meteor = true, PC0000_Limit003 = true, PC0010_Limit003 = true },
    signal = "PC0010_Meteor",   -- the damage source his cast makes when his hand goes up
    callAfter = 2.5,            -- ... or the call this long into the move
    meteor = {
        class = "/Game/BluePrint/Character/Property/FA0260_01_SephirothMeteor_Battle.FA0260_01_SephirothMeteor_Battle_C",
        scale = 0.12,           -- its body is about 200 m across at 1.0 (and its debris a kilometre around)
        height = 26000.0,       -- it appears this high above the impact (cm) ...
        beyond = 14000.0,       -- ... and this far beyond it, away from him (cm)
        fallSeconds = 7.5,      -- how long it takes to come down
        ease = 2.2,             -- > 1: it starts slow and speeds up as it falls
        spin = 9.0,             -- how fast it turns while it falls (degrees per second)
        follow = 0.25,          -- how much of the target's movement the impact point follows each second (0..1)
    },
    impact = {
        damage = "PC0010_Meteor_Impact",  -- the impact's damage source (on his target, 45 m around)
        -- explosions: effect, how far from the impact (cm, random up to), when (s after the impact), scale, how many (and
        -- seconds: it is stopped after that long, for an effect that would go on)
        explosions = {
            { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_WeightBomb_Exp_01.FX_SU2000_WeightBomb_Exp_01", radius = 0, at = 0.0, scale = 4.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_BombBullet_Exp_01.FX_SU2050_BombBullet_Exp_01", radius = 0, at = 0.05, scale = 5.0, count = 1 },
            -- Titan: rocks bursting out of the ground (his Rock Throw) and his Jump Punch's shock
            { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_RockThrow_Storm_01.FX_SU2000_RockThrow_Storm_01", radius = 0, at = 0.05, scale = 3.0, count = 1, seconds = 2.5 },
            { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_Stamp_Shock_01.FX_SU2000_Stamp_Shock_01", radius = 0, at = 0.1, scale = 6.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_JumpPunch_Shock_01.FX_SU2000_JumpPunch_Shock_01", radius = 0, at = 0.12, scale = 5.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_Cmn_GroundHit_01.FX_SU2050_Cmn_GroundHit_01", radius = 0, at = 0.15, scale = 6.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU0000_Ifrit/Particle/FX_SU0000_Drop_Exp_01.FX_SU0000_Drop_Exp_01", radius = 2200, at = 0.2, scale = 2.5, count = 8, spread = 1.2 },
            { path = "/Game/Effect/Ability/Fire01/Particle/FX_Fire03_Hit_01.FX_Fire03_Hit_01", radius = 3500, at = 0.5, scale = 3.0, count = 10, spread = 1.6 },
            { path = "/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_BombBullet_Exp_01.FX_SU2050_BombBullet_Exp_01", radius = 4500, at = 0.9, scale = 3.0, count = 6, spread = 1.4 },
        },
        -- The crater, from Titan: his rocks burst up out of the ground in rings around the impact (each partly in the ground,
        -- leaning out), the game's ground cracks lie under them and his smoke drifts over it. It stays `seconds`, then sinks
        -- into the ground in `sink` s. Every piece sits on the ground where it is (the ground's height is looked up there).
        -- (The game's ground cracks are flat models with a surface material, not decals: a decal can't draw them.)
        crater = {
            seconds = 30.0, sink = 3.0,
            rise = 0.45,            -- the rocks come up out of the ground in this long (each a moment after the other)
            most = 2,               -- craters at once: the oldest sinks when another comes
            rocks = {
                -- his rocks (the models his effects throw): how wide and how high each is at scale 1 (cm)
                meshes = {
                    { path = "/Game/Effect/Character/Summon/SU2000_Titan/Model/FX_SU2000_Rock_01.FX_SU2000_Rock_01", across = 90.0, high = 91.0 },
                    { path = "/Game/Effect/Character/Summon/SU2000_Titan/Model/FX_SU2000_Rock_Red_01.FX_SU2000_Rock_Red_01", across = 88.0, high = 89.0 },
                    { path = "/Game/Effect/Character/Summon/SU2000_Titan/Model/FX_SU2000_Rock_Red_02.FX_SU2000_Rock_Red_02", across = 78.0, high = 71.0 },
                },
                -- rings of rocks: how far out (cm, from..to), how many, how big (cm across, from..to), how far they lean out
                -- (degrees, from..to) and how much of each is in the ground (0..1)
                rings = {
                    { radius = { 1600, 2300 }, count = 16, size = { 300, 560 }, lean = { 15, 40 }, buried = 0.4 },  -- the rim
                    { radius = { 350, 1300 }, count = 8, size = { 110, 230 }, lean = { 0, 70 }, buried = 0.35 },    -- rubble in it
                    { radius = { 2500, 4000 }, count = 14, size = { 60, 180 }, lean = { 0, 90 }, buried = 0.25 },   -- thrown out
                },
            },
            -- the game's ground crack (a flat model, `long` cm long, its middle `center` off its origin), several, each turned
            -- another way: how long each is (cm)
            cracks = {
                mesh = "/Game/Environment/Building/Model/Decal_B_GroundCrack_01A.Decal_B_GroundCrack_01A",
                long = 129.4, center = { 10.4, 7.6 },
                sizes = { 3400, 2600, 1800, 1200 },
            },
            -- Titan's smoke over the rim (at some of its rocks): effect, how many, scale, when (s after the impact), how long
            smoke = {
                { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_Common_Smoke_01.FX_SU2000_Common_Smoke_01", count = 5, scale = 3.0, at = 0.6, seconds = 10.0 },
            },
        },
        hold = 3.0,             -- the camera stays on the impact this long
    },
    -- His flight: his model rises this high (cm) above where he stands, `delay` s into the move, in `rise` s; it comes back
    -- down `after` s after the impact, in `descend` s. Feathers burst where he takes off.
    flight = {
        enabled = true,
        height = 2500.0,
        delay = 0.15, rise = 1.6,
        after = 0.8, descend = 1.6,
        takeoff = { { path = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_01.FX_EV_FOREE_7250_BlackFeather_01", scale = 1.5 } },
        -- His aura while he flies: his own body aura (the game's FX_PC0010_Aura_Body_01, on his model), turned pink, and a
        -- pink light that moves with him. The aura's colours are built into the effect, so the pink is put on its materials:
        -- each of `tintParams` is set to `tint` (it multiplies the aura's own colour; above 1 is brighter).
        aura = {
            enabled = true,
            path = "/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Aura_Body_01.FX_PC0010_Aura_Body_01",
            socket = "None",
            tint = { R = 1.6, G = 0.35, B = 0.85, A = 1.0 },
            tintParams = { "ParticleEmitColorTop", "ParticleEmitColorBottom", "EmitterGeometryEmitColorTop", "EmitterGeometryEmitColorBottom", "ParticleLitColor" },
            tintEvery = 0.1,        -- how often the pink is put on again (the game can make the aura's materials late)
            -- the light: its colour, how bright (candelas) and how far it reaches (cm), how high on him (cm), how much it
            -- pulses (0..1), and how much it glows in fog. It is as bright as he is high up (it comes and goes with the flight).
            light = { enabled = true, color = { R = 1.0, G = 0.25, B = 0.65, A = 1.0 }, candelas = 4000.0, radius = 550.0, up = 110.0,
                      pulse = 0.15, scatter = 3.0 },
        },
    },
    camera = {
        enabled = true,
        -- from the start of the move: in front of him, low, looking up at him as he rises
        rise = { front = 1100.0, side = 450.0, up = 120.0, look = 150.0 },
        -- from `after` s past the call: behind him up in the sky (at his height), watching the meteor, then the impact
        sky = { after = 1.0, behind = 1500.0, side = 650.0, up = 250.0 },
        backAway = 600.0,       -- it moves back this far while the meteor falls
        fov = 80.0,
        blendIn = 0.6, blendOut = 1.2,
        move = 1.5,             -- how fast it moves to its next place (higher: snappier)
        turn = 4.0,             -- how fast it turns to what it watches (higher: snappier)
    },
    invincible = true,
    maxSeconds = 25.0,          -- the cinematic ends after this long, whatever happens
}

local H = nil           -- from main.lua: log, valid, str, battleApi
local char = nil        -- your Sephiroth (main.lua's tick)
local show = nil        -- the cinematic playing
local loopBusy = false

local function now() return os.clock() end
local function log(text) H.log("meteor: " .. text) end
local function valid(object) return H.valid(object) end

local names = {}
local function N(text)
    local n = names[text]
    if n == nil then
        n = FName(text)
        names[text] = n
    end
    return n
end

local function statics() return StaticFindObject("/Script/Engine.Default__GameplayStatics") end

local function loadObject(path)
    local object = StaticFindObject(path)
    if valid(object) then return object end
    local ok, loaded = pcall(function() return LoadAsset(path) end)
    if ok and valid(loaded) then return loaded end
    return nil
end

local function vec(x, y, z) return { X = x, Y = y, Z = z } end
local function add(a, b) return vec(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
local function sub(a, b) return vec(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
local function mul(a, s) return vec(a.X * s, a.Y * s, a.Z * s) end
local function lerp(a, b, u) return vec(a.X + (b.X - a.X) * u, a.Y + (b.Y - a.Y) * u, a.Z + (b.Z - a.Z) * u) end
local function flat(a)
    local len = math.sqrt(a.X * a.X + a.Y * a.Y)
    if len < 0.001 then return vec(1, 0, 0) end
    return vec(a.X / len, a.Y / len, 0)
end

local function where(actor)
    local v = actor:K2_GetActorLocation()
    return vec(v.X, v.Y, v.Z)
end

local function ground(actor)
    local p = where(actor)
    local comp = actor.CapsuleComponent
    if valid(comp) then p.Z = p.Z - comp:GetScaledCapsuleHalfHeight() end
    return p
end

-- the rotation looking from `from` at `to` (degrees)
local function lookAt(from, to)
    local d = sub(to, from)
    local yaw = math.deg(math.atan(d.Y, d.X))
    local pitch = math.deg(math.atan(d.Z, math.sqrt(d.X * d.X + d.Y * d.Y)))
    return { Pitch = pitch, Yaw = yaw, Roll = 0.0 }
end

local function angleTowards(a, b, k)
    local d = (b - a + 180.0) % 360.0 - 180.0
    return a + d * k
end

local function transform(at, yaw, scale)
    local h = math.rad(yaw or 0) / 2
    return { Rotation = { X = 0.0, Y = 0.0, Z = math.sin(h), W = math.cos(h) }, Translation = at,
             Scale3D = vec(scale or 1.0, scale or 1.0, scale or 1.0) }
end

-- an actor of `class` at `at` (it doesn't collide)
local function spawn(class, at, yaw, scale)
    local gs = statics()
    local t = transform(at, yaw, scale)
    local actor = gs:BeginDeferredActorSpawnFromClass(char, class, t, 1, nil)  -- 1: always spawn
    if not valid(actor) then return nil end
    gs:FinishSpawningActor(actor, t)
    actor:SetActorEnableCollision(false)
    return actor
end

-- an effect (Niagara or Cascade) at a place; its component
local function effectAt(path, at, scale, yaw)
    local system = loadObject(path)
    if not valid(system) then
        log("effect " .. path:match("([^/%.]+)$") .. " is not loaded")
        return nil
    end
    local className = H.str(system:GetClass():GetFName())
    local turn = { Pitch = 0.0, Yaw = yaw or 0.0, Roll = 0.0 }
    local size = vec(scale, scale, scale)
    if string.find(className, "Niagara", 1, true) then
        local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
        -- SpawnSystemAtLocation(World, System, Location, Rotation, Scale, bAutoDestroy, bAutoActivate, no pooling, bPreCullCheck)
        return lib:SpawnSystemAtLocation(char, system, at, turn, size, true, true, 0, false)
    end
    -- SpawnEmitterAtLocation(World, Emitter, Location, Rotation, Scale, bAutoDestroy, no pooling, bAutoActivate)
    return statics():SpawnEmitterAtLocation(char, system, at, turn, size, true, 0, true)
end

-- a rotation (degrees) as a quaternion
local function quat(pitch, yaw, roll)
    local p, y, r = math.rad(pitch) / 2, math.rad(yaw) / 2, math.rad(roll) / 2
    local sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return { X = cr * sp * sy - sr * cp * cy, Y = -cr * sp * cy - sr * cp * sy, Z = cr * cp * sy - sr * sp * cy, W = cr * cp * cy + sr * sp * sy }
end

-- a model (StaticMesh) of the game at a place: a movable StaticMeshActor that doesn't collide
local function spawnMesh(mesh, at, rot, scale)
    local cls = StaticFindObject("/Script/Engine.StaticMeshActor")
    if not valid(cls) then return nil end
    local gs = statics()
    local t = { Rotation = quat(rot.Pitch, rot.Yaw, rot.Roll), Translation = at, Scale3D = vec(scale, scale, scale) }
    local actor = gs:BeginDeferredActorSpawnFromClass(char, cls, t, 1, nil)  -- 1: always spawn
    if not valid(actor) then return nil end
    actor:SetMobility(2)                    -- movable (it comes up out of the ground and sinks back)
    local comp = actor.StaticMeshComponent
    if valid(comp) then
        comp:SetStaticMesh(mesh)
        comp:SetCollisionEnabled(0)         -- no collision
    end
    gs:FinishSpawningActor(actor, t)
    actor:SetActorEnableCollision(false)
    return actor
end

-- ---------------------------------------------------------------------------------------------------------------
-- the cinematic
-- ---------------------------------------------------------------------------------------------------------------
local function setInvincible(on)
    if not CONFIG.invincible or not valid(char) then return end
    local a = H.battleApi()
    if a then a:SetDisableDamageHit(char, on) end
end

local function playerController()
    local pc = statics():GetPlayerController(char, 0)
    return valid(pc) and pc or nil
end

-- ---- his flight: his model (mesh) lifted above his capsule, which the game keeps on the ground
local function smooth(u) return u * u * (3.0 - 2.0 * u) end
local function easeOut(u) return 1.0 - (1.0 - u) ^ 3 end

-- How high his model is now (cm) in the flight's timeline.
local function liftAt(s, t)
    local f = CONFIG.flight
    if not f.enabled or not s.meshBase then return 0.0 end
    local up = easeOut(math.max(0.0, math.min(1.0, (t - s.start - f.delay) / f.rise)))
    if s.impacted then
        local down = smooth(math.max(0.0, math.min(1.0, (t - s.impacted - f.after) / f.descend)))
        up = up * (1.0 - down)
    end
    return f.height * up
end

-- Puts his model `z` cm above where it belongs. In a call of its own (the next game tick), so a refusal by the engine
-- only skips the flight: a call that has not come back after half a second was refused, and the flight stops there.
local function setLift(s, z)
    if not s.meshBase or s.liftFailed then return end
    if s.liftPending then
        if now() - s.liftPending > 0.5 then
            s.liftFailed = true
            log("flight: his model can't be moved (K2_SetRelativeLocation refused); he stays on the ground")
        end
        return
    end
    if s.lift and math.abs(s.lift - z) < 0.05 then return end
    local mesh, b = char.Mesh, s.meshBase
    s.liftPending = now()
    ExecuteInGameThread(function()
        if valid(mesh) then mesh:K2_SetRelativeLocation(vec(b.X, b.Y, b.Z + z), false, {}, true) end
        s.liftPending = nil
        s.lift = z
    end)
end

local function startFlight(s)
    if not CONFIG.flight.enabled then return end
    local ok, base = pcall(function()
        local r = char.Mesh.RelativeLocation
        return vec(r.X, r.Y, r.Z)
    end)
    if not ok or type(base) ~= "table" or type(base.Z) ~= "number" then
        log("flight: his model's place is unknown (" .. tostring(base) .. "); he stays on the ground")
        return
    end
    s.meshBase = base
    s.lift = 0.0
    for _, e in ipairs(CONFIG.flight.takeoff or {}) do pcall(effectAt, e.path, s.base, e.scale or 1.0, 0.0) end
    log(string.format("flight: up %.0f m in %.1f s", CONFIG.flight.height / 100.0, CONFIG.flight.rise))
end

-- His model back on the ground (the cinematic's end, whatever ended it), in a call of its own.
local function endFlight(s)
    if not s.meshBase or s.liftFailed or not s.lift or s.lift == 0.0 then return end
    local mesh, b = valid(char) and char.Mesh or nil, s.meshBase
    s.lift = 0.0
    if not valid(mesh) then return end
    ExecuteInGameThread(function()
        if valid(mesh) then mesh:K2_SetRelativeLocation(vec(b.X, b.Y, b.Z), false, {}, true) end
    end)
    log("flight: back on the ground")
end

-- Where his model is in the world now (his capsule's place lifted).
local function body(s)
    return add(where(char), vec(0, 0, s.lift or 0.0))
end

-- ---- his aura while he flies (CONFIG.flight.aura): his body aura on his model, tinted pink, and a pink light
local function className(object)
    local ok, name = pcall(function() return H.str(object:GetClass():GetFName()) end)
    return ok and name or "?"
end

-- His body aura on his model, in a call of its own (an engine refusal only skips the aura).
local function spawnAura(s)
    local a = CONFIG.flight.aura
    local system = loadObject(a.path)
    if not valid(system) then
        log("aura: " .. a.path:match("([^/%.]+)$") .. " is not loaded")
        s.auraFailed = true
        return
    end
    local mesh = char.Mesh
    s.auraPending = now()
    ExecuteInGameThread(function()
        s.auraPending = nil
        if not valid(mesh) then return end
        local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
        -- SpawnSystemAttached(System, AttachTo, Socket, Location, Rotation, SnapToTarget, bAutoDestroy, bAutoActivate, no pooling, bPreCullCheck)
        local comp = lib:SpawnSystemAttached(system, mesh, N(a.socket or "None"), vec(0, 0, 0), { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }, 2, true, true, 0, false)
        if valid(comp) then
            s.aura = comp
            s.auraSpawns = (s.auraSpawns or 0) + 1
            s.auraMids, s.midSearches, s.midSearchNext = nil, 0, now() + 0.2
            log("aura: his body aura is on him (pink)")
        else
            s.auraFailed = true
            log("aura: his body aura didn't start")
        end
    end)
end

-- The pink on the aura's materials (the dynamic materials the game made for it), in a call of its own.
local function tintAura(s)
    local a = CONFIG.flight.aura
    local comp = s.aura
    if (s.tintStarted or 0) - (s.tintDone or 0) >= 5 then
        if not s.tintGaveUp then
            s.tintGaveUp = true
            log("aura: its materials refuse the pink (it stays its own colour; the light is still pink)")
        end
        return
    end
    -- The game makes the aura's dynamic materials itself (inside the aura, a little after it starts): they are found
    -- among all the dynamic materials by whose they are, a few times until there are some (each search a call of its
    -- own). The component's own list of them is not read: reading it fails in the game.
    local t = now()
    local mids = s.auraMids or {}
    if #mids == 0 then
        if s.midSearchPending or t < (s.midSearchNext or 0) or (s.midSearches or 0) >= 6 then return end
        s.midSearches = (s.midSearches or 0) + 1
        s.midSearchNext = t + 0.25 * s.midSearches
        s.midSearchPending = true
        ExecuteInGameThread(function()
            s.midSearchPending = nil
            if not valid(comp) then return end
            local mine = comp:GetAddress()
            local found = {}
            for _, m in ipairs(FindAllOf("MaterialInstanceDynamic") or {}) do
                local ok, outer = pcall(function() return m:GetOuter() end)
                if ok and valid(outer) and outer:GetAddress() == mine then table.insert(found, m) end
            end
            s.auraMids = found
            if #found > 0 then
                log(string.format("aura: %d of its materials found", #found))
            elseif s.midSearches >= 6 then
                log("aura: it has no materials of its own to turn pink (it stays its own colour; the light is still pink)")
            end
        end)
        return
    end
    s.tintPending = now()
    ExecuteInGameThread(function()
        s.tintPending = nil
        s.tintStarted = (s.tintStarted or 0) + 1
        local tinted = 0
        for _, mid in ipairs(mids) do
            if valid(mid) then
                for _, name in ipairs(a.tintParams) do
                    mid:SetVectorParameterValue(N(name), a.tint)
                end
                tinted = tinted + 1
            end
        end
        if tinted > 0 and tinted ~= s.auraTinted then
            log(string.format("aura: pink on %d of its materials", tinted))
        end
        s.auraTinted = tinted
        if tinted == 0 then s.auraMids = nil end   -- (they went: look again)
        s.tintDone = (s.tintDone or 0) + 1
    end)
end

-- The pink light: a movable point light on his model.
local function spawnAuraLight(s)
    local l = CONFIG.flight.aura.light
    local cls = StaticFindObject("/Script/Engine.PointLight")
    if not valid(cls) then
        log("aura: no light (no PointLight class)")
        return
    end
    local actor = spawn(cls, add(body(s), vec(0, 0, l.up)), 0.0, 1.0)
    if not valid(actor) then
        log("aura: the light didn't spawn")
        return
    end
    s.light = actor
    local comp = actor.PointLightComponent
    if not valid(comp) then comp = actor.LightComponent end
    if not valid(comp) then
        log("aura: the light has no light component")
        return
    end
    s.lightComp = comp
    local mesh = char.Mesh
    -- dark first, in a call of its own; it only lights up once it is pink (lightReady)
    ExecuteInGameThread(function()
        if valid(comp) then comp:SetIntensity(0.0) end
    end)
    ExecuteInGameThread(function()
        if not valid(comp) then return end
        comp:SetMobility(2)                 -- movable
        comp:SetIntensityUnits(1)           -- candelas
        comp:SetLightColor(l.color, true)
        comp:SetAttenuationRadius(l.radius)
        comp:SetSourceRadius(20.0)
        comp:SetCastShadows(false)
        comp:SetVolumetricScatteringIntensity(l.scatter)
        s.lightReady = true
        if valid(mesh) and comp:K2_AttachToComponent(mesh, N("None"), 2, 2, 2, false) then
            comp:K2_SetRelativeLocation(vec(0, 0, l.up), false, {}, true)
            s.lightAttached = true
        end
        log("aura: the pink light is on him" .. (s.lightAttached and "" or " (it follows him each step)"))
    end)
end

local function startAura(s)
    local a = CONFIG.flight.aura
    if not a or not a.enabled then return end
    s.auraOn = true
    s.tintNext = now()
    local okAura, errAura = pcall(spawnAura, s)
    if not okAura then log("aura error " .. tostring(errAura)) end
    if a.light and a.light.enabled then
        local okLight, errLight = pcall(spawnAuraLight, s)
        if not okLight then log("aura light error " .. tostring(errLight)) end
    end
end

-- Each step while it plays: the pink again, the light as bright as he is high up (it pulses), and the aura back if it ended.
local function updateAura(s, t)
    if not s.auraOn then return end
    local a = CONFIG.flight.aura
    if valid(s.aura) then
        if t >= s.tintNext and not s.tintPending then
            s.tintNext = t + a.tintEvery
            tintAura(s)
        end
        if not s.impacted and t >= (s.activeCheck or 0) then
            s.activeCheck = t + 1.0
            local ok, active = pcall(function() return s.aura:IsActive() end)
            if ok and active == false and (s.auraSpawns or 0) < 4 then
                s.aura = nil
                spawnAura(s)
            end
        end
    elseif not s.auraFailed and not s.auraPending and not s.impacted and (s.auraSpawns or 0) > 0 and (s.auraSpawns or 0) < 4 then
        spawnAura(s)  -- it ended by itself: again
    end
    local l = a.light
    if s.lightReady and valid(s.lightComp) then
        local up = CONFIG.flight.enabled and not s.liftFailed and CONFIG.flight.height > 0 and math.min(1.0, (s.lift or 0.0) / CONFIG.flight.height) or 1.0
        local glow = l.candelas * up * (1.0 + l.pulse * math.sin(t * 6.0))
        s.lightComp:SetIntensity(glow)
        if not s.lightAttached and valid(s.light) then
            s.light:K2_TeleportTo(add(body(s), vec(0, 0, l.up)), { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 })
        end
    end
end

-- The aura's end (the cinematic's end, whatever ended it): it stops (its last particles fade), the light goes.
local function endAura(s)
    if not s.auraOn then return end
    s.auraOn = false
    local comp, light = s.aura, s.light
    s.aura, s.light, s.lightComp = nil, nil, nil
    ExecuteInGameThread(function()
        if valid(comp) then comp:Deactivate() end
    end)
    ExecuteInGameThread(function()
        if valid(light) then light:K2_DestroyActor() end
    end)
    log("aura: off")
end

-- ---- the camera
local function startCamera(s)
    if not CONFIG.camera.enabled then return end
    local cls = StaticFindObject("/Script/Engine.CameraActor")
    local pc = playerController()
    if not valid(cls) or not pc then
        log("no camera (" .. (pc and "no CameraActor class" or "no player controller") .. ")")
        return
    end
    local c = CONFIG.camera
    local me = where(char)
    local fwd = flat(sub(s.towards, me))
    local right = vec(-fwd.Y, fwd.X, 0)
    s.camAt = add(add(add(me, mul(fwd, c.rise.front)), mul(right, c.rise.side)), vec(0, 0, c.rise.up))
    s.camRot = lookAt(s.camAt, add(me, vec(0, 0, c.rise.look)))
    local cam = spawn(cls, s.camAt, s.camRot.Yaw, 1.0)
    if not cam then
        log("the camera didn't spawn")
        return
    end
    cam:K2_TeleportTo(s.camAt, s.camRot)
    local comp = cam.CameraComponent
    if valid(comp) then comp:SetFieldOfView(c.fov) end
    local manager = pc.PlayerCameraManager
    local before = nil
    if valid(manager) then
        local ok, target = pcall(function() return manager.ViewTarget.Target end)
        if ok and valid(target) then before = target end
    end
    s.cam, s.pc, s.viewBefore = cam, pc, before or char
    pc:SetViewTargetWithBlend(cam, c.blendIn, 4, 2.0, false)  -- 4: ease in and out
    log("camera on him (it was on " .. H.str(s.viewBefore:GetFName()) .. ")")
end

-- The camera's place up in the sky beside him: behind him (away from the impact), at his flight's height.
local function skyPlace(s, u)
    local c = CONFIG.camera
    local away = flat(sub(s.impact, s.base))
    local right = vec(-away.Y, away.X, 0)
    local high = add(s.base, vec(0, 0, CONFIG.flight.enabled and not s.liftFailed and CONFIG.flight.height or 0.0))
    return add(add(add(high, mul(away, -(c.sky.behind + c.backAway * u))), mul(right, c.sky.side)), vec(0, 0, c.sky.up))
end

-- Moves the camera towards `place` and turns it towards `look` (both smoothed).
local function moveCamera(s, dt, place, look)
    if not valid(s.cam) then return end
    local c = CONFIG.camera
    s.camAt = lerp(s.camAt, place, math.min(1.0, dt * c.move))
    local want = lookAt(s.camAt, look)
    local k = math.min(1.0, dt * c.turn)
    s.camRot = { Pitch = angleTowards(s.camRot.Pitch, want.Pitch, k), Yaw = angleTowards(s.camRot.Yaw, want.Yaw, k), Roll = 0.0 }
    s.cam:K2_TeleportTo(s.camAt, s.camRot)
end

local function endCamera(s)
    if s.pc and valid(s.pc) and s.cam then
        local back = valid(s.viewBefore) and s.viewBefore or char
        if valid(back) then s.pc:SetViewTargetWithBlend(back, CONFIG.camera.blendOut, 4, 2.0, false) end
    end
    if valid(s.cam) then s.cam:SetLifeSpan(CONFIG.camera.blendOut + 0.5) end
    s.cam = nil
end

local function finish(s, why)
    if s.finished then return end
    s.finished = true
    if valid(s.meteor) then s.meteor:K2_DestroyActor() end
    s.meteor = nil
    endCamera(s)
    setInvincible(false)
    pcall(endAura, s)
    pcall(endFlight, s)
    show = nil
    log("over (" .. why .. ")")
end

local function call(s, why)
    s.called = now()
    local mc = CONFIG.meteor
    local me = s.base
    s.impact = valid(s.target) and ground(s.target) or add(ground(char), mul(flat(char:GetActorForwardVector()), 1500.0))
    local away = flat(sub(s.impact, me))
    s.meteorFrom = add(s.impact, add(mul(away, mc.beyond), vec(0, 0, mc.height)))
    s.meteorAt = s.meteorFrom
    local cls = loadObject(mc.class)
    if valid(cls) then
        s.meteor = spawn(cls, s.meteorFrom, 0.0, mc.scale)
        if valid(s.meteor) then s.meteor:SetActorScale3D(vec(mc.scale, mc.scale, mc.scale)) end
    end
    log(string.format("the call (%s): %s comes down on %s in %.1f s", why, valid(s.meteor) and "the meteor" or "NO METEOR (its class isn't loaded)",
        valid(s.target) and H.str(s.target:GetFName()) or "the ground in front of him", mc.fallSeconds))
end

-- ---- the crater (CONFIG.impact.crater): Titan's rocks in rings, the game's ground cracks, Titan's smoke. It outlives the
-- cinematic: updateCraters (each step of the loop) brings the rocks up, ends the smoke and sinks it all at its end.
local craters = {}          -- { born, pieces = { { actor, at, kind, depth, delay, scale } }, smoke = { { comp, ends } }, sinkAt }
local timed = {}            -- effects stopped after a while: { comp, ends }
local traceBroken = false   -- the ground's height can't be looked up (the trace failed once): everything at the impact's height
local missing = {}          -- models that aren't loaded (said once)

local function between(range) return range[1] + (range[2] - range[1]) * math.random() end

-- Where each piece goes: rocks in rings (x, y, rotation, scale, how high its middle is above the ground, how deep it
-- starts), cracks at the middle.
local function craterPlan(center)
    local c = CONFIG.impact.crater
    local plan = {}
    for _, ring in ipairs(c.rocks.rings) do
        local turn = math.random() * 360.0
        for k = 1, ring.count do
            local angle = turn + (k - 1 + 0.8 * math.random()) * 360.0 / ring.count
            local r = between(ring.radius)
            local m = c.rocks.meshes[math.random(#c.rocks.meshes)]
            local scale = between(ring.size) / m.across
            local high = m.high * scale
            local a = math.rad(angle)
            table.insert(plan, {
                kind = "rock", mesh = m.path, x = center.X + math.cos(a) * r, y = center.Y + math.sin(a) * r,
                -- facing out from the middle; pitched down = its top leans out
                rot = { Pitch = -between(ring.lean), Yaw = angle + 30.0 * (math.random() - 0.5), Roll = 40.0 * (math.random() - 0.5) },
                scale = scale, lift = high * (0.5 - ring.buried), depth = high + 40.0, delay = 0.3 * math.random(),
            })
        end
    end
    local cr = c.cracks
    for k, long in ipairs(cr.sizes) do
        local scale = long / cr.long
        local yaw = math.random() * 360.0 + k * 47.0
        -- its middle on the impact: its origin is `center` (turned, scaled) away from its middle
        local a = math.rad(yaw)
        local ox, oy = cr.center[1] * scale, cr.center[2] * scale
        table.insert(plan, {
            kind = "crack", mesh = cr.mesh, x = center.X - (ox * math.cos(a) - oy * math.sin(a)), y = center.Y - (ox * math.sin(a) + oy * math.cos(a)),
            rot = { Pitch = 0.0, Yaw = yaw, Roll = 0.0 }, scale = scale, lift = 3.0 + 1.5 * k, depth = 0.0, delay = 0.0, middle = true,
        })
    end
    return plan
end

local function crater(s)
    local c = CONFIG.impact.crater
    if not c then return end
    local t = now()
    -- at most `most` at once: the oldest goes now
    local standing = 0
    for _, old in ipairs(craters) do if not old.sinkAt then standing = standing + 1 end end
    for _, old in ipairs(craters) do
        if standing < c.most then break end
        if not old.sinkAt then old.sinkAt = t; standing = standing - 1 end
    end
    local center = s.impact
    local plan = craterPlan(center)
    local rec = { born = t, pieces = {}, smoke = {}, planned = #plan }
    table.insert(craters, rec)
    -- the ground's height under each piece, in a call of its own (a refusal leaves them at the impact's height)
    local heights = {}
    local traced = traceBroken
    if not traceBroken then
        ExecuteInGameThread(function()
            local lib = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
            if not valid(lib) or not valid(char) then traced = true; return end
            local none = { R = 0.0, G = 0.0, B = 0.0, A = 0.0 }
            local function groundAt(x, y)
                local hit = {}
                -- LineTraceSingleForObjects(World, Start, End, ObjectTypes {WorldStatic}, bTraceComplex, ActorsToIgnore,
                --   DrawDebugType None, OutHit, bIgnoreSelf, TraceColor, TraceHitColor, DrawTime)
                local ok = lib:LineTraceSingleForObjects(char, vec(x, y, center.Z + 600.0), vec(x, y, center.Z - 3500.0), { 0 }, false, {}, 0, hit, true, none, none, 0.0)
                local z = ok and hit.ImpactPoint and hit.ImpactPoint.Z
                if type(z) == "number" and z > center.Z - 3500.0 and z < center.Z + 600.0 then return z end
                return nil
            end
            heights.middle = groundAt(center.X, center.Y)
            for k, p in ipairs(plan) do
                if not p.middle then heights[k] = groundAt(p.x, p.y) end
            end
            traced = true
            local n = 0
            for _ in pairs(heights) do n = n + 1 end
            log(string.format("crater: the ground's height found under %d of %d places", n, #plan + 1 - #CONFIG.impact.crater.cracks.sizes))
        end)
    end
    -- each piece in a call of its own (an engine refusal only skips that piece)
    for k, p in ipairs(plan) do
        ExecuteInGameThread(function()
            if not traced then
                traced, traceBroken = true, true
                log("crater: the ground's height can't be looked up (the trace failed); it sits at the impact's height")
            end
            if not valid(char) then return end
            local mesh = loadObject(p.mesh)
            if not valid(mesh) then
                if not missing[p.mesh] then
                    missing[p.mesh] = true
                    log("crater: " .. p.mesh:match("([^/%.]+)$") .. " is not loaded")
                end
                return
            end
            local z = (p.middle and heights.middle or heights[k]) or heights.middle or center.Z
            local at = vec(p.x, p.y, z + p.lift)
            local actor = spawnMesh(mesh, vec(at.X, at.Y, at.Z - p.depth), p.rot, p.scale)
            if valid(actor) then
                actor:SetLifeSpan(c.seconds + c.sink + 10.0)   -- (gone by itself if the crater is never sunk)
                table.insert(rec.pieces, { actor = actor, at = at, kind = p.kind, depth = p.depth, delay = p.delay, scale = p.scale })
            end
            if k == #plan then
                log(string.format("crater: %d pieces (Titan's rocks, the ground cracks)", #rec.pieces))
            end
        end)
    end
    -- Titan's smoke over the rim, at some of its rocks
    local rim = {}
    for k, p in ipairs(plan) do if p.kind == "rock" and k <= CONFIG.impact.crater.rocks.rings[1].count then table.insert(rim, p) end end
    for _, e in ipairs(c.smoke or {}) do
        for n = 1, e.count do
            local p = rim[1 + math.floor((n - 1) * #rim / e.count)]
            if p then
                table.insert(s.pending, { path = e.path, at = vec(p.x, p.y, center.Z), when = t + e.at + 0.15 * n, scale = e.scale,
                                          yaw = math.random() * 360.0, smokeOf = rec, smokeFor = e.seconds })
            end
        end
    end
end

local function placePiece(p, down)
    if valid(p.actor) then p.actor:K2_SetActorLocation(vec(p.at.X, p.at.Y, p.at.Z - down), false, {}, true) end
end

-- Each step of the loop (also after the cinematic): the rocks come up, the smoke ends, the crater sinks at its end;
-- effects that would go on are stopped.
local function updateCraters(t)
    for i = #timed, 1, -1 do
        local fx = timed[i]
        if t >= fx.ends then
            table.remove(timed, i)
            if valid(fx.comp) then fx.comp:Deactivate() end
        end
    end
    local c = CONFIG.impact.crater
    for i = #craters, 1, -1 do
        local rec = craters[i]
        if not rec.sinkAt and t - rec.born >= c.seconds then rec.sinkAt = t end
        for _, p in ipairs(rec.pieces) do
            if valid(p.actor) then
                if rec.sinkAt then
                    local u = smooth(math.min(1.0, (t - rec.sinkAt) / c.sink))
                    if p.kind == "crack" then
                        local k = math.max(0.001, 1.0 - u)   -- the cracks close up
                        p.actor:SetActorScale3D(vec(p.scale * k, p.scale * k, p.scale))
                    else
                        placePiece(p, p.depth * u)
                    end
                elseif p.kind == "rock" and not p.up then
                    local u = (t - rec.born - p.delay) / c.rise
                    if u >= 1.0 then
                        p.up = true
                        placePiece(p, 0.0)
                    elseif u > 0.0 then
                        placePiece(p, p.depth * (1.0 - easeOut(u)))
                    end
                end
            end
        end
        for _, fx in ipairs(rec.smoke) do
            if not fx.ended and (t >= fx.ends or rec.sinkAt) then
                fx.ended = true
                if valid(fx.comp) then fx.comp:Deactivate() end
            end
        end
        if rec.sinkAt and t - rec.sinkAt >= c.sink then
            for _, p in ipairs(rec.pieces) do
                if valid(p.actor) then p.actor:K2_DestroyActor() end
            end
            table.remove(craters, i)
            log("crater: gone")
        end
    end
end

local function impact(s)
    s.impacted = now()
    if valid(s.meteor) then s.meteor:SetActorHiddenInGame(true) end
    -- the hit (his own hits must land: no damage-hit block on him while it is out)
    local a = H.battleApi()
    if a and valid(s.target) then
        setInvincible(false)
        s.reguard = s.impacted + 1.0
        a:CreateDamageSource(N(CONFIG.impact.damage), char, s.target, N(s.ability), false, 0)
    end
    s.pending = {}
    local okCrater, errCrater = pcall(crater, s)
    if not okCrater then log("crater error " .. tostring(errCrater)) end
    local smoke = #s.pending
    -- the explosions, each at its time
    for _, e in ipairs(CONFIG.impact.explosions) do
        for k = 1, e.count do
            local angle = math.random() * math.pi * 2
            local dist = e.radius * math.sqrt(math.random())
            local at = add(s.impact, vec(math.cos(angle) * dist, math.sin(angle) * dist, 0))
            table.insert(s.pending, { path = e.path, at = at, when = s.impacted + e.at + (e.spread or 0) * (k - 1) / math.max(1, e.count),
                                      scale = e.scale * (0.8 + 0.4 * math.random()), yaw = math.random() * 360.0, stopAfter = e.seconds })
        end
    end
    log(string.format("impact at (%.0f, %.0f, %.0f): %d explosions, the crater (%d smoke)", s.impact.X, s.impact.Y, s.impact.Z, #s.pending - smoke, smoke))
end

local function step(dt)
    local s = show
    local t = now()
    if not valid(char) then
        finish(s, "he is gone")
        return
    end
    local a = H.battleApi()
    if t > s.start + CONFIG.maxSeconds then
        finish(s, "time")
        return
    end
    if a and a:IsInBattle() == false then
        finish(s, "the battle ended")
        return
    end
    setLift(s, liftAt(s, t))
    local okAura, errAura = pcall(updateAura, s, t)
    if not okAura and not s.auraError then
        s.auraError = true
        log("aura error " .. tostring(errAura))
    end
    if not s.called then
        if (a and a:HasDamageSource(char, N(CONFIG.signal))) or t >= s.start + CONFIG.callAfter then
            call(s, t >= s.start + CONFIG.callAfter and "time" or "his sword is up")
        end
        moveCamera(s, dt, s.camAt, add(body(s), vec(0, 0, CONFIG.camera.rise.look)))
        return
    end
    if not s.impacted then
        local mc = CONFIG.meteor
        if valid(s.target) then s.impact = lerp(s.impact, ground(s.target), math.min(1.0, dt * mc.follow)) end
        local u = math.min(1.0, (t - s.called) / mc.fallSeconds)
        local e = u ^ mc.ease
        s.meteorAt = lerp(s.meteorFrom, s.impact, e)
        if valid(s.meteor) then
            s.meteor:K2_TeleportTo(s.meteorAt, { Pitch = (t - s.called) * mc.spin * 0.6, Yaw = (t - s.called) * mc.spin, Roll = 0.0 })
        end
        if t < s.called + CONFIG.camera.sky.after then
            moveCamera(s, dt, s.camAt, add(body(s), vec(0, 0, CONFIG.camera.rise.look)))  -- still on him
        else
            moveCamera(s, dt, skyPlace(s, u), s.meteorAt)
        end
        if u >= 1.0 then impact(s) end
        return
    end
    -- after the impact: the explosions go off, the camera holds, then back to you
    if s.reguard and t >= s.reguard then
        s.reguard = nil
        setInvincible(true)
    end
    local keep = {}
    for _, e in ipairs(s.pending) do
        if e.when <= t then
            -- each in a call of its own (a refusal only skips that one)
            ExecuteInGameThread(function()
                local comp = effectAt(e.path, e.at, e.scale, e.yaw)
                if e.smokeOf and valid(comp) then table.insert(e.smokeOf.smoke, { comp = comp, ends = now() + e.smokeFor }) end
                if e.stopAfter and valid(comp) then table.insert(timed, { comp = comp, ends = now() + e.stopAfter }) end
            end)
        else
            table.insert(keep, e)
        end
    end
    s.pending = keep
    moveCamera(s, dt, skyPlace(s, 1.0), s.impact)
    if t >= s.impacted + CONFIG.impact.hold and #s.pending == 0 then finish(s, "done") end
end

local function start(ability)
    local a = H.battleApi()
    local target = a and a:GetTargetCharacter(char) or nil
    show = { ability = ability, start = now(), target = valid(target) and target or nil, base = where(char) }
    local s = show
    s.towards = s.target and where(s.target) or add(s.base, mul(flat(char:GetActorForwardVector()), 1500.0))
    setInvincible(true)
    log(string.format("%s: he calls the meteor down on %s", ability, s.target and H.str(s.target:GetFName()) or "the ground in front of him"))
    local okFlight, errFlight = pcall(startFlight, s)
    if not okFlight then log("flight error " .. tostring(errFlight)) end
    local okAura, errAura = pcall(startAura, s)
    if not okAura then log("aura error " .. tostring(errAura)) end
    local okCam, errCam = pcall(startCamera, s)
    if not okCam then log("camera error " .. tostring(errCam)) end
end

local lastAbility = "None"
local lastStep = 0
local function tick()
    if not CONFIG.enabled then return end
    local t = now()
    local dt = math.max(0.0, math.min(0.1, t - lastStep))
    lastStep = t
    if show then
        local s = show
        local ok, err = pcall(step, dt)
        if not ok then
            log("error " .. tostring(err))
            pcall(finish, s, "error")
        end
        return
    end
    if not valid(char) then return end
    local a = H.battleApi()
    if not a then return end
    local ability = H.str(a:GetCurrentAbilityID(char))
    if ability ~= lastAbility then
        lastAbility = ability
        if CONFIG.moves[ability] then start(ability) end
    end
end

-- main.lua's tick (every 200 ms): who your Sephiroth is
function M.tick(character)
    char = character
    if show and not valid(character) then
        -- the cleanup runs in the loop (on the game thread)
    end
end

function M.init(helpers)
    H = helpers
    math.randomseed(os.time())
    local ms = math.max(10, math.floor(CONFIG.stepSeconds * 1000))
    local craterBusy = false
    LoopAsync(ms, function()
        if CONFIG.enabled and (char ~= nil or show ~= nil) and not loopBusy then
            loopBusy = true
            ExecuteInGameThread(function()
                loopBusy = false
                local ok, err = pcall(tick)
                if not ok then log("error " .. tostring(err)) end
            end)
        end
        -- the craters (they outlive the cinematic), in a call of their own
        if (#craters > 0 or #timed > 0) and not craterBusy then
            craterBusy = true
            ExecuteInGameThread(function()
                craterBusy = false
                local ok, err = pcall(updateCraters, now())
                if not ok then log("crater error " .. tostring(err)) end
            end)
        end
        return false
    end)
    H.log("MeteorStrike " .. (CONFIG.enabled and "on" or "off") .. ": Meteor is a cinematic (he flies up into the sky, the meteor comes down, explosions, a crater; he can't be hurt meanwhile)")
end

return M
