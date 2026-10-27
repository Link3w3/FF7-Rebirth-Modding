-- Plain-Lua test of ForceGrabs.lua with stand-ins for the UE4SS API.
package.path = "/work/sephforms/mod/SephirothForms/Scripts/?.lua;" .. package.path
local logs = {}
local function log(t) table.insert(logs, t); print(t) end
local function Obj(name, full, methods)
  local o = methods or {}
  o.__name = name
  o.IsValid = function() return true end
  o.GetFName = function() return { ToString = function() return name end } end
  o.GetFullName = function() return full end
  return o
end
-- fake functions: EndBattleAPI statics + an AI component with keep functions + the event
local function F(class, name, params)
  local f = Obj(name, "Function /Script/EndGame." .. class .. ":" .. name)
  f.ForEachProperty = function(self, cb)
    for _, p in ipairs(params) do
      cb({ GetFName = function() return { ToString = function() return p[1] end } end,
           GetClass = function() return { GetFName = function() return { ToString = function() return p[2] end } end } end })
    end
  end
  return f
end
local functions = {
  F("EndBattleAPI", "AddSpecialStatusChangeID", { { "Character", "ObjectProperty" }, { "ID", "NameProperty" } }),
  F("EndBattleAPI", "RemoveSpecialStatusChangeID", { { "Character", "ObjectProperty" }, { "ID", "NameProperty" } }),
  F("EndBattleAPI", "HasSpecialStatusChangeID", { { "Character", "ObjectProperty" }, { "ID", "NameProperty" }, { "ReturnValue", "BoolProperty" } }),
  F("EndBattleAPI", "GetTargetCharacter", { { "Character", "ObjectProperty" }, { "ReturnValue", "ObjectProperty" } }),
  F("EndBattleAPI", "GetKeep", { { "Character", "ObjectProperty" }, { "ReturnValue", "IntProperty" } }),
  F("EndBattleAPI", "GetSyncActionID", { { "Character", "ObjectProperty" }, { "ReturnValue", "NameProperty" } }),
  F("EndAIActionComponent", "SetOverrideKeep", { { "Keep", "IntProperty" } }),
  F("EndAIActionComponent", "ResetOverrideKeep", {}),
  F("EndAIActionComponent", "OnPreTakeDamage", { { "ownerCharacter", "ObjectProperty" }, { "hitBoneName", "NameProperty" }, { "damageSourceID", "NameProperty" },
    { "hitPosition", "StructProperty" }, { "damage", "IntProperty" }, { "appendAttribute", "ByteProperty" }, { "dataObjectBattleDamageSource", "StructProperty" } }),
  F("Other", "Unrelated", {}),
}
for i = 1, 5000 do table.insert(functions, F("Engine", "Fn" .. i, {})) end
function FindAllOf(c) assert(c == "Function"); return functions end
local hooks = {}
function RegisterHook(path, cb) hooks[path] = cb; return 1, 2 end
function FName(s) return { ToString = function() return s end, __text = s } end
-- world
local state = { keep = {}, binds = {}, sync = {} }
local comp = {}
local enemy = Obj("EN2000_Monster_C_1", "BP_EN2000_C /Game/Map.Map:PersistentLevel.EN2000_1", {
  K2_GetActorLocation = function() return {} end,
  GetComponentByClass = function(self, cls) return comp end,
})
comp = Obj("AIComp", "EndAIActionComponent /Game/Map.Map:PersistentLevel.EN2000_1.AIComp", {
  SetOverrideKeep = function(self, v) state.keep[enemy] = v end,
  ResetOverrideKeep = function(self) state.keep[enemy] = nil end,
  GetOwner = function() return enemy end,
})
local seph = Obj("PC0000_00_Cloud_Standard_C_0", "Seph full", { K2_GetActorLocation = function() return {} end })
local api = Obj("Default__EndBattleAPI", "EndBattleAPI /Script/EndGame.Default__EndBattleAPI", {
  AddSpecialStatusChangeID = function(self, who, id) state.binds[who] = id.__text end,
  RemoveSpecialStatusChangeID = function(self, who, id) state.binds[who] = nil end,
  HasSpecialStatusChangeID = function(self, who, id) return state.binds[who] == id.__text end,
  GetTargetCharacter = function(self, who) return enemy end,
  GetKeep = function(self, who) return state.keep[who] or 60 end,
  GetSyncActionID = function(self, who) return FName(state.sync[who] or "None") end,
})
function StaticFindObject(path)
  if path == "/Script/EndGame.Default__EndBattleAPI" then return api end
  if path == "/Script/EndGame.EndAIActionComponent" then return Obj("EndAIActionComponent", "Class /Script/EndGame.EndAIActionComponent") end
  return nil
end
local function valid(o) return o ~= nil and o.IsValid ~= nil end
local function str(v) if v == nil then return "nil" end if type(v) == "table" and v.ToString then return v:ToString() end return tostring(v) end
local clock = 0
os.clock = function() return clock end
local grabs = require("ForceGrabs")
grabs.init({ log = log, valid = valid, str = str, battleApi = function() return api end })
local function tick(ability) grabs.tick(seph, ability); clock = clock + 0.2 end
-- 1. Grip of Fate: target found, keep lowered, game doesn't bind -> forced bind, lifted after 3 s
tick("None")
tick("PC0010_T_BindFeeler")
assert(state.keep[enemy] == 0, "keep lowered at the move's start")
-- the hit (event on the AI component)
local P = function(v) return { get = function() return v end } end
local hook = hooks["/Script/EndGame.EndAIActionComponent:OnPreTakeDamage"]
assert(hook, "hooked")
hook(P(comp), P(seph), P(FName("Spine")), P(FName("PC0010_10_BindFeeler_01")), P({}), P(120), P(0), P({}))
for i = 1, 5 do tick("PC0010_T_BindFeeler") end
assert(state.binds[enemy] == "Sephiroth_BindFeeler", "bind forced")
for i = 1, 4 do tick("None") end
for i = 1, 20 do tick("None") end
assert(state.binds[enemy] == nil, "bind lifted")
assert(state.keep[enemy] == nil, "keep reset")
-- 2. Skewer: the game syncs (so nothing forced)
tick("PC0010_T_WarpStab")
hook(P(comp), P(seph), P(FName("Spine")), P(FName("PC0010_10_Stab_01")), P({}), P(300), P(0), P({}))
state.sync[enemy] = "PC0010_10_WarpStab"
for i = 1, 20 do tick("PC0010_T_WarpStab") end
for i = 1, 30 do tick("None") end
assert(state.keep[enemy] == nil, "keep reset after skewer")
-- 3. unrelated damage is ignored
hook(P(comp), P(seph), P(FName("Spine")), P(FName("PC0000_Attack01")), P({}), P(10), P(0), P({}))
for i = 1, 10 do tick("None") end
print("HARNESS OK")
