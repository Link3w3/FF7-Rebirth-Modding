-- HairDitherFix: FINAL FANTASY VII REBIRTH's grainy hair, for UE4SS 3.0.1.
--
-- The game cuts hair (and other "coverage" cut-outs) out per pixel by testing the coverage map against a moving blue
-- noise (the engine's SpatiotemporalBlueNoiseVolume, its red channel), so that TAA can blend the pattern into soft
-- strands. At 1080p, with TAAU, DLSS or FSR the blend falls apart and hair looks grainy. This mod points the engine at
-- a version of that noise with a calmer red channel (green, blue and alpha - used for other things - are the game's):
--
--   Soft    (default) only coverage near 50% still dithers: soft strand edges, far less grain
--   Stable  the same pattern every frame: no crawling, a fine fixed pattern instead
--   Off     no dither: a clean cut-out at 50% coverage (sharpest, wispy strand tips thin out)
--   Game    the game's own noise
--
-- Ctrl+H cycles the modes; the choice is kept in mode.txt next to this file. Needs HairDitherFix_P.pak/.ucas/.utoc
-- in the game's Content\Paks\~mods folder (the three noise textures).

local MOD = "HairDitherFix"
local VERSION = "1.0"
local MODES = { "Soft", "Stable", "Off", "Game" }
local PATHS = {
    Soft = "/Game/HairDitherFix/STBN_Soft.STBN_Soft",
    Stable = "/Game/HairDitherFix/STBN_Stable.STBN_Stable",
    Off = "/Game/HairDitherFix/STBN_Off.STBN_Off",
    Game = "/Engine/EngineResources/SpatiotemporalBlueNoiseVolume.SpatiotemporalBlueNoiseVolume",
}

local function scriptDir()
    local src = debug.getinfo(1, "S").source:gsub("^@", "")
    return src:match("^(.*)[/\\][^/\\]+$") or "."
end
local function modDir(dir)
    local base, last = dir:match("^(.*)[/\\]([^/\\]+)$")
    if last and last:lower() == "scripts" then return base end
    return dir
end
local MOD_DIR = modDir(scriptDir())
local MODE_FILE = MOD_DIR .. "/mode.txt"

local function log(text)
    print(string.format("[%s] %s\n", MOD, text))
end

local function valid(o)
    if o == nil then return false end
    local ok, yes = pcall(function() return o:IsValid() end)
    return ok and yes
end

local function readMode()
    local f = io.open(MODE_FILE, "r")
    if not f then return "Soft" end
    local m = (f:read("*l") or ""):gsub("%s", "")
    f:close()
    for _, x in ipairs(MODES) do if x:lower() == m:lower() then return x end end
    return "Soft"
end

local function writeMode(m)
    local f = io.open(MODE_FILE, "w")
    if f then f:write(m .. "\n"); f:close() end
end

local wanted = readMode()
local applied = nil          -- the mode the engine has now
local original = nil         -- the game's own noise (kept for "Game")
local registryHelpers = nil

-- mod packages are not in the game's asset registry: load them by path with the engine's loader
local function load(path)
    local o = StaticFindObject(path)
    if valid(o) then return o end
    local ok, loaded = pcall(function() return LoadAsset(path) end)
    if ok and valid(loaded) then return loaded end
    if not valid(registryHelpers) then
        registryHelpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
    end
    if valid(registryHelpers) then
        local ok2, o2 = pcall(function() return registryHelpers:GetAsset({ ObjectPath = FName(path) }) end)
        if ok2 and valid(o2) then return o2 end
    end
    return nil
end

local function engine()
    local e = FindFirstOf("GameEngine")
    if valid(e) then return e end
    return nil
end

-- (game thread only)
local function apply()
    local e = engine()
    if not e then return false end
    local current = e.SpatiotemporalBlueNoiseVolume
    if original == nil and valid(current) then
        local name = current:GetFullName()
        if not name:find("HairDitherFix") then original = current end
    end
    local target = (wanted == "Game") and (original or load(PATHS.Game)) or load(PATHS[wanted])
    if not valid(target) then
        if applied ~= "missing" then
            log("the " .. wanted .. " noise is not there (is HairDitherFix_P in Content\\Paks\\~mods?): the game's noise stays")
            applied = "missing"
        end
        return false
    end
    if not (valid(current) and current:GetAddress() == target:GetAddress()) then
        e.SpatiotemporalBlueNoiseVolume = target
    end
    if applied ~= wanted then
        applied = wanted
        log("hair dither: " .. wanted .. " (" .. target:GetFullName() .. ")")
    end
    return true
end

local queued = false
local function request()
    if queued then return end
    queued = true
    ExecuteInGameThread(function()
        queued = false
        pcall(apply)
    end)
end

-- keep it applied (the engine has it from the start; this also puts it back if anything resets it)
local ticks = 0
LoopAsync(2000, function()
    ticks = ticks + 1
    if applied ~= wanted or ticks % 5 == 0 then request() end
    return false
end)

RegisterKeyBind(Key.H, { ModifierKey.CONTROL }, function()
    local i = 1
    for k, m in ipairs(MODES) do if m == wanted then i = k end end
    wanted = MODES[i % #MODES + 1]
    writeMode(wanted)
    log("Ctrl+H: " .. wanted)
    request()
end)

log(string.format("%s %s ready: mode %s (Ctrl+H: Soft / Stable / Off / Game)", MOD, VERSION, wanted))
