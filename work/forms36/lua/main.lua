-- SephirothForms: your playable Sephiroth (he plays in Cloud's slot) changes form in battle.
--   His forms: normal, winged (animation pack Battle02), flying (Battle03), KH2 (Battle04: his Kingdom Hearts II moves).
--   Hold Triangle (the controller's top face button) in battle: the moveset menu opens (FormMenu.lua: a command window
--   like the game's, a row per form with the way to tilt the left stick for it). Tilt the stick that way (the row lights
--   up) and let go of Triangle: he switches to it.
--   Let go without lighting one up: nothing changes. A tap is still his Triangle attack. (CONFIG.menu.enabled = false:
--   each hold moves him to the next form instead, normal -> winged -> flying -> KH2 -> normal.)
--   Every switch plays a cue on him: an aura and a sound (CONFIG.cues). After his level 2 limit (Heartless Angel, on
--   Cloud's PC0000_Limit002) he switches to flying by himself.
--   His wing is hidden in his normal form and comes out in the winged, flying and KH2 forms, in a burst of black feathers
--   (CONFIG.wing). The wing is part of his model: SephirothTransformedBaseModel_P (the transformed
--   Sephiroth's model in his model's place, slot PC0010_10_Wing) or KH2Sephiroth_P (the KH2 model, slot Wing); either
--   works, so you can switch between the two models. Without a model with a wing there is no wing to show.
--   Every effect the mod plays lasts a moment, then fades and is removed (CONFIG.effects). A new switch first ends the
--   effects of the switch before it, so they never pile up on him.
--   The packs come from Create a Character System (compat\SephirothForms.json). Everything goes back when the battle ends.
--   Grip of Fate and Skewer catch every enemy, bosses too (ForceGrabs.lua): Grip of Fate's feeler binds the enemy it hits,
--   Skewer lifts the enemy on his sword and throws it off flying. Meteor is a cinematic (MeteorStrike.lua).
-- Keyboard: F2 turns his model for the KH2 moves another 90 degrees (CONFIG.kh2Turn), F4 next feather effect (preview),
--   F5 status, F6 winged now, F7 flying now, F8 back to normal, F9 KH2 now;
--   tests: F10 Battle02 pack only, F11 Battle00_Comp pack only.
-- Log lines start with [SephirothForms] in ue4ss\UE4SS.log. Rename enabled.txt to turn the mod off.

-- Black feathers bursting (from a cutscene where Sephiroth arrives in a shower of them).
local FEATHERS = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_01.FX_EV_FOREE_7250_BlackFeather_01"
local WING_ROOT = "R_FeatherShoulder_a" -- where his wing meets his shoulder

local CONFIG = {
    playerType = 0, -- EPlayerType::CLOUD: your Sephiroth plays in Cloud's slot
    rows = {
        PC0000_00_Cloud_Standard = true,
        PC0000_08_Cloud_SoldierNoHelmet = true,
        PC0000_09_Cloud_CostaClothing = true,
        PC0000_10_Cloud_CostaClothing2 = true,
        -- the prologue's Cloud in Zack's SOLDIER outfit ("CloudZack"), as Sephiroth too
        PC0000_04_Cloud_ZackCostume = true,
        PC0000_12_Cloud_ZackCostumeDirty = true,
        PC0000_18_Cloud_ZackCostumeAge21 = true,
        PC0000_19_Cloud_ZackCostumeDirtyAge21 = true,
        PC0000_23_Cloud_ZackCostumeWet = true,
    },
    -- Holding Triangle while he is the character you control opens the moveset menu (menu.openSeconds), or, with the
    -- menu off, switches him to the next form (holdSeconds).
    holdKeys = { "Gamepad_FaceButton_Top" },
    holdSeconds = 0.5,
    -- The form each hold moves to, from the one he is in (menu off).
    nextForm = { [0] = 1, [1] = 2, [2] = 3, [3] = 0 },
    -- The moveset menu (FormMenu.lua): where each form sits on it (from the middle of the screen, in pixels) and the
    -- direction of the left stick that lights it up.
    -- (FormMenu.lua draws them as rows of a command window like the game's, top to bottom: up, left, right, down)
    menu = {
        enabled = true,
        openSeconds = 0.35,
        forms = {
            [1] = { name = "WINGED", x = 0.0, y = -120.0, stick = "up" },
            [2] = { name = "FLYING", x = 230.0, y = 0.0, stick = "right" },
            [3] = { name = "KH2", x = 0.0, y = 120.0, stick = "down" },
            [0] = { name = "NORMAL", x = -230.0, y = 0.0, stick = "left" },
        },
        stick = { x = "Gamepad_LeftX", y = "Gamepad_LeftY", deadZone = 0.5 },
    },
    -- What plays on him when he switches to a form: effects (Niagara or Cascade, attached to his mesh at socket, a socket
    -- or bone of his model; none = his root; scale = size; seconds = stop it after that long) and sounds (a cue of a sound
    -- bank; voice = true takes his voice bank in the language the game loaded).
    cues = {
        [1] = { -- winged
            effects = {
                { path = "/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Limit01_BodyAura_01.FX_PC0010_Limit01_BodyAura_01" },
                { path = "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_SetFeeler_Wing_01.FX_PC0010_10_SetFeeler_Wing_01" },
            },
            sounds = {
                { bank = "/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard", name = "SE_PC0010_10_B_AtkTenshi01_0_whoosh" },
                { voice = true, name = "Atk_Ability_02" },
            },
        },
        [2] = { -- flying
            effects = {
                { path = "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_Tenshi_Charge_01.FX_PC0010_10_Tenshi_Charge_01" },
                { path = "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_SetFeeler_Wing_01.FX_PC0010_10_SetFeeler_Wing_01" },
            },
            sounds = {
                { bank = "/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard", name = "SE_PC0010_10_B_AtkTenshi01_1_jump" },
                { voice = true, name = "Atk_Ability_01" },
            },
        },
        [3] = { -- KH2: black feathers burst around him
            effects = {
                { path = FEATHERS, socket = WING_ROOT },
                { path = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_Aura_01.FX_EV_FOREE_7250_BlackFeather_Aura_01" },
            },
            sounds = {
                { bank = "/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard", name = "SE_PC0010_10_B_AtkTenshi01_0_whoosh" },
                { voice = true, name = "Atk_Ability_01" },
            },
        },
        [0] = { -- back to normal
            effects = {
                { path = "/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Aura_Body_01.FX_PC0010_Aura_Body_01" },
            },
            sounds = {
                { bank = "/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard", name = "SE_PC0010_10_B_AtkTenshi01_1_squat" },
            },
        },
    },
    voiceBanks = { "US", "JP", "FR", "DE" }, -- /Game/Sound/Voice/<language>/Character/Player/VO_PC0010_00_Sephiroth
    wingedAfter = nil, -- was "PC0010_Limit001" (after Octaslash); the form now comes from holding Triangle
    flyingAfter = "PC0000_Limit002", -- his level 2 limit, Heartless Angel (Cloud's limit row: it unlocks like Cloud's)
    wingedPack = "Battle02",
    flyingPack = "Battle03",
    kh2Pack = "Battle04",       -- his KH2 moves (compat\SephirothForms.json, his own Battle00 underneath)
    -- His model's turn (yaw) while he is in the KH2 form. 0: none. His KH2 moves are built facing the way he goes (the
    -- KH2 remaps hold him turned to his left of it; Create a Character System's KH2 build turns him back), so his model
    -- is not turned (turning it turns the way he runs too). F2 turns it another 90 degrees (live, in the KH2 form).
    kh2Turn = 0.0,
    -- His wing: the material slot of his model it is drawn with, the first of `slots` his model has (the transformed
    -- Sephiroth's model: PC0010_10_Wing; the KH2 model: Wing). method "section" has the engine hide that part of his
    -- model (ShowMaterialSection, every level of detail, its shadow too); "material" puts a see-through copy of the
    -- wing's material in the slot instead (its Coverage mask black, clearTexture).
    -- fadeSeconds: the wing fades in and out this long, through a copy of its material whose fadeParameter goes from 1
    -- to 0 (then the section is hidden); 0: it comes and goes at once, in its burst of feathers.
    wing = {
        enabled = true,
        slots = { "PC0010_10_Wing", "Wing" },
        method = "section",
        fadeSeconds = 0.0, -- 0.6: the fade (NativePrimitiveCoverage of a copy of the wing's material; untested in this game)
        fadeParameter = "NativePrimitiveCoverage",
        -- Feathers burst from the wing when it comes out and when it goes (effects as in cues).
        appear = { { path = FEATHERS, socket = WING_ROOT } },
        vanish = { { path = FEATHERS, socket = WING_ROOT } },
        -- Other copies of his model (cutscenes, the reserve party) keep the wing hidden.
        hideOnOthers = true,
    },
    clearTexture = "/Game/Renderer/Texture/000000FF_BC4.000000FF_BC4",
    -- How long the mod's effects play. Each kind (cue: the switch effects, wing: the feathers, preview: F4) plays this
    -- many seconds, then stops (an effect in a list can set its own: seconds = ...); its last particles then fade for
    -- fadeSeconds and whatever is left is removed. A new switch, feather burst or preview ends the ones of its kind
    -- that are still playing, and at most `max` play at once (the oldest ends first).
    effects = {
        seconds = { cue = 2.5, wing = 2.0, preview = 5.0 },
        fadeSeconds = 2.0,
        max = 6,
    },
    -- F4 plays these on him one at a time (each for effects.seconds.preview), so you can pick the feathers for
    -- wing.appear/vanish.
    featherPreview = {
        { path = FEATHERS, socket = WING_ROOT },
        { path = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_8312/Particle/FX_EV_FOREE_8312_BlackFeather_01.FX_EV_FOREE_8312_BlackFeather_01", socket = WING_ROOT },
        { path = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_8312/Particle/FX_EV_FOREE_8312_BlackFeather_FadeOut_01.FX_EV_FOREE_8312_BlackFeather_FadeOut_01", socket = WING_ROOT },
        { path = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_8510/Particle/FX_EV_FOREE_8510_BlackFeather_01.FX_EV_FOREE_8510_BlackFeather_01", socket = WING_ROOT },
        { path = "/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_Aura_01.FX_EV_FOREE_7250_BlackFeather_Aura_01" },
        { path = "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_Tenshi_Charge_01.FX_PC0010_10_Tenshi_Charge_01" },
        { path = "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_Tenshi_Area_01.FX_PC0010_10_Tenshi_Area_01" },
        { path = "/Game/Effect/Character/Enemy/EB2210_BizarroSephiroth/Particle/FX_EB2210_Angel_Area_01.FX_EB2210_Angel_Area_01" },
    },
}

local TICK_SECONDS = 0.2 -- the main tick: every 200 ms
local INPUT_SECONDS = 0.05 -- Triangle, the menu and the wing's fades: every frame (UE4SS loop: every 50 ms)

-- RebirthSkelCompat's frame pump (3.5.3+) drives the mod once it runs (see the end of this file).
local pumping = false
-- Create a Character System 3.6 changes his forms itself (compat\SephirothForms.json "forms": the forms menu, his wing,
-- the switch effects and sounds, flying after Heartless Angel, the Bizarro form): this mod then leaves all of that to it
-- and keeps Grip of Fate and Skewer (ForceGrabs.lua), the Meteor cinematic (MeteorStrike.lua) and its keys.
local function dllForms()
    local f = RebirthSkelCompatHasForms
    if type(f) ~= "function" then return false end
    local ok, yes = pcall(f)
    return ok and yes == true
end
-- Whether this runs on the game thread (RebirthSkelCompat 3.5.3+ can tell; without it: taken as yes).
local function onGameThread()
    local f = RebirthSkelCompatIsGameThread
    if type(f) ~= "function" then return true end
    local ok, yes = pcall(f)
    return not ok or yes ~= false
end

local function log(text)
    print(string.format("[SephirothForms] %s %s\n", os.date("%H:%M:%S"), text))
end

local function valid(object)
    if object == nil then return false end
    local ok, result = pcall(function() return object:IsValid() end)
    return ok and result
end

local function str(value)
    if value == nil then return "nil" end
    local ok, text = pcall(function() return value:ToString() end)
    if ok and text then return text end
    return tostring(value)
end

local api = nil
local function battleApi()
    if not valid(api) then api = StaticFindObject("/Script/EndGame.Default__EndBattleAPI") end
    if valid(api) then return api end
    return nil
end

-- ForceGrabs.lua (Grip of Fate, Skewer) and MeteorStrike.lua (the Meteor cinematic) sit next to this file.
do
    local source = debug.getinfo(1, "S").source:gsub("^@", "")
    local dir = source:match("^(.*[/\\])") or ""
    package.path = dir .. "?.lua;" .. package.path
end
local function loadModule(name)
    local okLoad, module = pcall(require, name)
    if okLoad then
        local okInit, errInit = pcall(module.init, { log = log, valid = valid, str = str, battleApi = battleApi,
            pumping = function() return pumping end, onGameThread = onGameThread })
        if okInit then return module end
        log(name .. " didn't start: " .. tostring(errInit))
    else
        log(name .. ".lua not loaded: " .. tostring(module))
    end
    return { tick = function() end }
end
local grabs = loadModule("ForceGrabs")
local meteor = loadModule("MeteorStrike")

-- The moveset menu (FormMenu.lua): without it, holding Triangle switches him to the next form.
local menu = nil
if CONFIG.menu.enabled then
    local okLoad, module = pcall(require, "FormMenu")
    if okLoad then
        local names, sticks = {}, {}
        for form, spot in pairs(CONFIG.menu.forms) do
            names[form] = spot.name
            sticks[form] = spot.stick
        end
        -- its art: the game's menu sprites (loaded when the game has not; under the frame pump RebirthSkelCompat preloads
        -- them, compat\SephirothForms.json)
        local function loadArt(path)
            local object = StaticFindObject(path)
            if valid(object) then return object end
            if pumping then return nil end
            local ok, loaded = pcall(function() return LoadAsset(path) end)
            if ok and valid(loaded) then return loaded end
            return nil
        end
        local okInit, errInit = pcall(module.init, { log = log, valid = valid, load = loadArt }, { names = names, sticks = sticks })
        if okInit then menu = module else log("FormMenu didn't start: " .. tostring(errInit)) end
    else
        log("FormMenu.lua not loaded: " .. tostring(module))
    end
end

-- The character in the watched slot, if it is one of your Sephiroth's rows.
local function sephiroth()
    local a = battleApi()
    if not a then return nil, "EndBattleAPI not found" end
    local char = a:GetPlayerCharacter(CONFIG.playerType)
    if not valid(char) then return nil, "no character in the slot" end
    local spec = str(a:GetCharaSpecName(char)):gsub("^CharaSpec_", "") -- the game gives the pack name
    if not CONFIG.rows[spec] then return nil, "the slot plays " .. spec end
    return char, spec
end

local state = nil -- { name, stage, ability, wingVisible, wingProblem, wingResets }

local function loadObject(path)
    local object = StaticFindObject(path)
    if valid(object) then return object end
    -- (UE4SS's LoadAsset works only inside its own game-thread calls; under the frame pump the mod plays what is loaded:
    -- RebirthSkelCompat preloads it)
    if pumping then return nil end
    local ok, loaded = pcall(function() return LoadAsset(path) end)
    if ok and valid(loaded) then return loaded end
    return nil
end

local function shortName(path)
    return (path:match("([^/%.]+)$") or path)
end

local function meshName(comp)
    local ok, name = pcall(function() return comp.SkeletalMesh:GetFullName() end)
    return ok and name or "?"
end

-- The material in a slot of a mesh component, or nil. This game's GetMaterial takes a layer too (ElementIndex, LayerIndex:
-- the engine asks for 2 parameters); a UFunction called with the wrong number of parameters ends the whole script tick
-- in UE4SS 3.0.1 (pcall does not catch it).
local function materialAt(comp, index)
    local ok, material = pcall(function() return comp:GetMaterial(index, 0) end)
    if ok and valid(material) then return material end
    return nil
end

-- ---------------------------------------------------------------------------------------------------------------
-- Effects
-- ---------------------------------------------------------------------------------------------------------------
-- The effects the mod started: { comp, group, name, ticks = until it stops, fade = until it is removed (once stopped) }.
local active = {}

local function ticksFor(seconds)
    return math.max(1, math.floor(seconds / TICK_SECONDS + 0.5))
end

-- Stops an effect: it spawns nothing more, its last particles fade, and it is removed after effects.fadeSeconds.
local function stopEffect(entry)
    if entry.fade then return end
    if valid(entry.comp) then pcall(function() entry.comp:Deactivate() end) end
    entry.fade = ticksFor(CONFIG.effects.fadeSeconds)
end

local function removeEffect(entry)
    if valid(entry.comp) then pcall(function() entry.comp:K2_DestroyComponent(entry.comp) end) end
end

-- Stops the playing effects of a group ("cue", "wing", "preview"; nil: every group).
local function stopEffects(group)
    for _, entry in ipairs(active) do
        if group == nil or entry.group == group then stopEffect(entry) end
    end
end

-- Every tick: effects whose time is up stop, stopped ones are removed once they had time to fade.
local function updateEffects()
    if #active == 0 then return end
    local keep = {}
    for _, entry in ipairs(active) do
        if valid(entry.comp) then -- (one that finished by itself is gone already)
            if entry.fade then
                entry.fade = entry.fade - 1
                if entry.fade <= 0 then removeEffect(entry) else table.insert(keep, entry) end
            else
                entry.ticks = entry.ticks - 1
                if entry.ticks <= 0 then stopEffect(entry) end
                table.insert(keep, entry)
            end
        end
    end
    active = keep
end

-- At most effects.max playing: the oldest that still plays stops first.
local function makeRoom()
    local playing = 0
    for _, entry in ipairs(active) do
        if not entry.fade then playing = playing + 1 end
    end
    for _, entry in ipairs(active) do
        if playing < CONFIG.effects.max then return end
        if not entry.fade then
            stopEffect(entry)
            playing = playing - 1
        end
    end
end

-- An effect on him: a Niagara system or a Cascade particle system, attached to his mesh. It plays `seconds` (else
-- effect.seconds, else effects.seconds[group]), then stops and fades.
local function playEffect(char, effect, group, seconds)
    local system = loadObject(effect.path)
    if not valid(system) then
        log("effect " .. shortName(effect.path) .. " did not load")
        return nil
    end
    makeRoom()
    local mesh = char.Mesh
    local className = str(system:GetClass():GetFName())
    local socket = FName(effect.socket or "None")
    local here, turn = { X = 0.0, Y = 0.0, Z = 0.0 }, { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }
    local ok, comp = pcall(function()
        if string.find(className, "Niagara", 1, true) then
            local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
            -- SpawnSystemAttached(System, AttachTo, Socket, Location, Rotation, SnapToTarget, bAutoDestroy, bAutoActivate, no pooling, bPreCullCheck)
            return lib:SpawnSystemAttached(system, mesh, socket, here, turn, 2, true, true, 0, false)
        end
        local statics = StaticFindObject("/Script/Engine.Default__GameplayStatics")
        -- SpawnEmitterAttached(System, AttachTo, Socket, Location, Rotation, Scale, SnapToTarget, bAutoDestroy, no pooling, bAutoActivate)
        return statics:SpawnEmitterAttached(system, mesh, socket, here, turn, { X = 1.0, Y = 1.0, Z = 1.0 }, 2, true, 0, true)
    end)
    local started = ok and valid(comp)
    if started and effect.scale then
        local s = effect.scale
        pcall(function() comp:SetRelativeScale3D({ X = s, Y = s, Z = s }) end)
    end
    local lasts = seconds or effect.seconds or CONFIG.effects.seconds[group] or 2.0
    if started then
        table.insert(active, { comp = comp, group = group, name = shortName(effect.path), ticks = ticksFor(lasts) })
    end
    log("effect " .. shortName(effect.path) .. " (" .. className .. (effect.socket and (", at " .. effect.socket) or "") .. ")" ..
        (started and string.format(" playing for %.1f s", lasts) or (" did not start" .. (ok and "" or (": " .. tostring(comp))))))
    return started and comp or nil
end

-- Plays a list of effects as `group`; the group's effects still playing end first, so they do not pile up.
local function playEffects(char, list, group)
    stopEffects(group)
    for _, effect in ipairs(list or {}) do
        local ok, err = pcall(playEffect, char, effect, group)
        if not ok then log("effect error " .. tostring(err)) end
    end
end

-- His voice bank in the language the game loaded (only one that is already loaded: no other language is loaded).
local function voiceBank()
    for _, language in ipairs(CONFIG.voiceBanks) do
        local bank = StaticFindObject("/Game/Sound/Voice/" .. language .. "/Character/Player/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth")
        if valid(bank) then return bank end
    end
    return nil
end

-- A sound cue of a bank, attached to his mesh, through the game's sound plugin (SQEX SEAD).
local function playSound(char, sound)
    local bank = nil
    if sound.voice then bank = voiceBank() else bank = loadObject(sound.bank) end
    if not valid(bank) then
        log("cue: no " .. (sound.voice and "voice bank is loaded" or (shortName(sound.bank) .. " did not load")) .. " for " .. sound.name)
        return
    end
    local sead = StaticFindObject("/Script/SQEXSEAD.Default__SQEXSEADStatics")
    if not valid(sead) then
        log("cue: SQEXSEADStatics not found")
        return
    end
    local cue = FName(sound.name)
    local okExists, exists = pcall(function() return sead:IsExistSoundInBank(bank, cue) end)
    if okExists and exists == false then
        log("cue: " .. sound.name .. " is not in " .. str(bank:GetFName()))
        return
    end
    local here, turn = { X = 0.0, Y = 0.0, Z = 0.0 }, { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }
    local ok, comp = pcall(function()
        -- SpawnSoundAttachedByName(Bank, AttachTo, Cue, SwitchValue, ZeroOneSlot, ZeroOneValue, ExternalID, Socket, Location,
        --   Rotation, SnapToTarget, bStopWhenAttachedToDestroyed, bVirtualizePlay, bUISound, Volume, Pitch, StartTime,
        --   Attenuation, Concurrency, bAutoDestroy, bRecycle, VibrationVolume, OutputPort Auto, VoiceEffect None)
        return sead:SpawnSoundAttachedByName(bank, char.Mesh, cue, 0.0, 0, 0.0, 0, FName("None"), here, turn, 2,
            true, false, false, 1.0, 1.0, 0.0, nil, nil, true, false, 1.0, 0, 0)
    end)
    log("cue: sound " .. sound.name .. " (" .. str(bank:GetFName()) .. ")" ..
        ((ok and valid(comp)) and " playing" or (" did not start" .. (ok and "" or (": " .. tostring(comp))))))
end

local function playCue(char, stage)
    local cue = CONFIG.cues[stage]
    if not cue then return end
    playEffects(char, cue.effects, "cue")
    for _, sound in ipairs(cue.sounds or {}) do playSound(char, sound) end
end

-- ---------------------------------------------------------------------------------------------------------------
-- The wing
-- ---------------------------------------------------------------------------------------------------------------
-- The wing's material slot on a mesh component: the first of CONFIG.wing.slots it has. Returns its index and name.
local function wingIndex(comp)
    if not valid(comp) then return nil end
    for _, slot in ipairs(CONFIG.wing.slots) do
        local ok, index = pcall(function() return comp:GetMaterialIndex(FName(slot)) end)
        if ok and type(index) == "number" and index >= 0 then return index, slot end
    end
    return nil
end

local function slotList()
    return table.concat(CONFIG.wing.slots, " / ")
end

local function lodCount(comp)
    local ok, count = pcall(function() return comp:GetNumLODs() end)
    if ok and type(count) == "number" and count > 0 then return count end
    return 8 -- the engine skips levels of detail the model does not have
end

local function showSection(comp, index, visible)
    for lod = 0, lodCount(comp) - 1 do comp:ShowMaterialSection(index, -1, visible, lod) end
end

local ownWingMaterial = {} -- mesh component -> the wing's own material (method "material")

-- The wing's fades: mesh component (full name) -> { comp, index, mid, from, to, start, seconds, hideAtEnd }.
local fades = {}
local fadeMids = {} -- mesh component (full name) -> { mid, index }: the copy of the wing's material that fades
local fadeProblem = nil -- why the wing cannot fade (it then comes and goes at once)

-- The copy of the wing's material that fades (made once per mesh component, kept in its slot: it looks like the wing's own).
local function fadeMid(comp, index)
    local key = comp:GetFullName()
    local made = fadeMids[key]
    if made and made.index == index and valid(made.mid) then return made.mid end
    -- CreateDynamicMaterialInstance(ElementIndex, LayerIndex, SourceMaterial (nil: the slot's own), OptionalName)
    local ok, mid = pcall(function() return comp:CreateDynamicMaterialInstance(index, 0, nil, FName("SephirothFormsWingFade")) end)
    if not ok or not valid(mid) then
        return nil, "no copy of the wing's material (" .. tostring(ok and "none made" or mid) .. ")"
    end
    fadeMids[key] = { mid = mid, index = index }
    return mid
end

local function setFadeValue(mid, value)
    mid:SetScalarParameterValue(FName(CONFIG.wing.fadeParameter), value)
end

-- Starts the wing fading in (visible) or out on one mesh component. Returns true, or false and why not.
local function startFade(comp, index, visible)
    if visible then pcall(showSection, comp, index, true) end
    local mid, why = fadeMid(comp, index)
    if not mid then return false, why end
    local key = comp:GetFullName()
    local running = fades[key]
    local from = visible and 0.0 or 1.0
    if running then -- (turning round halfway: from where it is)
        local t = math.min(1.0, (os.clock() - running.start) / running.seconds)
        from = running.from + (running.to - running.from) * t
    end
    local ok, err = pcall(function()
        setFadeValue(mid, from)
        if visible then showSection(comp, index, true) end
    end)
    if not ok then return false, tostring(err) end
    fades[key] = { comp = comp, index = index, mid = mid, from = from, to = visible and 1.0 or 0.0, start = os.clock(),
                   seconds = CONFIG.wing.fadeSeconds, hideAtEnd = not visible }
    return true
end

-- Every 50 ms: the wing's fades move on; one that is done hides the section (fading out).
local function updateFades()
    for key, fade in pairs(fades) do
        local t = math.min(1.0, (os.clock() - fade.start) / fade.seconds)
        local ok, err = pcall(function()
            if not valid(fade.comp) or not valid(fade.mid) then error("its mesh is gone") end
            setFadeValue(fade.mid, fade.from + (fade.to - fade.from) * t)
            if t >= 1.0 and fade.hideAtEnd then showSection(fade.comp, fade.index, false) end
        end)
        if not ok then
            log("wing fade stopped: " .. tostring(err))
            pcall(function() if fade.hideAtEnd and valid(fade.comp) then showSection(fade.comp, fade.index, false) end end)
            fades[key] = nil
        elseif t >= 1.0 then
            fades[key] = nil
        end
    end
end

local function fading(comp)
    return valid(comp) and fades[comp:GetFullName()] ~= nil
end

-- Shows or hides the wing on one mesh component (`fade`: it fades in or out). Returns true, or false and why not.
local function applyWing(comp, visible, fade)
    local index = wingIndex(comp)
    if not index then return false, "no " .. slotList() .. " material slot on " .. meshName(comp) end
    if CONFIG.wing.method ~= "material" then
        if fade and (CONFIG.wing.fadeSeconds or 0) > 0 and not fadeProblem then
            local ok, why = startFade(comp, index, visible)
            if ok then return true end
            fadeProblem = why
            log("wing: it cannot fade (" .. tostring(why) .. "); it comes and goes at once")
        end
        if valid(comp) then fades[comp:GetFullName()] = nil end
        local ok, err = pcall(function()
            local made = fadeMids[comp:GetFullName()]
            if made and made.index == index and valid(made.mid) then setFadeValue(made.mid, 1.0) end
            showSection(comp, index, visible)
        end)
        if ok then return true end
        return false, "ShowMaterialSection failed: " .. tostring(err)
    end
    local key = comp:GetFullName()
    local current = materialAt(comp, index)
    if valid(current) and not string.find(current:GetFullName(), "SephirothFormsWing", 1, true) then ownWingMaterial[key] = current end
    local own = ownWingMaterial[key]
    if not valid(own) then return false, "the wing's own material is not known" end
    local ok, err
    if visible then
        ok, err = pcall(function() comp:SetMaterial(index, own) end) -- (method "material" is not used; this game's SetMaterial may take a layer)
    else
        local black = loadObject(CONFIG.clearTexture)
        if not valid(black) then return false, CONFIG.clearTexture .. " did not load" end
        ok, err = pcall(function()
            local mid = comp:CreateDynamicMaterialInstance(index, 0, own, FName("SephirothFormsWingHidden"))
            mid:SetTextureParameterValue(FName("Coverage"), black)
        end)
    end
    if ok then return true end
    return false, tostring(err)
end

-- true / false, or nil when the component has no wing (a wing fading out counts as hidden already).
local function wingShown(comp)
    local index = wingIndex(comp)
    if not index then return nil end
    local fade = valid(comp) and fades[comp:GetFullName()]
    if fade then return not fade.hideAtEnd end
    if CONFIG.wing.method == "material" then
        local material = materialAt(comp, index)
        local ok, name = pcall(function() return material:GetFullName() end)
        if not material or not ok or not name then return nil end
        return not string.find(name, "SephirothFormsWingHidden", 1, true)
    end
    local ok, shown = pcall(function() return comp:IsMaterialSectionShown(index, 0) end)
    if ok and type(shown) == "boolean" then return shown end
    return nil
end

-- Shows or hides his wing. `feathers`: the feather burst plays when the wing comes out or goes; `fade` (else as
-- feathers): the wing fades in or out.
local function setWing(char, visible, feathers, fade)
    if not CONFIG.wing.enabled then return end
    if fade == nil then fade = feathers end
    local comp = char.Mesh
    local before = wingShown(comp)
    local changing = before ~= nil and before ~= visible
    local ok, why = applyWing(comp, visible, fade and changing)
    state.wingVisible = visible
    if not ok then
        if why ~= state.wingProblem then
            log("wing: " .. why .. (string.find(why, "material slot", 1, true) and " (turn SephirothTransformedBaseModel_P or KH2Sephiroth_P on: the wing is in those models)" or ""))
            state.wingProblem = why
        end
        return
    end
    state.wingProblem = nil
    local _, slot = wingIndex(comp)
    log("wing " .. (visible and "out" or "hidden") .. " (" .. CONFIG.wing.method .. ", slot " .. tostring(slot) ..
        ((fade and changing and fading(comp)) and string.format(", fading %.1f s", CONFIG.wing.fadeSeconds) or "") .. ")")
    if feathers and changing then
        playEffects(char, visible and CONFIG.wing.appear or CONFIG.wing.vanish, "wing")
    end
end

-- The game can reset the model (a new mesh, a costume): the wing goes back to how his form wants it.
local function keepWing(char)
    if not CONFIG.wing.enabled or state.wingVisible == nil or state.wingProblem then return end
    if fading(char.Mesh) then return end
    local shown = wingShown(char.Mesh)
    if shown == nil or shown == state.wingVisible then return end
    local ok = applyWing(char.Mesh, state.wingVisible, false)
    state.wingResets = (state.wingResets or 0) + 1
    if state.wingResets <= 5 then
        log("wing " .. (state.wingVisible and "out" or "hidden") .. " again (the game had reset it)" .. (ok and "" or " FAILED"))
    end
end

-- Other copies of his model (cutscenes, the reserve party): their wing stays hidden. They are looked for every few
-- seconds (FindAllOf of his class). (Not NotifyOnNewObject: UE4SS runs its callback on the Lua thread that registered
-- it, which for a call made from a game-thread call is a thread UE4SS has let go of by then.)
local othersClass = nil -- his class's short name
local othersAt = -100.0
local othersSeen = {} -- full names of copies already handled

local function watchOthers(char)
    if othersClass or not CONFIG.wing.enabled or not CONFIG.wing.hideOnOthers then return end
    local ok, short = pcall(function() return str(char:GetClass():GetFName()) end)
    if ok and short and short ~= "" then
        othersClass = short
        log("wing: other copies of his model (" .. short .. ") are looked for every 3 s")
    else
        othersClass = false
        log("wing: his class is unknown; other copies of his model are left alone")
    end
end

local function hideOnOthers(char)
    if not othersClass then return end
    local t = os.clock()
    if t - othersAt < 3.0 then return end
    othersAt = t
    local okAll, all = pcall(function() return FindAllOf(othersClass) end)
    if not okAll or type(all) ~= "table" then return end
    local mine = char and char:GetFullName() or ""
    for _, object in ipairs(all) do
        if valid(object) then
            local okName, name = pcall(function() return object:GetFullName() end)
            if okName and name and name ~= mine and not othersSeen[name] and not string.find(name, "Default__", 1, true) then
                local okMesh, comp = pcall(function() return object.Mesh end)
                if okMesh and wingIndex(comp) then
                    othersSeen[name] = true
                    local okHide = applyWing(comp, false)
                    log("wing hidden on another copy of his model: " .. name .. (okHide and "" or " (FAILED)"))
                end
            end
        end
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- Forms
-- ---------------------------------------------------------------------------------------------------------------
-- What the character's animation is doing, for the log.
local function animInfo(char)
    local text = "?"
    pcall(function()
        local inst = char.Mesh:GetAnimInstance()
        if not valid(inst) then
            text = "no anim instance"
            return
        end
        text = "anim instance " .. inst:GetFullName()
        local montage = inst:GetCurrentActiveMontage()
        text = text .. ", montage " .. (valid(montage) and montage:GetFullName() or "none")
    end)
    return text
end

local stageNames = { [0] = "normal", [1] = "winged", [2] = "flying", [3] = "KH2", [4] = "test: Battle02 pack only", [5] = "test: Battle00_Comp pack only" }

local function setPack(char, pack)
    local a = battleApi()
    local ok, err
    if pack then
        ok, err = pcall(function() a:SetPrimaryAnimPack(char, FName(pack), false) end)
    else
        ok, err = pcall(function() a:ResetPrimaryAnimPack(char) end)
    end
    log((pack and ("anim pack -> " .. pack) or "anim pack reset") .. (ok and "" or (" FAILED: " .. tostring(err))))
end

-- KH2's moves (Battle04) were made facing CONFIG.kh2Turn degrees off the game's: while he is in the KH2 form his model
-- turns that much (its own turn is kept and put back when he leaves the form).
local ownTurn = {} -- mesh component (full name) -> { Pitch, Yaw, Roll } it had before the KH2 turn
local turnResets = 0
local function meshRotation(comp)
    local ok, rot = pcall(function()
        local r = comp.RelativeRotation
        return { Pitch = r.Pitch, Yaw = r.Yaw, Roll = r.Roll }
    end)
    if ok and type(rot) == "table" and type(rot.Yaw) == "number" then return rot end
    return nil
end
local function angleGap(a, b)
    local d = (a - b) % 360.0
    if d > 180.0 then d = d - 360.0 end
    return math.abs(d)
end
-- on: the KH2 turn on his model (again, when the game reset it); off: his model's own turn back. Returns what it did.
local function kh2Turn(char, on)
    local comp = char.Mesh
    if not valid(comp) then return nil end
    local key = comp:GetFullName()
    local now = meshRotation(comp)
    if not now then return "his model's turn is unreadable" end
    local own = ownTurn[key]
    if on then
        if not own then
            own = now
            ownTurn[key] = own
        end
        local want = { Pitch = own.Pitch, Yaw = own.Yaw + (CONFIG.kh2Turn or 0.0), Roll = own.Roll }
        if angleGap(now.Yaw, want.Yaw) < 0.5 and angleGap(now.Pitch, want.Pitch) < 0.5 and angleGap(now.Roll, want.Roll) < 0.5 then return nil end
        comp:K2_SetRelativeRotation(want, false, {}, false)
        return string.format("his model turned %.0f degrees for the KH2 moves (yaw %.0f -> %.0f)", CONFIG.kh2Turn or 0.0, own.Yaw, want.Yaw)
    end
    if not own then return nil end
    ownTurn[key] = nil
    comp:K2_SetRelativeRotation(own, false, {}, false)
    return string.format("his model's own turn back (yaw %.0f)", own.Yaw)
end

local function setStage(char, stage, why, quiet)
    if not battleApi() then return end
    if dllForms() then
        -- (Create a Character System follows the pack: his form, wing and model come with it)
        local packs = { [0] = nil, [1] = CONFIG.wingedPack, [2] = CONFIG.flyingPack, [3] = CONFIG.kh2Pack, [4] = CONFIG.wingedPack, [5] = "Battle00_Comp" }
        setPack(char, packs[stage])
        state.stage = stage
        log("stage " .. stageNames[stage] .. " (" .. why .. "; the forms are Create a Character System's)")
        return
    end
    if quiet then stopEffects(nil) end -- (the battle ended: the effects of his forms end with it)
    -- The pack first, then the form is his (so nothing after can leave the menu thinking he is still in the old one),
    -- then the cue, his model's KH2 turn and, last, the wing.
    if stage == 0 then
        setPack(char, nil)
    elseif stage == 1 or stage == 2 then
        setPack(char, stage == 1 and CONFIG.wingedPack or CONFIG.flyingPack)
    elseif stage == 3 then
        setPack(char, CONFIG.kh2Pack)
    elseif stage == 4 then
        setPack(char, CONFIG.wingedPack)
    elseif stage == 5 then
        setPack(char, "Battle00_Comp")
    end
    state.stage = stage
    log("stage " .. stageNames[stage] .. " (" .. why .. "); " .. animInfo(char))
    if not quiet then
        local ok, err = pcall(playCue, char, stage)
        if not ok then log("cue error " .. tostring(err)) end
    end
    local okTurn, turned = pcall(kh2Turn, char, stage == 3)
    if okTurn and turned then log(turned) elseif not okTurn then log("KH2 turn error " .. tostring(turned)) end
    if stage == 0 then
        setWing(char, false, true)
    elseif stage == 1 or stage == 2 then
        setWing(char, true, true)
    elseif stage == 3 then
        setWing(char, true, false, true) -- his wing fades in (the KH2 cue's feather burst plays at its root)
    end
end

local function track(char, info)
    local name = char:GetFullName()
    if not state or state.name ~= name then
        stopEffects(nil) -- (effects on the character before)
        state = { name = name, stage = 0, ability = "None", wingVisible = nil, wingProblem = nil, wingResets = 0 }
        log("watching " .. name .. " (" .. info .. ")")
        if not dllForms() then
            setWing(char, false, false) -- his normal form: no wing, no feathers
            watchOthers(char)
        end
    end
end

-- How long the hold keys have been down (the longest of them), from the player controller's input.
local controller = nil
local function heldSeconds()
    if not valid(controller) then controller = FindFirstOf("PlayerController") end
    if not valid(controller) then return 0 end
    local longest = 0
    for _, key in ipairs(CONFIG.holdKeys) do
        local ok, seconds = pcall(function() return controller:GetInputKeyTimeDown({ KeyName = FName(key) }) end)
        if ok and type(seconds) == "number" and seconds > longest then longest = seconds end
    end
    return longest
end

-- In battle, and he is the character you control.
local function inCharge(char)
    local a = battleApi()
    if not a then return false end
    local okBattle, inBattle = pcall(function() return a:IsInBattle() end)
    if not (okBattle and inBattle) then return false end
    local okLeader, leader = pcall(function() return a:GetPartyLeader() end)
    if okLeader and valid(leader) and leader:GetFullName() ~= char:GetFullName() then return false end -- you control someone else
    return true
end

-- The form the left stick points at (CONFIG.menu.forms[].stick), or nil when it is in the middle.
local stickSeen = false
local stickForm = {}
for form, spot in pairs(CONFIG.menu.forms) do stickForm[spot.stick] = form end
local function stickPick()
    if not valid(controller) then return nil end
    local stick = CONFIG.menu.stick
    local okX, x = pcall(function() return controller:GetInputAnalogKeyState({ KeyName = FName(stick.x) }) end)
    local okY, y = pcall(function() return controller:GetInputAnalogKeyState({ KeyName = FName(stick.y) }) end)
    if not (okX and okY) or type(x) ~= "number" or type(y) ~= "number" then
        if not stickSeen then
            stickSeen = true
            log("menu: the left stick cannot be read (" .. tostring(okX and x or "") .. tostring(okY and "" or y) .. ")")
        end
        return nil
    end
    if math.abs(x) < stick.deadZone and math.abs(y) < stick.deadZone then return nil end
    if not stickSeen then
        stickSeen = true
        log(string.format("menu: left stick read (%.2f, %.2f)", x, y))
    end
    if math.abs(x) > math.abs(y) then return stickForm[x > 0 and "right" or "left"] end
    return stickForm[y > 0 and "up" or "down"]
end

-- Holding Triangle opens the menu (or, without it, moves him to the next form, CONFIG.nextForm), once per hold.
local holdUsed = false
local holdSeen = false
local menuOpen = nil -- { char, name, lit } while the menu is up

local function closeMenu(why)
    if not menuOpen then return end
    menuOpen = nil
    if menu then menu.close() end
    if why then log("menu closed (" .. why .. ")") end
end

local function checkHold()
    local seconds = heldSeconds()
    if menuOpen then
        local char = menuOpen.char
        if not valid(char) or not state or state.name ~= menuOpen.name then return closeMenu("he is gone") end
        if not inCharge(char) then return closeMenu("not in battle, or you control someone else") end
        if seconds > 0 then
            local pick = stickPick()
            if pick ~= nil and pick ~= menuOpen.lit then
                menuOpen.lit = pick
                menu.update(state.stage, pick)
            end
            return
        end
        -- Triangle let go: the lit form
        local lit = menuOpen.lit
        closeMenu()
        holdUsed, holdSeen = false, false
        if lit == nil or lit == state.stage then
            log("menu: " .. (lit == nil and "nothing chosen" or "he is in that form already") .. ", no switch")
            return
        end
        setStage(char, lit, "moveset menu")
        return
    end
    if seconds <= 0 then
        if holdSeen then log("Triangle released") end
        holdUsed, holdSeen = false, false
        return
    end
    if not holdSeen then
        holdSeen = true
        log("Triangle down")
    end
    local wanted = menu and CONFIG.menu.openSeconds or CONFIG.holdSeconds
    if holdUsed or seconds < wanted then return end
    holdUsed = true
    local char, info = sephiroth()
    if not char then return end
    track(char, info)
    if not inCharge(char) then return end
    if menu and menu.open(state.stage, nil) then
        menuOpen = { char = char, name = state.name, lit = nil }
        log(string.format("menu open (Triangle held %.2f s; he is %s)", seconds, stageNames[state.stage] or "?"))
        return
    end
    setStage(char, CONFIG.nextForm[state.stage] or 0, string.format("Triangle held %.1f s", seconds))
end

-- Every 50 ms (game thread): Triangle and the menu, then the wing's fades.
local function inputTick()
    if dllForms() then return end -- (the forms menu is Create a Character System's)
    local ok, err = pcall(checkHold)
    if not ok then
        log("menu error " .. tostring(err))
        pcall(closeMenu)
    end
    updateFades()
end

local lastWhy = nil
local function tick()
    updateEffects()
    local char, info = sephiroth()
    if not char then
        if info ~= lastWhy then
            log("waiting: " .. info)
            lastWhy = info
        end
        hideOnOthers(nil)
        grabs.tick(nil, "None")
        meteor.tick(nil)
        return
    end
    lastWhy = nil
    track(char, info)
    local own = not dllForms() -- (else his forms are Create a Character System's)
    if own then
        hideOnOthers(char)
        keepWing(char)
    end
    if own and state.stage == 3 then
        local okTurn, turned = pcall(kh2Turn, char, true)
        if okTurn and turned and turnResets < 5 then
            turnResets = turnResets + 1
            log(turned .. " (again: the game had reset it)")
        end
    end
    local a = battleApi()
    local ability = str(a:GetCurrentAbilityID(char))
    local okGrabs, errGrabs = pcall(grabs.tick, char, ability)
    if not okGrabs then log("grabs error " .. tostring(errGrabs)) end
    meteor.tick(char)
    if ability ~= state.ability then
        log("ability " .. state.ability .. " -> " .. ability .. "; " .. animInfo(char))
        if own and CONFIG.wingedAfter and state.ability == CONFIG.wingedAfter and state.stage ~= 1 and state.stage ~= 2 then setStage(char, 1, "after " .. CONFIG.wingedAfter) end
        if own and state.ability == CONFIG.flyingAfter and state.stage ~= 2 then setStage(char, 2, "after " .. CONFIG.flyingAfter) end
        state.ability = ability
    end
    if own and state.stage ~= 0 then
        local okBattle, inBattle = pcall(function() return a:IsInBattle() end)
        if okBattle and inBattle == false then
            closeMenu("the battle ended")
            setStage(char, 0, "the battle ended", true)
        end
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- What drives the mod. RebirthSkelCompat 3.5.3+ calls RebirthSkelCompatPump every frame on the game thread; until it
-- does (an older RebirthSkelCompat, or before the first map load), one UE4SS loop does, every 50 ms. (UE4SS 3.0.1's
-- ExecuteInGameThread makes a new Lua thread per call in a table it reads from other threads without a lock, and runs
-- the call in whatever thread calls ProcessEvent next: at frame rate that crashes the game in time.)
-- Key presses are queued and run there too.
-- ---------------------------------------------------------------------------------------------------------------
local keys = {} -- the key presses not run yet: functions

local function runKeys()
    if #keys == 0 then return end
    local list = keys
    keys = {}
    for _, fn in ipairs(list) do
        local ok, err = pcall(fn)
        if not ok then log("key error " .. tostring(err)) end
    end
end

local lastTickAt = -1.0
local function drive()
    local okInput, errInput = pcall(inputTick)
    if not okInput then log("input error " .. tostring(errInput)) end
    local t = os.clock()
    if t - lastTickAt >= TICK_SECONDS - 0.001 then
        lastTickAt = t
        local ok, err = pcall(tick)
        if not ok then log("error " .. tostring(err)) end
    end
    runKeys()
    if pumping then
        if grabs.pump then
            local ok, err = pcall(grabs.pump)
            if not ok then log("grabs error " .. tostring(err)) end
        end
        if meteor.pump then
            local ok, err = pcall(meteor.pump)
            if not ok then log("meteor error " .. tostring(err)) end
        end
    end
end

RebirthSkelCompatPump = function()
    if not pumping then
        pumping = true
        log("RebirthSkelCompat's frame pump drives the mod now, on the game thread (the UE4SS loops stop)")
    end
    drive()
end

local queued = false   -- (one at a time: a slow frame does not pile them up)
local offThread = 0
LoopAsync(math.floor(INPUT_SECONDS * 1000), function()
    if pumping then return true end -- (the frame pump runs the mod now: this loop ends)
    if not queued then
        queued = true
        ExecuteInGameThread(function()
            queued = false
            if pumping then return end
            if not onGameThread() then
                offThread = offThread + 1
                if offThread <= 3 then log("UE4SS ran a game-thread call on another thread: skipped (" .. offThread .. ")") end
                return
            end
            drive()
        end)
    end
    return false
end)

local function onKey(stage, label)
    table.insert(keys, function()
        local char, info = sephiroth()
        if not char then
            log(label .. ": " .. info)
            return
        end
        track(char, info)
        if stage == nil then
            local a = battleApi()
            local comp = char.Mesh
            local shown = wingShown(comp)
            local playing, fading = 0, 0
            for _, entry in ipairs(active) do
                if entry.fade then fading = fading + 1 else playing = playing + 1 end
            end
            log(string.format("status: effects %d playing, %d fading; driven by %s", playing, fading, pumping and "RebirthSkelCompat's frame pump" or "a UE4SS loop"))
            log("status: " .. state.name .. ", row " .. info .. ", stage " .. stageNames[state.stage] .. ", ability " ..
                str(a:GetCurrentAbilityID(char)) .. ", in battle " .. tostring(a:IsInBattle()) .. string.format(", Triangle held %.1f s", heldSeconds()) ..
                ", mesh " .. meshName(comp) .. ", wing " .. (shown == nil and ("none (no " .. slotList() .. " slot)") or (shown and "out" or "hidden")) ..
                string.format(", KH2 turn %.0f", CONFIG.kh2Turn or 0.0) .. "; " .. animInfo(char))
        else
            setStage(char, stage, label)
        end
    end)
end

-- F4: the next feather effect of CONFIG.featherPreview on him.
local previewAt = 0
local function previewFeathers()
    table.insert(keys, function()
        local char, info = sephiroth()
        if not char then
            log("F4: " .. info)
            return
        end
        track(char, info)
        local list = CONFIG.featherPreview
        if #list == 0 then return end
        previewAt = previewAt % #list + 1
        log(string.format("F4 preview %d of %d: %s", previewAt, #list, shortName(list[previewAt].path)))
        stopEffects("preview") -- (the one before)
        playEffect(char, list[previewAt], "preview")
    end)
end

-- F2: the KH2 turn another 90 degrees (applied at once in the KH2 form).
RegisterKeyBind(Key.F2, function()
    table.insert(keys, function()
        CONFIG.kh2Turn = ((CONFIG.kh2Turn or 0.0) + 90.0) % 360.0
        local char = sephiroth()
        local done = nil
        if char and state and state.stage == 3 then done = kh2Turn(char, true) end
        log(string.format("F2: KH2 turn now %.0f degrees", CONFIG.kh2Turn) .. (done and ("; " .. done) or " (it shows in the KH2 form)"))
    end)
end)
RegisterKeyBind(Key.F4, previewFeathers)
RegisterKeyBind(Key.F5, function() onKey(nil, "F5") end)
RegisterKeyBind(Key.F6, function() onKey(1, "F6") end)
RegisterKeyBind(Key.F7, function() onKey(2, "F7") end)
RegisterKeyBind(Key.F8, function() onKey(0, "F8") end)
RegisterKeyBind(Key.F9, function() onKey(3, "F9") end)
RegisterKeyBind(Key.F10, function() onKey(4, "F10") end)
RegisterKeyBind(Key.F11, function() onKey(5, "F11") end)

if dllForms() then
    log("SephirothForms: Create a Character System changes his forms (hold Triangle in battle: its forms menu); this mod keeps Grip of Fate, Skewer, the Meteor cinematic and F5 status (F6 to F9 switch his pack: his form follows)")
end
log(string.format("SephirothForms ready (%s; every switch plays a cue; the wing %s; KH2 turn %.0f degrees (F2: another 90); F4 feather preview, F5 status, F6 winged, F7 flying, F8 normal, F9 KH2; tests: F10 Battle02 pack only, F11 Battle00_Comp pack only)",
    menu and string.format("hold Triangle %.2f s in battle: the moveset menu, left stick to choose, let go to switch", CONFIG.menu.openSeconds)
        or string.format("hold Triangle %.1f s in battle: normal -> winged -> flying -> KH2 -> normal", CONFIG.holdSeconds),
    CONFIG.wing.enabled and ("comes out in the winged, flying and KH2 forms (" .. CONFIG.wing.method .. ", slot " .. slotList() ..
        ((CONFIG.wing.fadeSeconds or 0) > 0 and string.format(", fading %.1f s", CONFIG.wing.fadeSeconds) or "") .. ")") or "is left alone",
    CONFIG.kh2Turn or 0.0))
