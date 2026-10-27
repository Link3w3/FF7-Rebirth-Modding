local H = dofile("harness.lua")
local root = "tmp/Mods/RebirthLiveLink"
os.execute("rm -rf tmp && mkdir -p " .. root .. "/scripts " .. root .. "/link")
os.execute("cp ../RebirthLiveLink/Scripts/main.lua " .. root .. "/scripts/main.lua")
dofile(root .. "/scripts/main.lua")
local function send(cmd)
    local f = io.open(root .. "/link/command.lua", "w"); f:write("return " .. cmd .. "\n"); f:close()
    RebirthSkelCompatPump(); RebirthSkelCompatPump()
    return io.open(root .. "/link/status.json"):read("a")
end
RebirthSkelCompatPump()
print(send('{ seq = 1, op = "lua", code = [==[ return { v = link.version, pawn = link.fullName(link.player()), mem = link.memory, n = 1 + 2 } ]==] }'))
print(send('{ seq = 2, op = "lua", code = [==[ ticks = 0; link.every("count", function() ticks = ticks + 1 end); return link.hooks() ]==] }'))
for i = 1, 10 do RebirthSkelCompatPump() end
print(send('{ seq = 3, op = "lua", code = [==[ local t = ticks; link.cancel("count"); return t ]==] }'))
print(send('{ seq = 4, op = "lua", code = [==[ local a = {}; a.self = a; return a, 5, "x" ]==] }'))
print(send('{ seq = 5, op = "lua", code = [==[ error("boom") ]==] }'))
print(send('{ seq = 6, op = "lua", code = [==[ this is not lua ]==] }'))
print(send('{ seq = 7, op = "lua", code = [==[ link.every("bad", function() error("hook fails") end); return true ]==] }'))
for i = 1, 30 do RebirthSkelCompatPump() end
print(send('{ seq = 8, op = "lua", code = [==[ return link.hooks() ]==] }'))
print(send('{ seq = 9, op = "ping" }'))
print(io.open(root .. "/link/log.txt"):read("a"))
