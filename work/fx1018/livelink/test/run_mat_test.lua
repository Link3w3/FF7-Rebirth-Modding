local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")
-- a character with two mesh components: the body uses TopsA in slot 1, the sword uses another material
local Obj = getmetatable(FindFirstOf("PlayerController"))
local function obj(t) return setmetatable(t, Obj) end
local TOPS = obj({ _full = "MaterialInstanceConstant /Game/Character/Player/PC0000_00_Cloud_Standard/Material/PC0000_00_TopsA.PC0000_00_TopsA" })
local OTHER = obj({ _full = "MaterialInstanceConstant /Game/Character/Player/PC0000_00_Cloud_Standard/Material/PC0000_00_TopsA_Rock.PC0000_00_TopsA_Rock" })
local set = {}
local function mid(parent, comp, slot)
    local m = obj({ _full = "MaterialInstanceDynamic /Game/Level/X.X:PersistentLevel.Cloud.Mesh.RebirthLiveLink", Parent = parent,
        SetScalarParameterValue = function(self, n, v) set[#set + 1] = string.format("%s scalar %s=%s", comp._name, n:ToString(), v) end,
        SetVectorParameterValue = function(self, n, v) set[#set + 1] = string.format("%s vector %s=%s,%s,%s", comp._name, n:ToString(), v.R, v.G, v.B) end,
        SetTextureParameterValue = function(self, n, t) set[#set + 1] = comp._name .. " texture " .. n:ToString() end })
    return m
end
local function comp(name, mats)
    local c = obj({ _full = "SkeletalMeshComponent " .. name, _name = name, mats = mats })
    c.GetNumMaterials = function(self) return #self.mats end
    c.GetMaterial = function(self, i, layer) return self.mats[i + 1] end
    c.CreateDynamicMaterialInstance = function(self, i, layer, src, nm) local m = mid(src, self, i); self.mats[i + 1] = m; return m end
    c.GetOwner = function(self) return CLOUD end
    return c
end
local body = comp("Body", { OTHER, TOPS })
local sword = comp("Sword", { OTHER })
local pc = FindFirstOf("PlayerController")
CLOUD = pc:K2_GetPawn()
function FindAllOf(cls) if cls == "SkeletalMeshComponent" then return { body, sword } end return {} end
dofile(root .. "/scripts/main.lua")
local function send(cmd)
    local f = io.open(root .. "/link/command.lua", "w"); f:write("return " .. cmd .. "\n"); f:close()
    RebirthSkelCompatPump(); RebirthSkelCompatPump()
    return io.open(root .. "/link/status.json"):read("a")
end
print(send('{ seq = 20, op = "material_params", path = "/Game/Character/Player/PC0000_00_Cloud_Standard/Material/PC0000_00_TopsA", params = { { type = "vector", name = "BaseColorTint", value = {0.2, 0.4, 1.0, 1.0} }, { type = "scalar", name = "Glow", value = 2.0 } } }'))
print(table.concat(set, "\n"))
set = {}
print(send('{ seq = 21, op = "material_params", path = "/Game/Character/Player/PC0000_00_Cloud_Standard/Material/PC0000_00_TopsA", params = { { type = "scalar", name = "Glow", value = 3.0 } } }'))
print(table.concat(set, "\n"))
print(send('{ seq = 22, op = "reset_materials" }'))
print(body.mats[2]._full, body.mats[2].Parent and body.mats[2].Parent._full)
