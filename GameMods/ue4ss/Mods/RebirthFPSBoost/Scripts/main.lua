-- RebirthFPSBoost (UE4SS Lua mod for FINAL FANTASY VII REBIRTH)
--   Frame-rate presets: sets of engine console variables (presets.lua, next to the Scripts folder) applied as the
--   game starts, again after every map load, and whenever you switch.
--     Ctrl+F1  next preset (Off -> Light -> Balanced -> Performance -> Max -> Off ...); remembered for the next launch
--     Ctrl+F2  measure: the frame rate over 5 seconds (average, and the slowest of the sampled frames), in the UE4SS console
--   "Off" puts back the values the game had before this mod first changed them. A variable the game does not have, or
--   will not change, is named in the console and skipped.
--   Calls into the game are made on the game thread, one queued call at a time (UE4SS 3.0.1's ExecuteInGameThread is
--   not safe at frame rate), so the mod costs nothing between key presses and map loads.

local MOD = "RebirthFPSBoost"
local VERSION = "1.0"

local function log(text)
    print(string.format("[%s] %s\n", MOD, text))
end

-- ---------------------------------------------------------------------------------------------------------------
-- files: presets.lua and state.txt in the mod's folder
-- ---------------------------------------------------------------------------------------------------------------
local function modDir()
    local src = debug.getinfo(1, "S").source or ""
    src = src:gsub("^@", ""):gsub("\\", "/")
    local dir = src:match("^(.*)/[Ss]cripts/[^/]*$")
    if dir and dir ~= "" then return dir end
    return "Mods/" .. MOD
end
local DIR = modDir()

local function readFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local s = f:read("*a")
    f:close()
    return s
end

local function writeFile(path, text)
    local f = io.open(path, "w")
    if not f then return false end
    f:write(text)
    f:close()
    return true
end

local config
do
    local ok, cfg = pcall(dofile, DIR .. "/presets.lua")
    if ok and type(cfg) == "table" and type(cfg.presets) == "table" and type(cfg.order) == "table" then
        config = cfg
    else
        log("presets.lua could not be read (" .. tostring(cfg) .. "): only Off is available")
        config = { default = "Off", order = { "Off" }, presets = { Off = {} }, max_fps = 0 }
    end
end

local function indexOf(name)
    for i, n in ipairs(config.order) do
        if n == name then return i end
    end
    return nil
end

local current = (readFile(DIR .. "/state.txt") or ""):match("^%s*(.-)%s*$")
if not indexOf(current) then current = indexOf(config.default) and config.default or config.order[1] end

-- ---------------------------------------------------------------------------------------------------------------
-- the game
-- ---------------------------------------------------------------------------------------------------------------
local function valid(o)
    return o ~= nil and o.IsValid ~= nil and o:IsValid()
end

local KSL, GS
local function libs()
    if not valid(KSL) then KSL = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary") end
    if not valid(GS) then GS = StaticFindObject("/Script/Engine.Default__GameplayStatics") end
    return valid(KSL) and KSL or nil, valid(GS) and GS or nil
end

local function controller()
    local pc = FindFirstOf("PlayerController")
    if valid(pc) then return pc end
    return nil
end

local function onGameThread()
    if type(RebirthSkelCompatIsGameThread) == "function" then
        local ok, yes = pcall(RebirthSkelCompatIsGameThread)
        return not ok or yes
    end
    return true
end

local function fmt(v)
    if type(v) ~= "number" then return tostring(v) end
    if v == math.floor(v) and math.abs(v) < 1e9 then return string.format("%d", v) end
    return string.format("%.4g", v)
end

local function getValue(name)
    local ksl = libs()
    if not ksl then return nil end
    local ok, v = pcall(function() return ksl:GetConsoleVariableFloatValue(name) end)
    if ok and type(v) == "number" then return v end
    return nil
end

local function run(cmd)
    local ksl = libs()
    local pc = controller()
    if not ksl or not pc then return false end
    local ok = pcall(function() ksl:ExecuteConsoleCommand(pc, cmd, pc) end)
    return ok
end

-- ---------------------------------------------------------------------------------------------------------------
-- presets
-- ---------------------------------------------------------------------------------------------------------------
local originals = {}     -- console variable -> the value the game had before this mod first changed it
local touched = {}       -- the variables this mod has changed, in order
local capOriginal = nil

local function allNames()
    local out, seen = {}, {}
    for _, name in ipairs(config.order) do
        for _, kv in ipairs(config.presets[name] or {}) do
            if not seen[kv[1]] then
                seen[kv[1]] = true
                out[#out + 1] = kv[1]
            end
        end
    end
    return out
end

local function remember(name)
    if originals[name] ~= nil then return end
    local v = getValue(name)
    if v ~= nil then
        originals[name] = v
        touched[#touched + 1] = name
    end
end

local function applyPreset(name, why)
    if not controller() then return false end
    local list = config.presets[name] or {}
    local set, refused = 0, {}
    local wanted = {}
    for _, kv in ipairs(list) do wanted[kv[1]] = kv[2] end
    -- what the preset does not name goes back to the game's own value (a lighter preset after a heavier one)
    for _, cvar in ipairs(touched) do
        if wanted[cvar] == nil and originals[cvar] ~= nil then
            run(cvar .. " " .. fmt(originals[cvar]))
        end
    end
    for _, kv in ipairs(list) do
        local cvar, value = kv[1], kv[2]
        remember(cvar)
        run(cvar .. " " .. fmt(value))
        local now = getValue(cvar)
        if now ~= nil and math.abs(now - value) < 1e-3 then
            set = set + 1
        else
            refused[#refused + 1] = cvar
        end
    end
    local cap = tonumber(config.max_fps) or 0
    if cap > 0 then
        if capOriginal == nil then capOriginal = getValue("t.MaxFPS") or 0 end
        run("t.MaxFPS " .. fmt(cap))
    elseif capOriginal ~= nil then
        run("t.MaxFPS " .. fmt(capOriginal))
    end
    local line = string.format("preset %s (%s): %d of %d settings took", name, why, set, #list)
    if #refused > 0 then line = line .. "; not in this game or not changeable: " .. table.concat(refused, ", ") end
    if cap > 0 then line = line .. string.format("; frame cap %d", cap) end
    log(line)
    return true
end

-- ---------------------------------------------------------------------------------------------------------------
-- measuring the frame rate
-- ---------------------------------------------------------------------------------------------------------------
local measuring = nil

local function measureStart()
    local ksl, gs = libs()
    local pc = controller()
    if not ksl or not gs or not pc then log("measure: the game is not ready"); return end
    local okF, frames = pcall(function() return ksl:GetFrameCount() end)
    local okT, t = pcall(function() return gs:GetRealTimeSeconds(pc) end)
    if not okT or type(t) ~= "number" then log("measure: no clock (GetRealTimeSeconds)"); return end
    measuring = { frames = okF and tonumber(frames) or nil, t = t, worst = 0, samples = 0, sum = 0, clock = os.clock() }
    log("measuring the frame rate for 5 seconds (preset " .. current .. ")...")
end

local function measureSample()
    if not measuring then return end
    local _, gs = libs()
    local pc = controller()
    if not gs or not pc then return end
    local ok, dt = pcall(function() return gs:GetWorldDeltaSeconds(pc) end)
    if ok and type(dt) == "number" and dt > 0 then
        measuring.samples = measuring.samples + 1
        measuring.sum = measuring.sum + dt
        if dt > measuring.worst then measuring.worst = dt end
    end
end

local function measureEnd()
    if not measuring then return end
    local m = measuring
    measuring = nil
    local ksl, gs = libs()
    local pc = controller()
    if not ksl or not gs or not pc then log("measure: the game went away"); return end
    local okF, frames = pcall(function() return ksl:GetFrameCount() end)
    local okT, t = pcall(function() return gs:GetRealTimeSeconds(pc) end)
    local seconds = (okT and type(t) == "number") and (t - m.t) or 0
    local avg
    if m.frames and okF and tonumber(frames) and seconds > 0 then
        avg = (tonumber(frames) - m.frames) / seconds
    elseif m.samples > 0 then
        avg = m.samples / m.sum
    end
    if not avg then log("measure: nothing measured"); return end
    log(string.format("frame rate with %s: %.1f fps on average (%.1f ms a frame); slowest sampled frame %.1f ms (%d samples over %.1f s)",
        current, avg, 1000 / avg, 1000 * m.worst, m.samples, seconds))
end

-- ---------------------------------------------------------------------------------------------------------------
-- the queue: jobs run on the game thread, one queued call at a time
-- ---------------------------------------------------------------------------------------------------------------
local jobs = {}
local queued = false
local appliedOnce = false
local reapply = true      -- apply as soon as the game is up
local measureEndAt = nil
local nextSampleAt = 0

local function later(fn) jobs[#jobs + 1] = fn end

local function runJobs()
    local list = jobs
    jobs = {}
    for _, fn in ipairs(list) do
        local ok, err = pcall(fn)
        if not ok then log("error: " .. tostring(err)) end
    end
end

LoopAsync(250, function()
    local t = os.clock()
    if reapply then
        later(function()
            if applyPreset(current, appliedOnce and "after a map load" or "at start") then
                reapply = false
                appliedOnce = true
            end
        end)
    end
    if measuring and t >= nextSampleAt then
        nextSampleAt = t + 0.25
        later(measureSample)
    end
    if measureEndAt and t >= measureEndAt then
        measureEndAt = nil
        later(measureEnd)
    end
    if #jobs > 0 and not queued then
        queued = true
        ExecuteInGameThread(function()
            queued = false
            if not onGameThread() then return end   -- (UE4SS ran it elsewhere: the jobs wait for the next call)
            runJobs()
        end)
    end
    return false
end)

-- after every map load the game may set its own values again: the preset goes back on
pcall(function()
    RegisterHook("/Script/Engine.PlayerController:ClientRestart", function()
        reapply = true
    end)
end)

RegisterKeyBind(Key.F1, { ModifierKey.CONTROL }, function()
    later(function()
        local i = indexOf(current) or 1
        current = config.order[i % #config.order + 1]
        writeFile(DIR .. "/state.txt", current .. "\n")
        if not applyPreset(current, "Ctrl+F1") then
            reapply = true
            log("preset " .. current .. " chosen: it goes on when the game is up")
        end
    end)
end)

RegisterKeyBind(Key.F2, { ModifierKey.CONTROL }, function()
    later(function()
        if measuring then log("already measuring"); return end
        measureStart()
        if measuring then measureEndAt = os.clock() + 5.0 end
    end)
end)

log(string.format("%s %s ready: preset %s (Ctrl+F1 next preset, Ctrl+F2 measure the frame rate); presets: %s",
    MOD, VERSION, current, table.concat(config.order, ", ")))
