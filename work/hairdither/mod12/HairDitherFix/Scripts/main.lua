-- HairDitherFix 1.2: FINAL FANTASY VII REBIRTH's grainy hair, switchable in game (UE4SS 3.0.1).
--
-- The game cuts hair out per pixel against a moving blue noise (the engine's SpatiotemporalBlueNoiseVolume, its red
-- channel) and relies on TAA to blend the pattern into soft strands; at 1080p or with TAAU / DLSS / FSR it shows as
-- grain. This mod points the engine at a calmer noise (HairDitherFix_P: only the red channel differs):
--   Soft    (default) only coverage near 50% still dithers
--   Stable  the same pattern every frame: no crawling
--   Off     no dither: a clean cut-out
--   Game    the game's own noise
-- Ctrl+H cycles them (kept in mode.txt).
--
-- Safety: the engine loaded its own noise at start-up and nothing else holds it; before the engine is pointed at
-- another noise, the game's is kept referenced (in the engine's GameSingleton slot when the game leaves it empty, else
-- in the asset manager's keep-alive list), so it is never unloaded. If neither can hold it, the mod does nothing.

local MOD = "HairDitherFix"
local VERSION = "1.2"
local MODES = { "Soft", "Stable", "Off", "Game" }
local PATHS = {
    Soft = "/Game/HairDitherFix/STBN_Soft.STBN_Soft",
    Stable = "/Game/HairDitherFix/STBN_Stable.STBN_Stable",
    Off = "/Game/HairDitherFix/STBN_Off.STBN_Off",
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
local MODE_FILE = modDir(scriptDir()) .. "/mode.txt"

local function log(text) print(string.format("[%s] %s\n", MOD, text)) end
local function valid(o)
    if o == nil then return false end
    local ok, yes = pcall(function() return o:IsValid() end)
    return ok and yes
end
local function same(a, b)
    if not (valid(a) and valid(b)) then return false end
    local ok, r = pcall(function() return a:GetAddress() == b:GetAddress() end)
    return ok and r
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
local applied = nil
local original = nil          -- the game's own noise
local kept = nil              -- where it is kept: "singleton" | "asset manager" | false (nowhere: no swapping)
local registryHelpers = nil

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

-- keep the game's noise referenced (once): the engine's GameSingleton slot if the game leaves it empty, else the asset
-- manager's ObjectReferenceList (its own keep-alive list)
local function keepOriginal(e)
    if kept ~= nil then return kept end
    local okS, singleton = pcall(function() return e.GameSingleton end)
    if okS and not valid(singleton) then
        local ok = pcall(function() e.GameSingleton = original end)
        if ok and same(e.GameSingleton, original) then
            kept = "singleton"
            return kept
        end
    end
    local okA, am = pcall(function() return e.AssetManager end)
    if okA and valid(am) then
        local ok = pcall(function()
            local list = am.ObjectReferenceList
            local n = list:GetArrayNum()
            list[n + 1] = original
        end)
        if ok then
            local found = false
            pcall(function()
                am.ObjectReferenceList:ForEach(function(i, el)
                    if same(el:get(), original) then found = true end
                end)
            end)
            if found then
                kept = "asset manager"
                return kept
            end
        end
    end
    kept = false
    return kept
end

-- (game thread)
local function apply()
    local e = FindFirstOf("GameEngine")
    if not valid(e) then return end
    local current = e.SpatiotemporalBlueNoiseVolume
    if original == nil then
        if not valid(current) then return end
        if current:GetFullName():find("HairDitherFix") then
            log("the engine's noise is already one of this mod's (the mod restarted?): the game's is not known, Game mode is off")
        else
            original = current
        end
    end
    local target
    if wanted == "Game" then
        target = original
    else
        target = load(PATHS[wanted])
        if not valid(target) then
            if applied ~= "missing" then
                log("the " .. wanted .. " noise is not there: install HairDitherFix_P (.pak/.ucas/.utoc) in Content\\Paks\\~mods")
                applied = "missing"
            end
            return
        end
        if original ~= nil and not keepOriginal(e) then
            if applied ~= "unsafe" then
                log("nothing can keep the game's own noise loaded here, so the mod leaves it in place (use the HairDitherFix pak instead)")
                applied = "unsafe"
            end
            return
        end
    end
    if not valid(target) then return end
    if not same(current, target) then e.SpatiotemporalBlueNoiseVolume = target end
    if applied ~= wanted then
        applied = wanted
        log("hair dither: " .. wanted .. (kept and (" (the game's noise kept by the " .. kept .. ")") or ""))
    end
end

local queued = false
local function request()
    if queued then return end
    queued = true
    ExecuteInGameThread(function()
        queued = false
        local ok, err = pcall(apply)
        if not ok then log("error: " .. tostring(err)) end
    end)
end

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
