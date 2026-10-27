-- 1.6: a mod's new package (not in the game's asset registry: UE4SS's LoadAsset fails) loads by path through
-- AssetRegistryHelpers.GetAsset; effect commands refuse objects that are not Niagara effects
local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")

-- the game: a material only the engine's loader finds, a texture already loaded
local MI = "/Game/RebirthCustom/Taken/MI_Taken_PC0010_00_BodyA.MI_Taken_PC0010_00_BodyA"
local TEX = "/Game/Renderer/Texture/FFFFFFFF_BC4.FFFFFFFF_BC4"
local loadedByPath = {}
local Obj = { IsValid = function() return true end }
Obj.__index = Obj
local function obj(t) return setmetatable(t, Obj) end
local mi = obj({ _full = "MaterialInstanceConstant " .. MI, GetFullName = function(self) return self._full end, GetAddress = function() return 7 end })
local tex = obj({ _full = "Texture2D " .. TEX, GetFullName = function(self) return self._full end, GetAddress = function() return 8 end })
local getAssetCalls = 0
local helpers = obj({ _full = "AssetRegistryHelpers /Script/AssetRegistry.Default__AssetRegistryHelpers",
    GetFullName = function(self) return self._full end,
    GetAsset = function(self, data)
        getAssetCalls = getAssetCalls + 1
        local p = data.ObjectPath:ToString()
        if p == MI then loadedByPath[p] = mi; return mi end
        return nil
    end })
local baseFind = StaticFindObject
function StaticFindObject(path)
    if path == "/Script/AssetRegistry.Default__AssetRegistryHelpers" then return helpers end
    if path == TEX then return tex end
    if loadedByPath[path] then return loadedByPath[path] end
    return baseFind(path)
end
-- a mesh component on the pawn, so slot_material has somewhere to go
local made = 0
local comp = obj({ _full = "EndSkeletalMeshComponent CharacterMesh0", GetFullName = function(self) return self._full end,
    GetOwner = function() return obj({ GetAddress = function() return 99 end }) end,
    GetMaterial = function(self, i) return tex end,
    CreateDynamicMaterialInstance = function(self, slot, layer, material, name)
        made = made + 1
        return obj({ _full = "MaterialInstanceDynamic /Engine/Transient.MID_" .. made, GetFullName = function(s) return s._full end })
    end })
function FindAllOf(cls) if cls == "SkeletalMeshComponent" then return { comp } end return {} end

dofile(root .. "/scripts/main.lua")
local failures = 0
local function check(what, ok)
    print((ok and "ok    " or "FAIL  ") .. what)
    if not ok then failures = failures + 1 end
end
local function send(cmd)
    local f = io.open(root .. "/link/command.lua", "w"); f:write("return " .. cmd .. "\n"); f:close()
    RebirthSkelCompatPump(); RebirthSkelCompatPump()
    return io.open(root .. "/link/status.json"):read("a")
end
local function asyncLoop() for _, fn in ipairs(loops) do fn() end end
RebirthSkelCompatPump()

check("the pump is connected only after the start", type(RebirthSkelCompatPump) == "function")
-- from the frame pump (the game thread): loaded right away, by path, on the first try
local s = send(string.format('{ seq = 30, op = "slot_material", component = 1, slot = 1, path = "%s" }', MI))
check("first try from the pump: on the slot", s:find('"ok":true', 1, true) ~= nil and made == 1)
check("the engine's loader was asked once (" .. getAssetCalls .. ")", getAssetCalls == 1)
-- off the game thread nothing loads (LoadObject there crashes the game's async loader): it waits for the game thread
local MI2 = "/Game/RebirthCustom/Taken/MI_Taken_PC0010_00_Hair.MI_Taken_PC0010_00_Hair"
local mi2 = obj({ _full = "MaterialInstanceConstant " .. MI2, GetFullName = function(self) return self._full end })
local baseGet = helpers.GetAsset
helpers.GetAsset = function(self, data)
    local p = data.ObjectPath:ToString()
    if p == MI2 then getAssetCalls = getAssetCalls + 1; loadedByPath[p] = mi2; return mi2 end
    return baseGet(self, data)
end
local onGame = false
RebirthSkelCompatIsGameThread = function() return onGame end
s = send(string.format('{ seq = 31, op = "slot_material", component = 1, slot = 2, path = "%s" }', MI2))
check("off the game thread: waits", s:find("not loaded yet", 1, true) ~= nil and getAssetCalls == 1)
asyncLoop()
check("still off the game thread: no load (" .. getAssetCalls .. ")", getAssetCalls == 1)
onGame = true
asyncLoop()
check("on the game thread: loaded (" .. getAssetCalls .. ")", getAssetCalls == 2)
s = send(string.format('{ seq = 311, op = "slot_material", component = 1, slot = 2, path = "%s" }', MI2))
check("then on the slot", s:find('"ok":true', 1, true) ~= nil and made == 2)
-- a path the engine cannot load either: failed, and not asked again at once
local before = getAssetCalls
s = send('{ seq = 312, op = "slot_material", component = 1, slot = 3, path = "/Game/Nope/MI_Nope" }')
local after1 = getAssetCalls
s = send('{ seq = 313, op = "slot_material", component = 1, slot = 3, path = "/Game/Nope/MI_Nope" }')
check("a failed load is not tried again at once (" .. (after1 - before) .. ", " .. (getAssetCalls - after1) .. ")", after1 - before == 1 and getAssetCalls == after1)

s = send(string.format('{ seq = 320, op = "probe", path = "%s" }', TEX))
check("probe of a texture: refused", s:find("not a Niagara effect", 1, true) ~= nil)
s = send(string.format('{ seq = 321, op = "spawn", path = "%s" }', TEX))
check("spawn of a texture: refused", s:find("not a Niagara effect", 1, true) ~= nil)
s = send(string.format('{ seq = 322, op = "set_lut", path = "%s", curve = "X", hex = "0000803f" }', TEX))
check("set_lut of a texture: refused", s:find("not a Niagara effect", 1, true) ~= nil)

local log = io.open(root .. "/link/log.txt"):read("a")
check("the log says it loaded", log:find("load " .. MI .. ": ok", 1, true) ~= nil and log:find("load " .. MI2 .. ": ok (by path)", 1, true) ~= nil)
print(log)
print(failures == 0 and "ALL PASSED" or (failures .. " FAILED"))
os.exit(failures == 0 and 0 or 1)
