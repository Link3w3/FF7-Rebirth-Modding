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
local function Obj(name, methods, props)
    local o = { __obj = true, __valid = true, __name = name }
    setmetatable(o, { __index = function(self, k)
        if k == "IsValid" then return function(s) return s.__valid end end
        if props and props[k] ~= nil then return props[k] end
        local m = methods[k] or (k == "GetFName" and function() return FName(name) end) or (k == "GetFullName" and function() return name end)
            or (k == "GetClass" and function() return Obj(props and props.__class or "Class", {}) end)
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
    }, { CameraComponent = Obj("CameraComponent", { SetFieldOfView = sig({ "num" }, function() end) }) })
    return a
end
local meteorClass = Obj("FA0260_01_SephirothMeteor_Battle_C", {})
local cameraClass = Obj("CameraActor", {})
local manager = Obj("Manager", {}, { ViewTarget = { Target = seph } })
local pc = Obj("PlayerController", {
    SetViewTargetWithBlend = sig({ "obj", "num", "int", "num", "bool" }, function(self, t, b) table.insert(W.views, t.__name) end),
}, { PlayerCameraManager = manager })
local statics = Obj("Default__GameplayStatics", {
    BeginDeferredActorSpawnFromClass = sig({ "obj", "obj", "xform", "int", "objornil" }, function(self, w, cls, t)
        local a = Actor(cls.__name .. "_actor"); a.__at = t.Translation; table.insert(W.spawned, a); return a end),
    FinishSpawningActor = sig({ "obj", "xform" }, function(self, a) return a end),
    GetPlayerController = sig({ "obj", "int" }, function() return pc end),
    SpawnDecalAtLocation = sig({ "obj", "obj", "vec", "vec", "rot", "num" }, function(self, w, m, size)
        local d = Obj("Decal", { SetFadeOut = sig({ "num", "num", "bool" }, function() end) }); table.insert(W.decals, size.Y); return d end),
    SpawnEmitterAtLocation = sig({ "obj", "obj", "vec", "rot", "vec", "bool", "int", "bool" }, function(self, w, sys) table.insert(W.effects, sys.__name) end),
})
local niagara = Obj("Default__NiagaraFunctionLibrary", {
    SpawnSystemAtLocation = sig({ "obj", "obj", "vec", "rot", "vec", "bool", "bool", "int", "bool" }, function(self, w, sys) table.insert(W.effects, sys.__name) end),
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
function ExecuteInGameThread(f)
    local ok, err = pcall(f)
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
assert(#W.spawned == 1 and W.spawned[1].__name == "CameraActor_actor", "only the camera before the call")
assert(W.views[1] == "CameraActor_actor", "camera on him from the start")
assert(meshZ[1] > -90.0 + 500, "he is flying up: " .. meshZ[1])
W.sources.PC0010_Meteor = true
run(0.1)
W.ability = "None"
W.sources.PC0010_Meteor = nil
assert(#W.spawned == 2, "meteor and camera spawned: " .. #W.spawned)
local m = W.spawned[2]
assert(m.__name:find("Meteor"), "the meteor")
assert(m.__scale and math.abs(m.__scale - 0.12) < 1e-6, "meteor scale")
local z0 = m.__at.Z
run(2.0)
assert(math.abs(meshZ[1] - (-90.0 + 2500.0)) < 1.0, "he is up in the sky: " .. meshZ[1])
local cam = W.spawned[1]
run(2.0)
assert(m.__at.Z < z0, "it comes down")
assert(cam.__at.Z > 2000, "the camera is up in the sky beside him: " .. cam.__at.Z)
run(4.0)
assert(found("impact at"), "impact")
assert(W.damage[1] == "PC0010_Meteor_Impact", "impact damage")
assert(#W.decals == 3, "crater")
run(4.0)
assert(#W.effects >= 20, "explosions " .. #W.effects)
assert(found("over %(done%)"), "over")
assert(math.abs(meshZ[1] - (-90.0)) < 1.0, "back on the ground: " .. meshZ[1])
assert(W.views[#W.views] == "Seph", "camera back to him")
assert(W.invincible[#W.invincible] == false, "invincibility off at the end")
assert(not m.__valid, "meteor gone")
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
run(1.5)
assert(found("can't be moved"), "the flight gives up")
assert(math.abs(meshZ[1] - (-90.0)) < 1.0, "he stays on the ground")
W.sources.PC0010_Meteor = true; run(0.1); W.sources.PC0010_Meteor = nil; W.ability = "None"
run(12.0)
assert(found("over %(done%)"), "over without the flight")
print("METEOR HARNESS OK")
