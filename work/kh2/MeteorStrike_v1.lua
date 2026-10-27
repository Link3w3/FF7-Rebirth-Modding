-- MeteorStrike: your Sephiroth's Meteor (the ATB move PC0010_T_Meteor and his limit level 3) as a cinematic.
--   He raises his hand and calls it. A giant meteor (the game's FA0260_01 Sephiroth meteor) appears high in the sky
--   beyond his target and slowly comes down on it while a cinematic camera watches. It crashes in a great explosion,
--   more explosions ripple out all around, the ground is left cracked in a huge crater, and the impact hits every enemy
--   near it (PC0010_Meteor_Impact). Then the camera goes back to you. He can't be hurt from the cast until the camera
--   is back (EndBattleAPI SetDisableDamageHit).
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
        -- explosions: effect, how far from the impact (cm, random up to), when (s after the impact), scale, how many
        explosions = {
            { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_WeightBomb_Exp_01.FX_SU2000_WeightBomb_Exp_01", radius = 0, at = 0.0, scale = 4.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_BombBullet_Exp_01.FX_SU2050_BombBullet_Exp_01", radius = 0, at = 0.05, scale = 5.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_Stamp_Shock_01.FX_SU2000_Stamp_Shock_01", radius = 0, at = 0.1, scale = 6.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_Cmn_GroundHit_01.FX_SU2050_Cmn_GroundHit_01", radius = 0, at = 0.15, scale = 6.0, count = 1 },
            { path = "/Game/Effect/Character/Summon/SU0000_Ifrit/Particle/FX_SU0000_Drop_Exp_01.FX_SU0000_Drop_Exp_01", radius = 2200, at = 0.2, scale = 2.5, count = 8, spread = 1.2 },
            { path = "/Game/Effect/Ability/Fire01/Particle/FX_Fire03_Hit_01.FX_Fire03_Hit_01", radius = 3500, at = 0.5, scale = 3.0, count = 10, spread = 1.6 },
            { path = "/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_BombBullet_Exp_01.FX_SU2050_BombBullet_Exp_01", radius = 4500, at = 0.9, scale = 3.0, count = 6, spread = 1.4 },
        },
        -- the crater: ground-crack decals at the impact (cm, half sizes: across, depth projected), for `seconds`, then
        -- they fade
        crater = {
            material = "/Game/Environment/Building/Material/M_Decal_B_GroundCrack_01A.M_Decal_B_GroundCrack_01A",
            decals = { { size = 2600.0, depth = 1500.0 }, { size = 1500.0, depth = 1500.0 }, { size = 800.0, depth = 1500.0 } },
            seconds = 30.0, fade = 4.0,
        },
        hold = 3.0,             -- the camera stays on the impact this long
    },
    camera = {
        enabled = true,
        behind = 900.0,         -- it is this far behind him (cm) ...
        side = 450.0,           -- ... this far to his side ...
        up = 160.0,             -- ... and this high, looking up at the meteor
        backAway = 600.0,       -- it moves back this far while the meteor falls
        fov = 80.0,
        blendIn = 1.0, blendOut = 1.2,
        turn = 4.0,             -- how fast it turns to follow the meteor (higher: snappier)
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

-- an effect (Niagara or Cascade) at a place
local function effectAt(path, at, scale, yaw)
    local system = loadObject(path)
    if not valid(system) then
        log("effect " .. path:match("([^/%.]+)$") .. " is not loaded")
        return
    end
    local className = H.str(system:GetClass():GetFName())
    local turn = { Pitch = 0.0, Yaw = yaw or 0.0, Roll = 0.0 }
    local size = vec(scale, scale, scale)
    if string.find(className, "Niagara", 1, true) then
        local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
        -- SpawnSystemAtLocation(World, System, Location, Rotation, Scale, bAutoDestroy, bAutoActivate, no pooling, bPreCullCheck)
        lib:SpawnSystemAtLocation(char, system, at, turn, size, true, true, 0, false)
    else
        -- SpawnEmitterAtLocation(World, Emitter, Location, Rotation, Scale, bAutoDestroy, no pooling, bAutoActivate)
        statics():SpawnEmitterAtLocation(char, system, at, turn, size, true, 0, true)
    end
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

local function startCamera(s)
    if not CONFIG.camera.enabled then return end
    local cls = StaticFindObject("/Script/Engine.CameraActor")
    local pc = playerController()
    if not valid(cls) or not pc then
        log("no camera (" .. (pc and "no CameraActor class" or "no player controller") .. ")")
        return
    end
    local me = where(char)
    local away = flat(sub(s.impact, me))
    local right = vec(-away.Y, away.X, 0)
    s.camFrom = add(add(add(me, mul(away, -CONFIG.camera.behind)), mul(right, CONFIG.camera.side)), vec(0, 0, CONFIG.camera.up))
    s.camAway = mul(away, -CONFIG.camera.backAway)
    s.camRot = lookAt(s.camFrom, s.meteorAt)
    local cam = spawn(cls, s.camFrom, s.camRot.Yaw, 1.0)
    if not cam then
        log("the camera didn't spawn")
        return
    end
    cam:K2_TeleportTo(s.camFrom, s.camRot)
    local comp = cam.CameraComponent
    if valid(comp) then comp:SetFieldOfView(CONFIG.camera.fov) end
    local manager = pc.PlayerCameraManager
    local before = nil
    if valid(manager) then
        local ok, target = pcall(function() return manager.ViewTarget.Target end)
        if ok and valid(target) then before = target end
    end
    s.cam, s.pc, s.viewBefore = cam, pc, before or char
    pc:SetViewTargetWithBlend(cam, CONFIG.camera.blendIn, 4, 2.0, false)  -- 4: ease in and out
    log("camera on the meteor (it was on " .. H.str(s.viewBefore:GetFName()) .. ")")
end

local function moveCamera(s, dt, look, u)
    if not valid(s.cam) then return end
    local at = add(s.camFrom, mul(s.camAway, u))
    local want = lookAt(at, look)
    local k = math.min(1.0, dt * CONFIG.camera.turn)
    s.camRot = { Pitch = angleTowards(s.camRot.Pitch, want.Pitch, k), Yaw = angleTowards(s.camRot.Yaw, want.Yaw, k), Roll = 0.0 }
    s.cam:K2_TeleportTo(at, s.camRot)
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
    show = nil
    log("over (" .. why .. ")")
end

local function call(s, why)
    s.called = now()
    local mc = CONFIG.meteor
    local me = where(char)
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
    startCamera(s)
end

local function crater(s)
    local c = CONFIG.impact.crater
    local material = loadObject(c.material)
    if not valid(material) then
        log("no crater: its decal material isn't loaded")
        return
    end
    local yaw = math.random() * 360.0
    for i, d in ipairs(c.decals) do
        -- decals project along their X: pitch -90 looks straight down
        local comp = statics():SpawnDecalAtLocation(char, material, vec(d.depth, d.size, d.size), add(s.impact, vec(0, 0, 50)),
            { Pitch = -90.0, Yaw = 0.0, Roll = yaw + i * 47.0 }, c.seconds + c.fade)
        if valid(comp) then comp:SetFadeOut(c.seconds, c.fade, false) end
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
    crater(s)
    -- the explosions, each at its time
    s.pending = {}
    for _, e in ipairs(CONFIG.impact.explosions) do
        for k = 1, e.count do
            local angle = math.random() * math.pi * 2
            local dist = e.radius * math.sqrt(math.random())
            local at = add(s.impact, vec(math.cos(angle) * dist, math.sin(angle) * dist, 0))
            table.insert(s.pending, { path = e.path, at = at, when = s.impacted + e.at + (e.spread or 0) * (k - 1) / math.max(1, e.count),
                                      scale = e.scale * (0.8 + 0.4 * math.random()), yaw = math.random() * 360.0 })
        end
    end
    log(string.format("impact at (%.0f, %.0f, %.0f): %d explosions", s.impact.X, s.impact.Y, s.impact.Z, #s.pending))
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
    if not s.called then
        if (a and a:HasDamageSource(char, N(CONFIG.signal))) or t >= s.start + CONFIG.callAfter then
            call(s, t >= s.start + CONFIG.callAfter and "time" or "his hand is up")
        end
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
        moveCamera(s, dt, s.meteorAt, u)
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
        if e.when <= t then effectAt(e.path, e.at, e.scale, e.yaw) else table.insert(keep, e) end
    end
    s.pending = keep
    moveCamera(s, dt, s.impact, 1.0)
    if t >= s.impacted + CONFIG.impact.hold and #s.pending == 0 then finish(s, "done") end
end

local function start(ability)
    local a = H.battleApi()
    local target = a and a:GetTargetCharacter(char) or nil
    show = { ability = ability, start = now(), target = valid(target) and target or nil }
    setInvincible(true)
    log(string.format("%s: he calls the meteor down on %s", ability, show.target and H.str(show.target:GetFName()) or "the ground in front of him"))
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
    LoopAsync(ms, function()
        if CONFIG.enabled and (char ~= nil or show ~= nil) and not loopBusy then
            loopBusy = true
            ExecuteInGameThread(function()
                loopBusy = false
                local ok, err = pcall(tick)
                if not ok then log("error " .. tostring(err)) end
            end)
        end
        return false
    end)
    H.log("MeteorStrike " .. (CONFIG.enabled and "on" or "off") .. ": Meteor is a cinematic (the meteor comes down from the sky, explosions, a crater; he can't be hurt meanwhile)")
end

return M
