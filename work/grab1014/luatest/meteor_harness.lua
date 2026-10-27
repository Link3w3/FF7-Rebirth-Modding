-- Plain-Lua test of MeteorStrike.lua with strict stand-ins (wrong types or calls on invalid objects fail like UE4SS).
package.path = "/work/sephforms/mod/SephirothForms/Scripts/?.lua;" .. package.path
local logs = {}
local function log(t) table.insert(logs, t); print("  | " .. t) end
local function found(p) for _, l in ipairs(logs) do if l:find(p) then return true end end return false end
local clock = 0.0
os.clock = function() return clock end
local FNameMeta = { __index = { ToString = function(self) return self.__text end } }
function FName(s) assert(type(s) == "string"); return setmetatable({ __text = s, __fname = true }, FNameMeta) end
local nullMeta = {}
local function Null() return setmetatable({ __null = true }, nullMeta) end
nullMeta.__index = function(self, k)
    if k == "IsValid" then return function() return false end end
    return function() error("Tried calling a member function but the UObject instance is nullptr") end
end
local nextAddr = 0x7ff600000000
local function Obj(name, methods, props)
    nextAddr = nextAddr + 0x40
    local o = { __obj = true, __valid = true, __name = name, __addr = nextAddr }
    setmetatable(o, { __index = function(self, k)
        if k == "IsValid" then return function(s) return s.__valid end end
        if props and props[k] ~= nil then return props[k] end
        local m = methods[k] or (k == "GetFName" and function() return FName(name) end) or (k == "GetFullName" and function() return name end)
            or (k == "GetClass" and function() return Obj(props and props.__class or "Class", {}) end)
            or (k == "GetAddress" and function(s) return rawget(s, "__addr") end)
            or (k == "GetOuter" and function() return (props and props.__outer) or Null() end)
        if not m then return Null() end
        return function(s, ...)
            if not s.__valid then error("Tried calling a member function but the UObject instance is nullptr") end
            return m(s, ...)
        end
    end })
    return o
end
local function chk(v, kind, what)
    local ok
    if kind == "obj" then ok = type(v) == "table" and (v.__obj == true or v.__null == true)
    elseif kind == "objornil" then ok = v == nil or (type(v) == "table" and v.__obj == true)
    elseif kind == "name" then ok = type(v) == "table" and v.__fname == true
    elseif kind == "int" then ok = math.type(v) == "integer"
    elseif kind == "num" then ok = type(v) == "number"
    elseif kind == "bool" then ok = type(v) == "boolean"
    elseif kind == "vec" then ok = type(v) == "table" and type(v.X) == "number" and type(v.Y) == "number" and type(v.Z) == "number"
    elseif kind == "table" then ok = type(v) == "table" and v.__obj == nil
    elseif kind == "rot" then ok = type(v) == "table" and type(v.Pitch) == "number" and type(v.Yaw) == "number" and type(v.Roll) == "number"
    elseif kind == "xform" then ok = type(v) == "table" and type(v.Rotation) == "table" and type(v.Rotation.W) == "number" and type(v.Translation) == "table" and type(v.Scale3D) == "table"
    end
    if not ok then error("bad parameter " .. tostring(what) .. " (want " .. kind .. ", got " .. type(v) .. ")") end
end
local function sig(kinds, f)
    return function(self, ...)
        local args = { ... }
        local n = select("#", ...)
        if n ~= #kinds then error("wrong number of parameters: " .. n .. " for " .. #kinds) end
        for i, k in ipairs(kinds) do chk(args[i], k, i) end
        return f(self, ...)
    end
end
local W = { ability = "None", sources = {}, invincible = {}, spawned = {}, effects = {}, decals = {}, damage = {}, views = {}, inBattle = true }
local function Capsule(h) return Obj("Capsule", { GetScaledCapsuleHalfHeight = sig({}, function() return h end) }) end
local target = Obj("EN0001_Monster_C_1", { K2_GetActorLocation = sig({}, function() return { X = 2000, Y = 0, Z = 150 } end) }, { CapsuleComponent = Capsule(150.0) })
local meshZ = { -90.0 }
local refuseLift = false
local mesh = Obj("CharacterMesh0", {
    K2_SetRelativeLocation = sig({ "vec", "bool", "table", "bool" }, function(self, v)
        if refuseLift then error("refused by the engine") end
        meshZ[1] = v.Z
    end),
}, { RelativeLocation = { X = 0.0, Y = 0.0, Z = -90.0 } })
local seph
seph = Obj("Seph", {
    K2_GetActorLocation = sig({}, function() return { X = 0, Y = 0, Z = 90 } end),
    GetActorForwardVector = sig({}, function() return { X = 1, Y = 0, Z = 0 } end),
}, { CapsuleComponent = Capsule(90.0), Mesh = mesh })
local function Actor(kind)
    local a
    a = Obj(kind, {
        K2_TeleportTo = sig({ "vec", "rot" }, function(self, v, r) self.__at = v; return true end),
        SetActorScale3D = sig({ "vec" }, function(self, v) self.__scale = v.X end),
        SetActorEnableCollision = sig({ "bool" }, function() end),
        SetActorHiddenInGame = sig({ "bool" }, function(self, h) self.__hidden = h end),
        K2_DestroyActor = sig({}, function(self) self.__valid = false end),
        SetLifeSpan = sig({ "num" }, function(self, s) self.__life = s end),
        K2_GetActorLocation = sig({}, function(self) return self.__at end),
        K2_SetActorLocation = sig({ "vec", "bool", "table", "bool" }, function(self, v) self.__at = v; return true end),
        SetMobility = sig({ "int" }, function(self, m) self.__mobility = m end),
    }, { CameraComponent = Obj("CameraComponent", { SetFieldOfView = sig({ "num" }, function() end) }),
         StaticMeshComponent = kind:find("StaticMeshActor", 1, true) and Obj("StaticMeshComponent", {
            SetStaticMesh = sig({ "obj" }, function(self, m) W.meshOf[self] = m.__name; return true end),
            SetCollisionEnabled = sig({ "int" }, function(self, c) W.collision = c end),
         }) or nil,
         PointLightComponent = kind:find("PointLight", 1, true) and Obj("PointLightComponent", {
            SetMobility = sig({ "int" }, function(self, m) W.lightMobility = m end),
            SetIntensityUnits = sig({ "int" }, function() end),
            SetLightColor = sig({ "table", "bool" }, function(self, c) W.lightColor = c end),
            SetAttenuationRadius = sig({ "num" }, function() end),
            SetSourceRadius = sig({ "num" }, function() end),
            SetCastShadows = sig({ "bool" }, function() end),
            SetVolumetricScatteringIntensity = sig({ "num" }, function() end),
            SetIntensity = sig({ "num" }, function(self, i) W.lightIntensity = i; W.lightMax = math.max(W.lightMax or 0, i) end),
            K2_AttachToComponent = sig({ "obj", "name", "int", "int", "int", "bool" }, function(self, parent) W.lightParent = parent.__name; return true end),
            K2_SetRelativeLocation = sig({ "vec", "bool", "table", "bool" }, function() end),
         }) or nil })
    return a
end
local meteorClass = Obj("FA0260_01_SephirothMeteor_Battle_C", {})
local cameraClass = Obj("CameraActor", {})
local pointLightClass = Obj("PointLight", {})
local staticMeshActorClass = Obj("StaticMeshActor", {})
W.meshOf = {}
-- the ground: a slope (it rises 2 cm per metre east), so every piece of the crater has its own height
local function groundZ(x, y) return 0.02 * x end
local kismet = Obj("Default__KismetSystemLibrary", {
    LineTraceSingle = sig({ "obj", "vec", "vec", "int", "bool", "table", "int", "table", "bool", "table", "table", "num" },
        function(self, w, from, to, channel, complex, ignore, debug, hit)
            if W.refuseTrace then error("refused by the engine (trace)") end
            W.traces = (W.traces or 0) + 1
            assert(channel == 0 and from.X == to.X and from.Y == to.Y and from.Z > to.Z, "a straight trace down (Visibility)")
            local z = groundZ(from.X, from.Y)
            if z > from.Z or z < to.Z then return false end
            hit.ImpactPoint = { X = from.X, Y = from.Y, Z = z }
            return true
        end),
})
local manager = Obj("Manager", {}, { ViewTarget = { Target = seph } })
local pc = Obj("PlayerController", {
    SetViewTargetWithBlend = sig({ "obj", "num", "int", "num", "bool" }, function(self, t, b) table.insert(W.views, t.__name) end),
}, { PlayerCameraManager = manager })
local statics = Obj("Default__GameplayStatics", {
    BeginDeferredActorSpawnFromClass = sig({ "obj", "obj", "xform", "int", "objornil" }, function(self, w, cls, t)
        local a = Actor(cls.__name .. "_actor"); a.__at = t.Translation; a.__z0 = t.Translation.Z; a.__scale = t.Scale3D.X; table.insert(W.spawned, a); return a end),
    FinishSpawningActor = sig({ "obj", "xform" }, function(self, a) return a end),
    GetPlayerController = sig({ "obj", "int" }, function() return pc end),
    SpawnDecalAtLocation = sig({ "obj", "obj", "vec", "vec", "rot", "num" }, function(self, w, m, size)
        local d = Obj("Decal", { SetFadeOut = sig({ "num", "num", "bool" }, function() end) }); table.insert(W.decals, size.Y); return d end),
    SpawnEmitterAtLocation = sig({ "obj", "obj", "vec", "rot", "vec", "bool", "int", "bool" }, function(self, w, sys) table.insert(W.effects, sys.__name) end),
})
local function MID(name, outer)
    return Obj("MID_" .. name, {
        SetVectorParameterValue = sig({ "name", "table" }, function(self, n, c)
            if W.refuseTint then error("refused by the engine (tint)") end
            W.tints[n:ToString()] = c; W.tintCalls = (W.tintCalls or 0) + 1; W.tintedMids[self.__name] = true end),
    }, { __class = "MaterialInstanceDynamic", __outer = outer })
end
-- the component's own list of materials fails when read, like in the game
local function Array(items)
    local arr = { __items = items }
    function arr:ForEach(f) error("Tried calling a member function but the UObject instance is nullptr") end
    return arr
end
W.tints = {}
W.tintedMids = {}
W.smokeOff = {}
-- every dynamic material in the game: some that are not the aura's (a widget's, one with no outer)
local allMids = { MID("ui", Obj("UserWidget", {})), MID("orphan", nil) }
function FindAllOf(cls)
    assert(type(cls) == "string")
    if cls ~= "MaterialInstanceDynamic" then return nil end
    W.searches = (W.searches or 0) + 1
    local r = {}
    for _, m in ipairs(allMids) do if m.__valid then table.insert(r, m) end end
    return #r > 0 and r or nil
end
local auraComp = nil
local niagara = Obj("Default__NiagaraFunctionLibrary", {
    SpawnSystemAtLocation = sig({ "obj", "obj", "vec", "rot", "vec", "bool", "bool", "int", "bool" }, function(self, w, sys)
        table.insert(W.effects, sys.__name)
        return Obj("NiagaraComponent_" .. sys.__name, { Deactivate = sig({}, function(c) W.smokeOff[sys.__name] = (W.smokeOff[sys.__name] or 0) + 1 end) })
    end),
    SpawnSystemAttached = sig({ "obj", "obj", "name", "vec", "rot", "int", "bool", "bool", "int", "bool" }, function(self, sys, parent, socket)
        W.auraSpawned = (W.auraSpawned or 0) + 1
        W.auraParent = parent.__name
        local n = W.auraSpawned
        local materials = 0
        auraComp = Obj("NiagaraComponent", {
            IsActive = sig({}, function(self) return not rawget(self, "__off") end),
            Deactivate = sig({}, function(self) self.__off = true; W.auraOff = (W.auraOff or 0) + 1 end),
            GetNumMaterials = sig({}, function() W.searches = (W.searches or 0) + 1; return materials end),
            CreateDynamicMaterialInstance = sig({ "int", "int", "objornil", "name" }, function(self, i, layer, src, name)
                assert(i >= 0 and i < materials and layer == 0 and src == nil, "a copy of one of its own materials")
                return MID((i == 0 and "a" or "b") .. n, self)
            end),
        }, { EmitterMaterials = Array({}) })
        -- the aura has its materials a little later
        W.makeMids = function() materials = 2 end
        return auraComp
    end),
})
local api = Obj("Default__EndBattleAPI", {
    GetCurrentAbilityID = sig({ "obj" }, function() return FName(W.ability) end),
    GetTargetCharacter = sig({ "obj" }, function() return target end),
    HasDamageSource = sig({ "obj", "name" }, function(self, c, id) return W.sources[id:ToString()] == true end),
    SetDisableDamageHit = sig({ "obj", "bool" }, function(self, c, on) table.insert(W.invincible, on) end),
    CreateDamageSource = sig({ "name", "obj", "obj", "name", "bool", "int" }, function(self, id) table.insert(W.damage, id:ToString()) end),
    IsInBattle = sig({}, function() return W.inBattle end),
})
local assets = {}
function StaticFindObject(path)
    if path == "/Script/Engine.Default__GameplayStatics" then return statics end
    if path == "/Script/Niagara.Default__NiagaraFunctionLibrary" then return niagara end
    if path == "/Script/Engine.CameraActor" then return cameraClass end
    if path == "/Script/Engine.PointLight" then return pointLightClass end
    if path == "/Script/Engine.StaticMeshActor" then return staticMeshActorClass end
    if path == "/Script/Engine.Default__KismetSystemLibrary" then return kismet end
    if path:find("FA0260_01_SephirothMeteor_Battle_C", 1, true) then return meteorClass end
    if path:find("/Game/", 1, true) then
        assets[path] = assets[path] or Obj(path:match("([^/%.]+)$"), {}, { __class = path:find("Fire03") and "ParticleSystem" or "NiagaraSystem" })
        return assets[path]
    end
    return Null()
end
function LoadAsset(p) error("not loaded: " .. p) end
local loops = {}
function LoopAsync(ms, f) table.insert(loops, f) end
-- UE4SS's game-thread queue: a call handed to it from inside a game-thread call can crash the game (the queue moves
-- in memory as it grows while it runs), so that fails here
local inGameThread = false
W.gameThreadCalls = 0
function ExecuteInGameThread(f)
    if inGameThread then error("ExecuteInGameThread called from inside a game-thread call (crashes the game)") end
    W.gameThreadCalls = W.gameThreadCalls + 1
    inGameThread = true
    local ok, err = pcall(f)
    inGameThread = false
    if not ok then print("  | (a game-thread call failed: " .. tostring(err) .. ")") end
end
local function valid(o) if o == nil then return false end local ok, r = pcall(function() return o:IsValid() end) return ok and r end
local function str(v) if v == nil then return "nil" end local ok, t = pcall(function() return v:ToString() end) if ok and t then return t end return tostring(v) end
local meteor = require("MeteorStrike")
meteor.init({ log = log, valid = valid, str = str, battleApi = function() return api end })
local function run(seconds, each)
    for i = 1, math.floor(seconds / 0.016 + 0.5) do
        clock = clock + 0.016
        if each then each() end
        meteor.tick(seph)
        loops[1]()
    end
end
run(0.2)
W.ability = "PC0010_T_Meteor"
run(0.5)
assert(W.invincible[1] == true, "invincible at the cast")
local function spawnedOf(kind) local n = 0 for _, a in ipairs(W.spawned) do if a.__name:find(kind, 1, true) then n = n + 1 end end return n end
local function firstOf(kind) for _, a in ipairs(W.spawned) do if a.__name:find(kind, 1, true) then return a end end end
assert(spawnedOf("Meteor") == 0 and spawnedOf("CameraActor") == 1, "only the camera (and the light) before the call")
assert(spawnedOf("PointLight") == 1, "the pink light")
assert(W.auraSpawned == 1 and W.auraParent == "CharacterMesh0", "his aura on his model")
assert(W.lightParent == "CharacterMesh0" and W.lightMobility == 2, "the light on him, movable")
assert(W.lightColor and W.lightColor.R > W.lightColor.G, "the light is pink")
assert(W.searches and W.searches >= 1 and not found("materials copied"), "it looks for the aura's materials before there are any")
W.makeMids()
run(0.6)
assert(found("2 of its 2 materials copied"), "the aura's own materials are copied")
assert(W.tints.ParticleEmitColorTop and W.tints.ParticleEmitColorTop.R > 1.0 and W.tints.ParticleEmitColorTop.G < 0.5, "the aura is pink")
assert(found("pink on 2 of its materials"), "only the aura's dynamic materials are tinted")
assert(W.tintedMids.MID_a1 and W.tintedMids.MID_b1 and not W.tintedMids.MID_ui and not W.tintedMids.MID_orphan, "nothing else is tinted")
local searchesAfterFound = W.searches
assert(W.views[1] == "CameraActor_actor", "camera on him from the start")
assert(meshZ[1] > -90.0 + 500, "he is flying up: " .. meshZ[1])
W.sources.PC0010_Meteor = true
run(0.1)
W.ability = "None"
W.sources.PC0010_Meteor = nil
assert(spawnedOf("Meteor") == 1 and spawnedOf("CameraActor") == 1, "meteor and camera spawned")
local m = firstOf("Meteor")
assert(m.__name:find("Meteor"), "the meteor")
assert(m.__scale and math.abs(m.__scale - 0.12) < 1e-6, "meteor scale")
local z0 = m.__at.Z
run(2.0)
assert(W.searches == searchesAfterFound, "no more searches once they are found")
assert(math.abs(meshZ[1] - (-90.0 + 2500.0)) < 1.0, "he is up in the sky: " .. meshZ[1])
local cam = firstOf("CameraActor")
assert(W.lightIntensity > 3000.0, "the light glows when he is up: " .. tostring(W.lightIntensity))
run(2.0)
assert(m.__at.Z < z0, "it comes down")
assert(cam.__at.Z > 2000, "the camera is up in the sky beside him: " .. cam.__at.Z)
run(4.0)
assert(found("impact at"), "impact")
assert(W.damage[1] == "PC0010_Meteor_Impact", "impact damage")
-- the crater: Titan's rocks in three rings and four ground cracks, each on the ground where it is
local function meshActors() local r = {} for _, a in ipairs(W.spawned) do if a.__name:find("StaticMeshActor", 1, true) then table.insert(r, a) end end return r end
local pieces = meshActors()
assert(#pieces == 16 + 8 + 14 + 4, "the crater's pieces: " .. #pieces)
local rocks, cracks = 0, 0
for _, a in ipairs(pieces) do
    local name = W.meshOf[a.StaticMeshComponent]
    if name and name:find("FX_SU2000_Rock", 1, true) then rocks = rocks + 1 elseif name == "Decal_B_GroundCrack_01A" then cracks = cracks + 1 end
    assert(a.__mobility == 2 and a.__life and a.__life > 30, "movable, with a life span")
end
assert(rocks == 38 and cracks == 4 and W.collision == 0, "38 rocks and 4 cracks, no collision: " .. rocks .. " " .. cracks)
assert(found("the ground's height found under 39 of 39 places"), "the ground's height under each")
assert(found("crater: 42 pieces"), "the crater logged")
run(4.0)
for _, a in ipairs(pieces) do
    local name = W.meshOf[a.StaticMeshComponent]
    local g = groundZ(a.__at.X, a.__at.Y)
    if name == "Decal_B_GroundCrack_01A" then
        assert(a.__at.Z > groundZ(2000, 0) and a.__at.Z < groundZ(2000, 0) + 12, "a crack lies on the ground at the middle: " .. a.__at.Z)
    else
        assert(a.__at.Z > g - 1 and a.__at.Z < g + 60, "a rock sits on the ground where it is: " .. a.__at.Z .. " ground " .. g)
        assert(a.__z0 < a.__at.Z - 50, "it came up out of the ground")
    end
    assert(a.__valid, "the crater outlives the cinematic")
end
assert(#W.effects >= 25 and W.effects[#W.effects] ~= nil, "explosions and smoke")
local smokes = 0
for _, e in ipairs(W.effects) do if e == "FX_SU2000_Common_Smoke_01" then smokes = smokes + 1 end end
assert(smokes == 5, "Titan's smoke over the rim: " .. smokes)
local storm = false
for _, e in ipairs(W.effects) do if e == "FX_SU2000_RockThrow_Storm_01" then storm = true end end
assert(storm, "Titan's rocks burst out of the ground")
assert(#W.effects >= 20, "explosions " .. #W.effects)
assert(found("over %(done%)"), "over")
assert(math.abs(meshZ[1] - (-90.0)) < 1.0, "back on the ground: " .. meshZ[1])
assert(W.views[#W.views] == "Seph", "camera back to him")
assert(W.invincible[#W.invincible] == false, "invincibility off at the end")
assert(not m.__valid, "meteor gone")
assert(W.auraOff == 1 and found("aura: off"), "the aura stops at the end")
assert(not firstOf("PointLight").__valid, "the light is gone at the end")
-- a second cast, the battle ends in the middle: everything is cleaned up
logs = {}
W.ability = "PC0000_Limit003"
run(0.2)
run(2.6)
assert(found("the call %(time%)"), "the call by time")
assert(meshZ[1] > 1000, "flying in the second cast")
W.inBattle = false
run(0.1)
assert(found("over %(the battle ended%)"), "cleaned up at the battle's end")
assert(W.invincible[#W.invincible] == false)
assert(math.abs(meshZ[1] - (-90.0)) < 1.0, "back on the ground when the battle ends: " .. meshZ[1])
-- a third cast where the engine refuses to move his model: no flight, the cinematic still plays and ends
logs = {}
W.inBattle = true
refuseLift = true
W.ability = "None"; run(0.1)
W.ability = "PC0010_Limit003"
W.refuseTint = true
run(0.1)
W.makeMids()
run(1.4)
assert(found("its materials refuse the pink"), "the tint gives up when the engine refuses it")
assert(found("can't be moved"), "the flight gives up")
assert(math.abs(meshZ[1] - (-90.0)) < 1.0, "he stays on the ground")
assert(found("2 of its 2 materials copied") and not found("4 of its"), "this aura's own materials")
W.sources.PC0010_Meteor = true; run(0.1); W.sources.PC0010_Meteor = nil; W.ability = "None"
run(12.0)
assert(found("over %(done%)"), "over without the flight")
-- a fourth cast where the aura never has materials of its own: a few searches, then it says so and stops looking
logs = {}
refuseLift = false
W.refuseTint = false
W.tintedMids = {}
W.refuseTrace = true
W.ability = "PC0010_Limit003"
local before = W.searches
run(0.1)
W.sources.PC0010_Meteor = true; run(0.1); W.sources.PC0010_Meteor = nil; W.ability = "None"
run(12.0)
assert(found("it has no materials to turn pink"), "it says the aura has no materials to tint")
assert(W.searches - before == 6, "six searches at most: " .. (W.searches - before))
assert(next(W.tintedMids) == nil, "the old auras' materials are not tinted")
assert(found("over %(done%)"), "the fourth is over")
assert(found("can't be looked up"), "the trace refused: the crater sits at the impact's height")
-- the craters stay a while after the cinematic, then sink and go
run(40.0)
assert(found("crater: gone"), "the craters sink and go")
for _, a in ipairs(meshActors()) do assert(not a.__valid, "every piece is gone") end
assert(W.smokeOff.FX_SU2000_Common_Smoke_01 == 15, "every smoke ended: " .. tostring(W.smokeOff.FX_SU2000_Common_Smoke_01))
assert(W.smokeOff.FX_SU2000_RockThrow_Storm_01 == 3, "Titan's rock storm is stopped each time: " .. tostring(W.smokeOff.FX_SU2000_RockThrow_Storm_01))
print("METEOR HARNESS OK")
