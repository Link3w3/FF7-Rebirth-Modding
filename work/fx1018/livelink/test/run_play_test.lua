-- 1.6: a live edit plays the effect when nothing is playing (after a game restart nothing is), replays it when it is
local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")
dofile(root .. "/scripts/main.lua")
local PATH = "/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01"
local failures = 0
local function check(what, ok)
    print((ok and "ok    " or "FAIL  ") .. what)
    if not ok then failures = failures + 1 end
end
local function status()
    return io.open(root .. "/link/status.json"):read("a")
end
local function send(cmd)
    local f = io.open(root .. "/link/command.lua", "w"); f:write("return " .. cmd .. "\n"); f:close()
    RebirthSkelCompatPump(); RebirthSkelCompatPump()
    return status()
end
local function floatsHex(t) local p = {} for i, v in ipairs(t) do p[i] = H.tohex(string.pack("<f", v)) end return table.concat(p) end
local green = {}
for k = 1, 46 do green[#green + 1] = 0.1; green[#green + 1] = 1.0; green[#green + 1] = 0.2; green[#green + 1] = 1.0 end
local edit = string.format('op = "set_lut", path = "%s", curves = { { curve = "Main.ColorFromCurve002.ColorCurve", hex = "%s", samples = 46, tmin = 0.0, tmax = 0.55560302734375 } }', PATH, floatsHex(green))

RebirthSkelCompatPump()
local s = status()
check("status has version 1.6 and started", s:find('"version":"1.6"', 1, true) ~= nil and s:find('"started":', 1, true) ~= nil)
check("nothing plays at the start", spawnedCount == 0 and s:find('"looping"', 1, true) == nil)

-- an edit with nothing playing: it plays
s = send("{ seq = 20, " .. edit .. " }")
check("edit with nothing playing: ok", s:find('"ok":true', 1, true) ~= nil)
check("edit with nothing playing: started", s:find('"play":"started"', 1, true) ~= nil)
check("edit with nothing playing: the status says it is looping", s:find('"looping":"' .. PATH .. '"', 1, true) ~= nil)
RebirthSkelCompatPump()
check("the effect spawned after the edit (" .. spawnedCount .. ")", spawnedCount >= 1)

-- another edit: replayed at once
local before = spawnedCount
s = send("{ seq = 21, " .. edit .. " }")
check("edit while it plays: replayed", s:find('"play":"replayed"', 1, true) ~= nil)
RebirthSkelCompatPump()
check("the edit replayed it (" .. (spawnedCount - before) .. " new)", spawnedCount > before)

-- it keeps replaying every 4 s (the fake clock moves 0.3 s per call)
before = spawnedCount
for _ = 1, 40 do RebirthSkelCompatPump() end
check("it keeps replaying (" .. (spawnedCount - before) .. " replays)", spawnedCount - before >= 2)

-- stop, then an edit with play = false: nothing plays
s = send("{ seq = 22, op = \"stop\" }")
check("stop ends the replays", s:find('"looping"', 1, true) == nil)
s = send("{ seq = 23, play = false, " .. edit .. " }")
check("play = false: written, not started", s:find('"ok":true', 1, true) ~= nil and s:find('"play":', 1, true) == nil and s:find('"looping"', 1, true) == nil)

-- an edit that writes nothing does not start anything
s = send(string.format('{ seq = 24, op = "set_lut", path = "%s", curves = { { curve = "Nope.Curve", hex = "%s" } } }', PATH, floatsHex(green)))
check("failed edit: not ok, nothing started", s:find('"ok":false', 1, true) ~= nil and s:find('"looping"', 1, true) == nil)

-- an effect that is not loaded: the answer says it is loading (the editor sends the edit again)
s = send(string.format('{ seq = 25, op = "set_lut", path = "/Game/Effect/Nope/FX_Nope", curves = { { curve = "Main.ColorFromCurve002.ColorCurve", hex = "%s" } } }', floatsHex(green)))
check("unloaded effect: loading = true", s:find('"loading":true', 1, true) ~= nil and s:find('"looping"', 1, true) == nil)

-- a different effect playing: an edit of this one switches to it
s = send(string.format('{ seq = 26, op = "spawn", path = "/Game/Effect/Nope/FX_Nope", loop = true }'))
check("another effect loops", s:find('"looping":"/Game/Effect/Nope/FX_Nope"', 1, true) ~= nil)
s = send("{ seq = 27, " .. edit .. " }")
check("edit of this one: it plays instead", s:find('"play":"started"', 1, true) ~= nil and s:find('"looping":"' .. PATH .. '"', 1, true) ~= nil)

local log = io.open(root .. "/link/log.txt"):read("a")
check("the log says it plays", log:find("set_lut: ok (playing it now, again every 4 s)", 1, true) ~= nil)
print(log)
print(failures == 0 and "ALL PASSED" or (failures .. " FAILED"))
os.exit(failures == 0 and 0 or 1)
