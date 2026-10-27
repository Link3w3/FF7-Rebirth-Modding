local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
-- a stale command from an earlier session: must not run
local f = io.open(root .. "/link/command.lua", "w"); f:write('return { seq = 5, op = "spawn", path = "/Game/X" }\n'); f:close()
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")
dofile(root .. "/scripts/main.lua")
local function send(cmd)
    local f = io.open(root .. "/link/command.lua", "w"); f:write("return " .. cmd .. "\n"); f:close()
    RebirthSkelCompatPump(); RebirthSkelCompatPump()
    local s = io.open(root .. "/link/status.json"):read("a")
    return s
end
RebirthSkelCompatPump()
print("stale command ran:", spawnedCount ~= 0)
local function floatsHex(t) local p = {} for i, v in ipairs(t) do p[i] = H.tohex(string.pack("<f", v)) end return table.concat(p) end
-- 46 samples of green (as the editor sends for Main.ColorFromCurve002)
local green = {}
for k = 1, 46 do green[#green + 1] = 0.1; green[#green + 1] = 1.0; green[#green + 1] = 0.2; green[#green + 1] = 1.0 end
local s = send(string.format('{ seq = 10, op = "set_lut", path = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01", curve = "Main.ColorFromCurve002.ColorCurve", hex = "%s" }', floatsHex(green)))
print(s)
for _, w in ipairs(writes) do print(string.format("write 0x%x %d bytes", w.at, w.n)) end
-- read back
local back = RebirthSkelCompatReadMemory(0x7fed89ae5cb0, 16)
print("spawn copy now", back)
-- a curve sent at another sampling (10 samples over 0..0.5556): resampled into the 46-sample copies
writes = {}
local ten = {}
for k = 0, 9 do ten[#ten + 1] = k / 9; ten[#ten + 1] = 0.0; ten[#ten + 1] = 1 - k / 9; ten[#ten + 1] = 1.0 end
s = send(string.format('{ seq = 11, op = "set_lut", path = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01", curve = "Main.ColorFromCurve001.ColorCurve", hex = "%s", samples = 10, tmin = 0.0, tmax = 0.55560302734375 }', floatsHex(ten)))
print(s)
for _, w in ipairs(writes) do print(string.format("write 0x%x %d bytes", w.at, w.n)) end
local h = RebirthSkelCompatReadMemory(0x7fed89ae5fe0, 0x7fed89ae6140 - 0x7fed89ae5fe0)
local vals = {}
for i = 0, (#h // 32) - 1 do vals[#vals + 1] = string.format("%.3f", string.unpack("<f", H.unhex(h:sub(i * 32 + 1, i * 32 + 8)))) end
print("resampled R:", table.concat(vals, " "))
-- probe reports the frozen copies
s = send('{ seq = 12, op = "probe", path = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01" }')
print(s:sub(1, 900))
s = send('{ seq = 13, op = "read", at = 140658193882288, count = 16 }')
print(s)
print(io.open(root .. "/link/log.txt"):read("a"))
writes = {}
local two = {}
for k = 1, 46 do two[#two + 1] = 1.0; two[#two + 1] = 0.0; two[#two + 1] = 1.0; two[#two + 1] = 1.0 end
local hx = floatsHex(two)
s = send(string.format('{ seq = 14, op = "set_lut", path = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01", curves = { { curve = "Main.ColorFromCurve002.ColorCurve", hex = "%s", samples = 46, tmin = 0.0, tmax = 0.55560302734375 }, { curve = "Main.ColorFromCurve001.ColorCurve", hex = "%s" }, { curve = "Nope.Curve", hex = "%s" } } }', hx, hx, hx))
print(s)
print(#writes, "writes")
