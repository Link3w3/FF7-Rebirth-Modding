-- SephirothForms: your playable Sephiroth (he plays in Cloud's slot) changes form in battle.
--   Hold Triangle (the controller's top face button) for half a second in battle: each hold moves him to the next form,
--   normal -> winged (animation pack Battle02) -> flying (Battle03) -> KH2 (Battle04: his Kingdom Hearts II moves) ->
--   normal. A tap is still his Triangle attack.
--   Every switch plays a cue on him: an aura and a sound (CONFIG.cues). After his level 2 limit (Heartless Angel, on
--   Cloud's PC0000_Limit002) he switches to flying by himself.
--   His wing is hidden in his normal form and comes out in the winged, flying and KH2 forms, in a burst of black feathers
--   (CONFIG.wing). The wing is part of his model from SephirothTransformedBaseModel_P (the transformed Sephiroth's model
--   in his model's place); without that pak there is no wing to show.
--   Every effect the mod plays lasts a moment, then fades and is removed (CONFIG.effects). A new switch first ends the
--   effects of the switch before it, so they never pile up on him.
--   The packs come from Create a Character System (compat\SephirothForms.json). Everything goes back when the battle ends.
--   Grip of Fate and Skewer catch every enemy, bosses too (ForceGrabs.lua): Grip of Fate's feeler binds the enemy it hits,
--   Skewer lifts the enemy on his sword and throws it off flying. Meteor is a cinematic (MeteorStrike.lua).
-- Keyboard: F4 next feather effect (preview), F5 status, F6 winged now, F7 flying now, F8 back to normal, F9 KH2 now;
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
    -- Holding Triangle this long (seconds) while he is the character you control switches his form.
    holdKeys = { "Gamepad_FaceButton_Top" },
    holdSeconds = 0.5,
    -- The form each hold moves to, from the one he is in.
    nextForm = { [0] = 1, [1] = 2, [2] = 3, [3] = 0 },
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
    -- His wing: the material slot of his model it is drawn with. method "section" has the engine hide that part of his
    -- model (ShowMaterialSection, every level of detail, its shadow too: nothing about the material changes); "material"
    -- puts a see-through copy of the wing's material in the slot instead (its Coverage mask black, clearTexture).
    wing = {
        enabled = true,
        slot = "PC0010_10_Wing",
        method = "section",
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

local TICK_SECONDS = 0.2 -- the main loop runs every 200 ms

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
        local okInit, errInit = pcall(module.init, { log = log, valid = valid, str = str, battleApi = battleApi })
        if okInit then return module end
        log(name .. " didn't start: " .. tostring(errInit))
    else
        log(name .. ".lua not loaded: " .. tostring(module))
    end
    return { tick = function() end }
end
local grabs = loadModule("ForceGrabs")
local meteor = loadModule("MeteorStrike")

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
    local bank = sound.voice and voiceBank() or loadObject(sound.bank)
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
local function wingIndex(comp)
    if not valid(comp) then return nil end
    local ok, index = pcall(function() return comp:GetMaterialIndex(FName(CONFIG.wing.slot)) end)
    if ok and type(index) == "number" and index >= 0 then return index end
    return nil
end

local function lodCount(comp)
    local ok, count = pcall(function() return comp:GetNumLODs() end)
    if ok and type(count) == "number" and count > 0 then return count end
    return 8 -- the engine skips levels of detail the model does not have
end

local ownWingMaterial = {} -- mesh component -> the wing's own material (method "material")

-- Shows or hides the wing on one mesh component. Returns true, or false and why not.
local function applyWing(comp, visible)
    local index = wingIndex(comp)
    if not index then return false, "no " .. CONFIG.wing.slot .. " material slot on " .. meshName(comp) end
    if CONFIG.wing.method ~= "material" then
        local ok, err = pcall(function()
            for lod = 0, lodCount(comp) - 1 do comp:ShowMaterialSection(index, -1, visible, lod) end
        end)
        if ok then return true end
        return false, "ShowMaterialSection failed: " .. tostring(err)
    end
    local key = comp:GetFullName()
    local current = comp:GetMaterial(index)
    if valid(current) and not string.find(current:GetFullName(), "SephirothFormsWing", 1, true) then ownWingMaterial[key] = current end
    local own = ownWingMaterial[key]
    if not valid(own) then return false, "the wing's own material is not known" end
    local ok, err
    if visible then
        ok, err = pcall(function() comp:SetMaterial(index, own) end)
    else
        local black = loadObject(CONFIG.clearTexture)
        if not valid(black) then return false, CONFIG.clearTexture .. " did not load" end
        ok, err = pcall(function()
            local mid = comp:CreateDynamicMaterialInstance(index, own, FName("SephirothFormsWingHidden"))
            mid:SetTextureParameterValue(FName("Coverage"), black)
        end)
    end
    if ok then return true end
    return false, tostring(err)
end

-- true / false, or nil when the component has no wing.
local function wingShown(comp)
    local index = wingIndex(comp)
    if not index then return nil end
    if CONFIG.wing.method == "material" then
        local ok, name = pcall(function() return comp:GetMaterial(index):GetFullName() end)
        if not ok or not name then return nil end
        return not string.find(name, "SephirothFormsWingHidden", 1, true)
    end
    local ok, shown = pcall(function() return comp:IsMaterialSectionShown(index, 0) end)
    if ok and type(shown) == "boolean" then return shown end
    return nil
end

-- Shows or hides his wing. `feathers`: the feather burst plays when the wing comes out or goes.
local function setWing(char, visible, feathers)
    if not CONFIG.wing.enabled then return end
    local comp = char.Mesh
    local before = wingShown(comp)
    local ok, why = applyWing(comp, visible)
    state.wingVisible = visible
    if not ok then
        if why ~= state.wingProblem then
            log("wing: " .. why .. (string.find(why, "material slot", 1, true) and " (turn SephirothTransformedBaseModel_P on: the wing is in that model)" or ""))
            state.wingProblem = why
        end
        return
    end
    state.wingProblem = nil
    log("wing " .. (visible and "out" or "hidden") .. " (" .. CONFIG.wing.method .. ")")
    if feathers and before ~= nil and before ~= visible then
        playEffects(char, visible and CONFIG.wing.appear or CONFIG.wing.vanish, "wing")
    end
end

-- The game can reset the model (a new mesh, a costume): the wing goes back to how his form wants it.
local function keepWing(char)
    if not CONFIG.wing.enabled or state.wingVisible == nil or state.wingProblem then return end
    local shown = wingShown(char.Mesh)
    if shown == nil or shown == state.wingVisible then return end
    local ok = applyWing(char.Mesh, state.wingVisible)
    state.wingResets = (state.wingResets or 0) + 1
    if state.wingResets <= 5 then
        log("wing " .. (state.wingVisible and "out" or "hidden") .. " again (the game had reset it)" .. (ok and "" or " FAILED"))
    end
end

-- Other copies of his model (cutscenes, the reserve party): their wing stays hidden.
local othersHooked = false
local others = {} -- { object, tries }

local function watchOthers(char)
    if othersHooked or not CONFIG.wing.enabled or not CONFIG.wing.hideOnOthers then return end
    othersHooked = true
    local okClass, classFull = pcall(function() return char:GetClass():GetFullName() end)
    local classPath = okClass and classFull and classFull:match("^%S+%s+(.+)$")
    local okShort, classShort = pcall(function() return str(char:GetClass():GetFName()) end)
    if not classPath then
        log("wing: his class is unknown; other copies of his model are left alone")
        return
    end
    local okHook, err = pcall(function()
        NotifyOnNewObject(classPath, function(object) table.insert(others, { object = object, tries = 0 }) end)
    end)
    log("wing: " .. (okHook and "watching" or ("NOT watching (" .. tostring(err) .. ")")) .. " new copies of " .. classPath)
    if okShort and classShort then
        local okAll, all = pcall(function() return FindAllOf(classShort) end)
        if okAll and type(all) == "table" then
            for _, object in ipairs(all) do table.insert(others, { object = object, tries = 0 }) end
        end
    end
end

local function hideOnOthers(char)
    if #others == 0 then return end
    local mine = char and char:GetFullName() or ""
    local keep = {}
    for _, entry in ipairs(others) do
        local object = entry.object
        if valid(object) then
            local okName, name = pcall(function() return object:GetFullName() end)
            if okName and name and name ~= mine and not string.find(name, "Default__", 1, true) then
                local okMesh, comp = pcall(function() return object.Mesh end)
                if okMesh and wingIndex(comp) then
                    local ok = applyWing(comp, false)
                    log("wing hidden on another copy of his model: " .. name .. (ok and "" or " (FAILED)"))
                else
                    entry.tries = entry.tries + 1
                    if entry.tries < 25 then table.insert(keep, entry) end -- its model may come a moment later (5 s)
                end
            end
        end
    end
    others = keep
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

local function setStage(char, stage, why, quiet)
    if not battleApi() then return end
    if quiet then stopEffects(nil) end -- (the battle ended: the effects of his forms end with it)
    if stage == 0 then
        setPack(char, nil)
        setWing(char, false, true)
    elseif stage == 1 or stage == 2 then
        setPack(char, stage == 1 and CONFIG.wingedPack or CONFIG.flyingPack)
        setWing(char, true, true)
    elseif stage == 3 then
        setPack(char, CONFIG.kh2Pack)
        setWing(char, true, false) -- his wing out (the KH2 cue's feather burst plays at its root)
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
end

local function track(char, info)
    local name = char:GetFullName()
    if not state or state.name ~= name then
        stopEffects(nil) -- (effects on the character before)
        state = { name = name, stage = 0, ability = "None", wingVisible = nil, wingProblem = nil, wingResets = 0 }
        log("watching " .. name .. " (" .. info .. ")")
        setWing(char, false, false) -- his normal form: no wing, no feathers
        watchOthers(char)
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

-- Holding Triangle moves him to the next form (CONFIG.nextForm), once per hold.
local holdUsed = false
local holdSeen = false
local function checkHold(char)
    local seconds = heldSeconds()
    if seconds <= 0 then
        if holdSeen then log("Triangle released") end
        holdUsed = false
        holdSeen = false
        return
    end
    if not holdSeen then
        holdSeen = true
        log("Triangle down")
    end
    if holdUsed or seconds < CONFIG.holdSeconds then return end
    holdUsed = true
    local a = battleApi()
    local okBattle, inBattle = pcall(function() return a:IsInBattle() end)
    if not (okBattle and inBattle) then return end
    local okLeader, leader = pcall(function() return a:GetPartyLeader() end)
    if okLeader and valid(leader) and leader:GetFullName() ~= char:GetFullName() then return end -- you control someone else
    setStage(char, CONFIG.nextForm[state.stage] or 0, string.format("Triangle held %.1f s", seconds))
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
    hideOnOthers(char)
    keepWing(char)
    local a = battleApi()
    local ability = str(a:GetCurrentAbilityID(char))
    local okGrabs, errGrabs = pcall(grabs.tick, char, ability)
    if not okGrabs then log("grabs error " .. tostring(errGrabs)) end
    meteor.tick(char)
    if ability ~= state.ability then
        log("ability " .. state.ability .. " -> " .. ability .. "; " .. animInfo(char))
        if CONFIG.wingedAfter and state.ability == CONFIG.wingedAfter and state.stage ~= 1 and state.stage ~= 2 then setStage(char, 1, "after " .. CONFIG.wingedAfter) end
        if state.ability == CONFIG.flyingAfter and state.stage ~= 2 then setStage(char, 2, "after " .. CONFIG.flyingAfter) end
        state.ability = ability
    end
    checkHold(char)
    if state.stage ~= 0 then
        local okBattle, inBattle = pcall(function() return a:IsInBattle() end)
        if okBattle and inBattle == false then setStage(char, 0, "the battle ended", true) end
    end
end

LoopAsync(math.floor(TICK_SECONDS * 1000), function()
    ExecuteInGameThread(function()
        local ok, err = pcall(tick)
        if not ok then log("error " .. tostring(err)) end
    end)
    return false
end)

local function onKey(stage, label)
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
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
                log(string.format("status: effects %d playing, %d fading", playing, fading))
                log("status: " .. state.name .. ", row " .. info .. ", stage " .. stageNames[state.stage] .. ", ability " ..
                    str(a:GetCurrentAbilityID(char)) .. ", in battle " .. tostring(a:IsInBattle()) .. string.format(", Triangle held %.1f s", heldSeconds()) ..
                    ", mesh " .. meshName(comp) .. ", wing " .. (shown == nil and ("none (no " .. CONFIG.wing.slot .. " slot)") or (shown and "out" or "hidden")) ..
                    "; " .. animInfo(char))
            else
                setStage(char, stage, label)
            end
        end)
        if not ok then log(label .. " error " .. tostring(err)) end
    end)
end

-- F4: the next feather effect of CONFIG.featherPreview on him.
local previewAt = 0
local function previewFeathers()
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
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
        if not ok then log("F4 error " .. tostring(err)) end
    end)
end

RegisterKeyBind(Key.F4, previewFeathers)
RegisterKeyBind(Key.F5, function() onKey(nil, "F5") end)
RegisterKeyBind(Key.F6, function() onKey(1, "F6") end)
RegisterKeyBind(Key.F7, function() onKey(2, "F7") end)
RegisterKeyBind(Key.F8, function() onKey(0, "F8") end)
RegisterKeyBind(Key.F9, function() onKey(3, "F9") end)
RegisterKeyBind(Key.F10, function() onKey(4, "F10") end)
RegisterKeyBind(Key.F11, function() onKey(5, "F11") end)

log(string.format("SephirothForms ready (hold Triangle %.1f s in battle: normal -> winged -> flying -> KH2 -> normal, with a cue; the wing %s; F4 feather preview, F5 status, F6 winged, F7 flying, F8 normal, F9 KH2; tests: F10 Battle02 pack only, F11 Battle00_Comp pack only)",
    CONFIG.holdSeconds, CONFIG.wing.enabled and ("comes out in the winged, flying and KH2 forms (" .. CONFIG.wing.method .. ")") or "is left alone"))
