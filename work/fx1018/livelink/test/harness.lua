-- A mocked UE4SS + game for RebirthLiveLink, with memory taken from a real probe of the running game.
local game = dofile("fake_game.lua")
local function unhex(h) return (h:gsub("%x%x", function(x) return string.char(tonumber(x, 16)) end)) end
local function tohex(s) return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end)) end
local mem = {}
for _, b in ipairs(game.blocks) do mem[#mem + 1] = { at = b.at, bytes = unhex(b.hex) } end
local function block(at, n)
    for _, b in ipairs(mem) do if at >= b.at and at + n <= b.at + #b.bytes then return b end end
end
writes = {}
function RebirthSkelCompatReadMemory(at, count)
    local b = block(at, count)
    if not b then return "" end
    return tohex(b.bytes:sub(at - b.at + 1, at - b.at + count))
end
function RebirthSkelCompatWriteMemory(at, hex)
    local n = #hex // 2
    local any = false
    for _, b in ipairs(mem) do
        local from, to = math.max(at, b.at), math.min(at + n, b.at + #b.bytes)
        if from < to then
            local piece = unhex(hex):sub(from - at + 1, to - at)
            b.bytes = b.bytes:sub(1, from - b.at) .. piece .. b.bytes:sub(to - b.at + 1)
            any = true
        end
    end
    if not any then return false end
    writes[#writes + 1] = { at = at, n = n }
    return true
end
function RebirthSkelCompatFindMemory() return 0 end
function RebirthSkelCompatIsGameThread() return true end

local Obj = {}
Obj.__index = Obj
function Obj:IsValid() return true end
function Obj:GetFullName() return self._full or "Object" end
function Obj:GetAddress() return self._address or 0 end
local function obj(t) return setmetatable(t, Obj) end
local function fname(s, index)
    return setmetatable({ s = s, index = index }, { __index = {
        ToString = function(self) return self.s end,
        GetComparisonIndex = function(self) if self.index then return self.index end error("no index") end } })
end
function FName(s) return fname(s) end
local function array(list)
    return setmetatable({ _list = list }, { __index = function(t, k)
        if type(k) == "number" then return t._list[k] end
        if k == "GetArrayNum" then return function(self) return #self._list end end
    end })
end
local function ptr(addr) return setmetatable({}, { __tostring = function() return string.format("userdata: %016X", addr) end }) end
local function u32(at) local h = RebirthSkelCompatReadMemory(at, 4); return #h == 8 and string.unpack("<I4", unhex(h)) or nil end
local function u64(at) local h = RebirthSkelCompatReadMemory(at, 8); return #h == 16 and string.unpack("<I8", unhex(h)) or nil end

local function makeScript(sc)
    local s = obj({ _full = "NiagaraScript " .. sc.name, _address = sc.address })
    local data = u64(sc.arrayAt)
    local infos = {}
    for i, n in ipairs(sc.dis) do
        local idx = data and u32(data + (i - 1) * 0x50 + 8) or nil
        infos[i] = { Name = fname(n, idx), DataInterface = nil }
    end
    s.CachedDefaultDataInterfaces = array(infos)
    s.Reflection = function(self)
        return { GetProperty = function(_, name)
            return { ContainerPtrToValuePtr = function(_, o, _) return ptr(sc.arrayAt) end }
        end }
    end
    return s
end

local emitters, order, sysScripts = {}, {}, {}
for _, sc in ipairs(game.scripts) do
    if sc.emitter == "(system)" then
        sysScripts[sc.kind] = makeScript(sc)
    else
        local e = emitters[sc.emitter]
        if not e then e = obj({ _full = "NiagaraEmitter " .. sc.emitter }); emitters[sc.emitter] = e; order[#order + 1] = sc.emitter end
        if sc.kind == "GPUComputeScript" then e.GPUComputeScript = makeScript(sc) else e[sc.kind] = { Script = makeScript(sc) } end
    end
end
local handles = {}
for _, n in ipairs(order) do handles[#handles + 1] = { Name = fname(n), Instance = emitters[n] } end
local SYSTEM_PATH = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01.FX_PC0000_Limit01_CrossSlash_01"
local system = obj({ _full = "NiagaraSystem " .. SYSTEM_PATH, _address = 1234, EmitterHandles = array(handles),
                     SystemSpawnScript = sysScripts.SystemSpawnScript, SystemUpdateScript = sysScripts.SystemUpdateScript })
spawnedCount = 0
local comp = obj({ _full = "NiagaraComponent X", DeactivateImmediate = function() end, K2_DestroyComponent = function() end })
local lib = obj({ _full = "NiagaraFunctionLibrary", SpawnSystemAtLocation = function(...) spawnedCount = spawnedCount + 1; return comp end })
function StaticFindObject(path)
    if path == SYSTEM_PATH then return system end
    if path == "/Script/Niagara.Default__NiagaraFunctionLibrary" then return lib end
    return nil
end
local pawn = obj({ _full = "PC0000_00_Cloud_Standard_C Cloud", _address = 99,
    K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end,
    GetActorForwardVector = function() return { X = 1, Y = 0, Z = 0 } end,
    GetActorRightVector = function() return { X = 0, Y = 1, Z = 0 } end,
    K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end })
function FindFirstOf(cls) if cls == "PlayerController" then return obj({ K2_GetPawn = function() return pawn end }) end end
function FindAllOf() return {} end
loops = {}
function LoopAsync(ms, fn) loops[#loops + 1] = fn end
function ExecuteInGameThread(fn) fn() end
function LoadAsset() return nil end
local fakeNow = 0
os.clock = function() fakeNow = fakeNow + 0.3; return fakeNow end

return { unhex = unhex, tohex = tohex, u64 = u64, mem = mem }
