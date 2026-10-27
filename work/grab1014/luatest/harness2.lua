-- Plain-Lua test of ForceGrabs.lua (v2) with strict stand-ins for UE4SS and EndBattleAPI: a call on an invalid object or
-- with a wrong parameter type fails the way UE4SS does (an error that ends the whole call).
package.path = "/work/sephforms/mod/SephirothForms/Scripts/?.lua;" .. package.path
local logs = {}
local function log(t) table.insert(logs, t); print("  | " .. t) end
local function found(pattern)
    for _, l in ipairs(logs) do if l:find(pattern) then return true end end
    return false
end

local clock = 0.0
os.clock = function() return clock end

-- FName
local FNameMeta = { __index = { ToString = function(self) return self.__text end } }
function FName(s) assert(type(s) == "string", "FName takes a string"); return setmetatable({ __text = s, __fname = true }, FNameMeta) end

-- objects: unknown members are null objects; calling a member of a null object fails
local nullMeta = {}
local function Null() return setmetatable({ __null = true }, nullMeta) end
nullMeta.__index = function(self, k)
    if k == "IsValid" then return function() return false end end
    return function() error("Tried calling a member function but the UObject instance is nullptr") end
end
local function Obj(name, full, methods, props)
    local o = { __obj = true, __valid = true }
    local meta = {}
    meta.__index = function(self, k)
        if k == "IsValid" then return function(s) return s.__valid end end
        if props and props[k] ~= nil then return props[k] end
        local m = methods[k] or (k == "GetFName" and function() return FName(name) end) or (k == "GetFullName" and function() return full end)
        if not m then return Null() end
        return function(s, ...)
            if not s.__valid then error("Tried calling a member function but the UObject instance is nullptr") end
            return m(s, ...)
        end
    end
    return setmetatable(o, meta)
end
local function chk(v, kind, what)
    local ok
    if kind == "obj" then ok = type(v) == "table" and (v.__obj == true or v.__null == true)
    elseif kind == "name" then ok = type(v) == "table" and v.__fname == true
    elseif kind == "int" then ok = math.type(v) == "integer"
    elseif kind == "bool" then ok = type(v) == "boolean"
    elseif kind == "vec" then ok = type(v) == "table" and type(v.X) == "number" and type(v.Y) == "number" and type(v.Z) == "number"
    elseif kind == "rot" then ok = type(v) == "table" and type(v.Pitch) == "number" and type(v.Yaw) == "number" and type(v.Roll) == "number"
    elseif kind == "num" then ok = type(v) == "number"
    end
    if not ok then error("bad parameter " .. tostring(what) .. " (want " .. kind .. ", got " .. type(v) .. ")") end
end
local function sig(kinds, f)
    return function(self, ...)
        local args = { ... }
        if #args ~= #kinds then error("wrong number of parameters: " .. #args .. " for " .. #kinds) end
        for i, k in ipairs(kinds) do chk(args[i], k, i) end
        return f(self, ...)
    end
end

-- the world
local W = {}
local function reset(opts)
    W = { enemyAt = { X = 300, Y = 0, Z = 0 }, sephAt = { X = 0, Y = 0, Z = 0 }, teleports = {}, partMotions = {}, ability = "None", sources = {}, hp = 10000, keepBase = 100, override = nil, statuses = {}, sync = nil, syncEnds = nil,
          vel = { X = 0, Y = 0, Z = 0 }, launched = nil, damage = {}, gameLaunch = false, opts = opts or {}, statusRemoveAt = nil }
end
local characterClass = Obj("Character", "Class /Script/Engine.Character", {})
local enemy, seph
local function Capsule(r, h)
    return Obj("CollisionCylinder", "CapsuleComponent x", {
        GetScaledCapsuleRadius = sig({}, function() return r end),
        GetScaledCapsuleHalfHeight = sig({}, function() return h end),
    })
end
enemy = Obj("EN0001_Monster_C_1", "EN0001_Monster_C /Game/Map.Map:PersistentLevel.EN0001_Monster_C_1", {
    K2_GetActorLocation = sig({}, function() return W.enemyAt end),
    GetVelocity = sig({}, function() return W.vel end),
    LaunchCharacter = sig({ "vec", "bool", "bool" }, function(self, v) W.launched = v; W.vel = { X = v.X, Y = v.Y, Z = v.Z } end),
    IsA = sig({ "obj" }, function(self, cls) return cls == characterClass end),
}, { CapsuleComponent = Capsule(80.0, 150.0) })
seph = Obj("PC0010_00_Sephiroth_Standard_C_1", "PC0010_00_Sephiroth_Standard_C /Game/Map.Map:PersistentLevel.Seph_1", {
    K2_GetActorLocation = sig({}, function() return W.sephAt end),
    GetActorForwardVector = sig({}, function() return { X = 1, Y = 0, Z = 0 } end),
    K2_TeleportTo = sig({ "vec", "rot" }, function(self, v, r) table.insert(W.teleports, { v, r }); W.sephAt = v; return true end),
}, { CapsuleComponent = Capsule(40.0, 90.0) })
local function isEnemy(o) chk(o, "obj"); return o == enemy end
local api = Obj("Default__EndBattleAPI", "EndBattleAPI /Script/EndGame.Default__EndBattleAPI", {
    GetCurrentAbilityID = sig({ "obj" }, function(self, c) return FName(c == seph and W.ability or "None") end),
    GetTargetCharacter = sig({ "obj" }, function(self, c) if W.opts.noTarget then return Null() end return enemy end),
    GetCharaHP = sig({ "obj" }, function(self, c) return W.hp end),
    GetKeep = sig({ "obj" }, function(self, c) return W.override or W.keepBase end),
    SetOverrideKeep = sig({ "obj", "int" }, function(self, c, v) W.override = v end),
    ResetOverrideKeep = sig({ "obj" }, function(self, c) W.override = nil end),
    HasDamageSource = sig({ "obj", "name" }, function(self, c, id) return c == seph and W.sources[id:ToString()] == true end),
    HasSpecialStatusChangeID = sig({ "obj", "name" }, function(self, c, id) return W.statuses[id:ToString()] == true end),
    AddSpecialStatusChangeID = sig({ "obj", "obj", "name" }, function(self, c, causer, id)
        if not W.opts.refuseBind then W.statuses[id:ToString()] = true end end),
    RemoveSpecialStatusChangeIDRequest = sig({ "obj", "name" }, function(self, c, id) W.statusRemoveAt = clock + 0.5 end),
    RemoveSpecialStatusChangeID = sig({ "obj", "name" }, function(self, c, id) W.statuses[id:ToString()] = nil end),
    IsInSyncAction = sig({ "obj" }, function(self, c) return W.sync ~= nil end),
    CanSyncAction = sig({ "obj" }, function(self, c) return not W.opts.refuseSync end),
    GetSyncActionID = sig({ "obj" }, function(self, c) return FName(W.sync or "None") end),
    CreateSyncAction = sig({ "name", "obj", "obj", "bool", "bool" }, function(self, id, owner, target)
        error("CreateSyncAction must never be called (it crashes the game on enemies the game won't lift)") end),
    PlayPartMotion = sig({ "obj", "name", "name", "int", "num", "num" }, function(self, c, motion, bone, layer)
        assert(c == seph); table.insert(W.partMotions, motion:ToString() .. "@" .. bone:ToString()) end),
    CreateDamageSource = sig({ "name", "obj", "obj", "name", "bool", "int" }, function(self, id, owner, target, ability)
        table.insert(W.damage, id:ToString()) end),
    IsLaunchActionPlaying = sig({ "obj" }, function(self, c) return W.gameLaunch end),
    IsLaunchActionInAir = sig({ "obj" }, function(self, c) return false end),
})
function StaticFindObject(path)
    if path == "/Script/Engine.Character" then return characterClass end
    return Null()
end
local loops = {}
function LoopAsync(ms, f) table.insert(loops, f) end
function ExecuteInGameThread(f) f() end

local function valid(o) if o == nil then return false end local ok, r = pcall(function() return o:IsValid() end) return ok and r end
local function str(v) if v == nil then return "nil" end local ok, t = pcall(function() return v:ToString() end) if ok and t then return t end return tostring(v) end
local grabs = require("ForceGrabs")
grabs.init({ log = log, valid = valid, str = str, battleApi = function() return api end })
assert(#loops == 1, "one loop")

-- one frame: 33 ms; main.lua's tick every 6th frame
local frame = 0
local function run(seconds, each)
    local n = math.floor(seconds / 0.033 + 0.5)
    for i = 1, n do
        clock = clock + 0.033
        frame = frame + 1
        if each then each() end
        if W.sync and W.syncEnds and clock >= W.syncEnds then W.sync = nil; W.syncEnds = nil end
        if W.statusRemoveAt and clock >= W.statusRemoveAt then W.statuses = {}; W.statusRemoveAt = nil end
        if frame % 6 == 0 then grabs.tick(seph, W.ability) end
        local ok, err = pcall(loops[1])
        if not ok then error("loop failed: " .. tostring(err)) end
    end
end
local function scenario(title, opts)
    print("== " .. title)
    reset(opts)
    logs = {}
    grabs.tick(seph, "None")
    run(0.3)
end

-- 1. Grip of Fate: the game doesn't bind -> forced bind, let go after 5 s, keep back
scenario("Grip of Fate, forced bind")
W.ability = "PC0010_T_BindFeeler"
run(0.2)
assert(W.override == 0, "keep lowered at the start")
W.sources.PC0010_10_BindFeeler_01 = true
run(0.5)
W.sources.PC0010_10_BindFeeler_01 = nil; W.hp = W.hp - 20      -- the bullet hits
run(0.3)
assert(W.statuses.Sephiroth_BindFeeler, "bind forced")
assert(found("binding it") and found("binds EN0001_Monster_C_1 %(forced%)"), "logged")
W.ability = "None"
run(4.0)
assert(W.statuses.Sephiroth_BindFeeler and W.override == 0, "still bound, keep still 0 while bound")
run(1.5)
assert(not W.statuses.Sephiroth_BindFeeler, "let go")
run(1.2)
assert(W.override == nil, "keep back")

-- 2. Grip of Fate: the game binds by itself -> nothing forced
scenario("Grip of Fate, the game binds")
W.ability = "PC0010_T_BindFeeler"
run(0.2)
W.sources.PC0010_10_BindFeeler_01 = true
run(0.4)
W.sources.PC0010_10_BindFeeler_01 = nil; W.hp = W.hp - 20; W.statuses.Sephiroth_BindFeeler = true
run(0.2)
assert(found("binds EN0001_Monster_C_1 %(the game%)") and not found("binding it"), "the game's bind, nothing forced")
W.ability = "None"
run(7.0)
assert(not W.statuses.Sephiroth_BindFeeler and W.override == nil, "let go, keep back")

-- 3. Grip of Fate: refused
scenario("Grip of Fate, refused", { refuseBind = true })
W.ability = "PC0010_T_BindFeeler"
run(0.2)
W.sources.PC0010_10_BindFeeler_01 = true
run(0.3)
W.sources.PC0010_10_BindFeeler_01 = nil; W.hp = W.hp - 20
run(0.6)
assert(found("refused the bind"), "refusal logged")
W.ability = "None"
run(5.0)
assert(W.override == nil, "keep back after a refusal")

-- 4. Grip of Fate: a miss
scenario("Grip of Fate, miss")
W.ability = "PC0010_T_BindFeeler"
run(0.2)
W.sources.PC0010_10_BindFeeler_01 = true
run(3.0)
W.sources.PC0010_10_BindFeeler_01 = nil
W.ability = "None"
run(5.0)
assert(not found("binding it") and W.override == nil, "a miss forces nothing, keep back")

-- 5. Skewer: the game lifts; the throw-off moves it (the game's launch)
scenario("Skewer, the game lifts")
W.ability = "PC0010_T_WarpStab"
run(0.2)
assert(W.override == 0, "keep lowered")
W.sources.PC0010_10_Stab_01 = true
run(0.066)
W.hp = W.hp - 300; W.sync = "PC0010_10_WarpStab"; W.syncEnds = clock + 2.0
run(0.1)
W.sources.PC0010_10_Stab_01 = nil
run(0.5)
assert(found("lifts EN0001_Monster_C_1 %(sync PC0010_10_WarpStab"), "the game's lift")
W.ability = "None"
run(1.6, function() if not W.sync then W.gameLaunch = true end end)
run(0.5)
assert(found("throws EN0001_Monster_C_1 off") and found("flies %(the game's launch"), "thrown off, flying by itself")
assert(not W.launched, "no launch of ours")
run(2.0)
assert(W.override == nil, "keep back")

-- 6. Skewer on a far enemy the game doesn't lift: he vanishes to it, his lift motion, the throw-off, launched
scenario("Skewer, far, not lifted")
W.enemyAt = { X = 1500, Y = 500, Z = 60 }
W.ability = "PC0010_T_WarpStab"
run(0.4)
assert(#W.teleports == 1, "vanished once")
local dest, rot = W.teleports[1][1], W.teleports[1][2]
local d = math.sqrt((1500 - dest.X) ^ 2 + (500 - dest.Y) ^ 2)
assert(math.abs(d - (80 + 40 + 120)) < 0.5, "in front of its edge: " .. d)
assert(math.abs(dest.Z - (60 - 150 + 90)) < 0.01, "on its ground")
assert(math.abs(rot.Yaw - math.deg(math.atan(500, 1500))) < 0.01, "facing it")
W.sources.PC0010_T_Stab_01 = true
run(0.066)
W.hp = W.hp - 300
run(0.1)
W.sources.PC0010_T_Stab_01 = nil
run(0.3)
assert(W.partMotions[1] == "B_AtkStab02@C_Hip_a", "his lift motion")
assert(found("he does the lift"), "logged")
W.ability = "None"
run(1.0)
assert(W.damage[1] == "PC0010_T_StabDetach_01", "the player's throw-off hit: " .. tostring(W.damage[1]))
run(0.5)
assert(W.launched and W.launched.X > 0 and W.launched.Y > 0 and W.launched.Z > 0, "launched away and up")
run(2.0)
assert(W.override == nil, "keep back")

-- 7. Skewer with the boss's own stab (the old pak): its throw-off hit
scenario("Skewer, boss stab names", { refuseSync = true })
W.ability = "PC0010_T_WarpStab"
run(0.4)
assert(#W.teleports == 0 and found("is close"), "close: no vanish")
W.sources.PC0010_10_Stab_01 = true
run(0.066)
W.hp = W.hp - 300
run(0.1)
W.sources.PC0010_10_Stab_01 = nil
run(0.3)
W.ability = "None"
run(1.2)
assert(W.damage[1] == "PC0010_10_StabDetach_01", "throw-off hit")
run(0.5)
assert(W.launched, "launched")
run(2.0)
assert(W.override == nil, "keep back")

-- 8. no target
scenario("no target", { noTarget = true })
W.ability = "PC0010_T_WarpStab"
run(2.0)
assert(found("Skewer: no target"), "no target logged")
W.ability = "None"
run(0.5)

-- 9. Sephiroth gone: the loop does nothing
scenario("gone")
grabs.tick(nil, "None")
local before = #logs
run(1.0)
assert(#logs == before, "nothing while he is gone")
print("HARNESS OK")
