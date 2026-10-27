-- RebirthLiveLink 1.4: post-process blendables (pp_apply / pp_status / pp_clear), level changes, the paused-pump fallback
local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")

local MAT_PATH = "/Engine/EngineMaterials/DefaultPostProcessMaterial.DefaultPostProcessMaterial"
local Obj = {}
Obj.__index = Obj
function Obj:IsValid() return not self._gone end
function Obj:GetFullName() return self._full end
function Obj:GetAddress() return self._address end
local function obj(t) return setmetatable(t, Obj) end
local function array(list)
    return setmetatable({ _list = list }, {
        __index = function(t, k)
            if type(k) == "number" then return t._list[k] end
            if k == "GetArrayNum" then return function(self) return #self._list end end
        end,
        __newindex = function(t, k, v) t._list[k] = v end })
end
local nextAddress = 5000
local function volume(name, unbound, interfaceWorks)
    nextAddress = nextAddress + 16
    local v = obj({ _full = "PostProcessVolume " .. name, _address = nextAddress, bUnbound = unbound, bEnabled = true,
                    Priority = 0.0, Settings = { WeightedBlendables = { Array = array({}) } }, calls = 0 })
    v.AddOrUpdateBlendable = function(self, mat, weight)
        self.calls = self.calls + 1
        if not interfaceWorks then error("TScriptInterface parameters are not supported") end
        local arr = self.Settings.WeightedBlendables.Array._list
        for _, e in ipairs(arr) do if e.Object == mat then e.Weight = weight; return end end
        arr[#arr + 1] = { Object = mat, Weight = weight }
    end
    return v
end

local mat = obj({ _full = "Material " .. MAT_PATH, _address = 777 })
local worldVolumes = { volume("Bounded", false, true) }
local spawnedVolumes = {}
local gs = obj({ _full = "GameplayStatics Default__GameplayStatics", _address = 1 })
gs.BeginDeferredActorSpawnFromClass = function(self, ctx, cls, xform, how, owner)
    if spawnFails then error("spawning is not supported here") end
    local v = volume("Spawned" .. (#spawnedVolumes + 1), false, true)
    spawnedVolumes[#spawnedVolumes + 1] = v
    worldVolumes[#worldVolumes + 1] = v
    return v
end
gs.FinishSpawningActor = function(self, a, xform) return a end
local volumeClass = obj({ _full = "Class /Script/Engine.PostProcessVolume", _address = 2 })

local baseFind = StaticFindObject
function StaticFindObject(path)
    if path == MAT_PATH then return mat end
    if path == "/Script/Engine.Default__GameplayStatics" then return gs end
    if path == "/Script/Engine.PostProcessVolume" then return volumeClass end
    return baseFind(path)
end
local baseAll = FindAllOf
function FindAllOf(cls)
    if cls == "PostProcessVolume" then
        local live = {}
        for _, v in ipairs(worldVolumes) do if not v._gone then live[#live + 1] = v end end
        return live
    end
    return baseAll(cls)
end

dofile(root .. "/scripts/main.lua")
local function send(cmd)
    local f = io.open(root .. "/link/command.lua", "w"); f:write("return " .. cmd .. "\n"); f:close()
    RebirthSkelCompatPump(); RebirthSkelCompatPump()
    return io.open(root .. "/link/status.json"):read("a")
end
local function check(what, ok) print((ok and "ok   " or "FAIL ") .. what); if not ok then failed = true end end

RebirthSkelCompatPump()
-- a level without an unbound volume: the link spawns its own
local r = send('{ seq = 1, op = "pp_apply", materials = { { path = "/Engine/EngineMaterials/DefaultPostProcessMaterial", weight = 1.0 } } }')
print(r)
check("spawned a volume", #spawnedVolumes == 1)
check("the spawned volume is unbound", spawnedVolumes[1].bUnbound == true)
check("material on it", spawnedVolumes[1].Settings.WeightedBlendables.Array._list[1].Object == mat)
check("bounded volume untouched", #worldVolumes[1].Settings.WeightedBlendables.Array._list == 0)
check("preset saved", (io.open(root .. "/link/postprocess.lua") ~= nil))

-- nothing re-applied while it stays there
local calls = spawnedVolumes[1].calls
for i = 1, 40 do RebirthSkelCompatPump() end
check("no repeated applies", spawnedVolumes[1].calls == calls)

-- level change: the volume is gone, the new level has an unbound volume of its own whose AddOrUpdateBlendable fails
spawnedVolumes[1]._gone = true
worldVolumes = { volume("LevelGrading", true, false) }
spawnFails = true
for i = 1, 40 do RebirthSkelCompatPump() end
local level = worldVolumes[1]
check("re-applied on the level's unbound volume (array fallback)", level.Settings.WeightedBlendables.Array._list[1]
    and level.Settings.WeightedBlendables.Array._list[1].Object == mat)
check("no second spawn", #spawnedVolumes == 1)

print(send('{ seq = 2, op = "pp_status" }'))

-- the frame pump stops (photo mode): the UE4SS loop processes commands
local f = io.open(root .. "/link/command.lua", "w"); f:write('return { seq = 3, op = "ping" }\n'); f:close()
for i = 1, 8 do for _, fn in ipairs(loops) do fn() end end
local status = io.open(root .. "/link/status.json"):read("a")
check("command handled while the pump is paused", status:find('"seq":3') ~= nil)

-- a new game session: the preset comes back
local preset = io.open(root .. "/link/postprocess.lua"):read("a")
print(preset)
check("preset lists the material", preset:find("DefaultPostProcessMaterial", 1, true) ~= nil)

print(send('{ seq = 4, op = "pp_clear" }'))
check("weight 0 after clear (through the array there)", level.Settings.WeightedBlendables.Array._list[1].Weight == 0.0)
local cleared = io.open(root .. "/link/postprocess.lua"):read("a")
check("preset emptied", not cleared:find("DefaultPostProcessMaterial", 1, true))
print(io.open(root .. "/link/log.txt"):read("a"))
if failed then os.exit(1) end
