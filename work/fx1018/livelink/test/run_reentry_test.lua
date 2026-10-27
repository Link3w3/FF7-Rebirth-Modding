local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")
dofile(root .. "/scripts/main.lua")
-- the game calls the pump again while an effect spawns (what made 1.1 overflow its stack)
local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
local inner = lib.SpawnSystemAtLocation
local depth, maxDepth = 0, 0
lib.SpawnSystemAtLocation = function(...)
    depth = depth + 1; if depth > maxDepth then maxDepth = depth end
    RebirthSkelCompatPump()
    local r = inner(...)
    depth = depth - 1
    return r
end
local f = io.open(root .. "/link/command.lua", "w")
f:write('return { seq = 30, op = "spawn", path = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01", loop = true, every = 0.5 }\n'); f:close()
for i = 1, 200 do RebirthSkelCompatPump() end
print("spawned", spawnedCount, "max nested spawn depth", maxDepth)
print(io.open(root .. "/link/log.txt"):read("a"))
