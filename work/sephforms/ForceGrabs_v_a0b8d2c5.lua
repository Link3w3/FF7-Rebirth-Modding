-- ForceGrabs: your Sephiroth's grabs catch every enemy, bosses too.
--   Grip of Fate (PC0010_T_BindFeeler): the feeler he throws binds the enemy it hits (special status Sephiroth_BindFeeler:
--     the feeler EN9000_20_Feeler_BlackEnd2 wraps around it and holds it) for CONFIG.bindSeconds, then lets it go.
--   Skewer (PC0010_T_WarpStab): he vanishes and reappears in front of his target (CONFIG.teleport), runs it through, lifts
--     it on his sword (sync action PC0010_10_WarpStab: his B_AtkStab02) and throws it off with a blow that sends it flying.
-- How: an enemy reacts to a hit only when the hit's cut (50 for these) beats its guard ("keep": 60 to 100 for most monsters
-- and bosses, more while they attack), so most shrug both off. While he does one of them, his target's keep is 0
-- (EndBattleAPI SetOverrideKeep), so the game's own bind, lift and blow happen. When the game still doesn't bind it, the
-- mod binds it (AddSpecialStatusChangeID). An enemy the game won't lift (big monsters, bosses) can't be put on his sword
-- (a lift forced on it crashes the game), so he does the lift motion by himself and the throw-off hit lands on it; when the
-- throw-off leaves an enemy standing, it is launched (LaunchCharacter). Its keep goes back (ResetOverrideKeep) after.
-- The feeler is a character the binder must have loaded: his rows list it in FullyPlayableSephirothDataAssets_P, as the boss
-- Sephiroth's row does. Skewer's hits (PC0010_T_Stab_01, PC0010_T_StabDetach_01) are in it too, with his sword's reach.
-- It looks every CONFIG.stepSeconds while he is in the party. UE4SS.log lines start with "grabs:".
-- Note: an error inside a UE4SS call is not caught by pcall here (it ends the whole call), so every object is checked
-- before it is used and every game function gets the parameter types it takes (EndBattleAPI's signatures in the exe).
local M = {}

local CONFIG = {
    enabled = true,
    stepSeconds = 0.033,    -- how often it looks (only while he is in the party)
    bindSeconds = 5.0,      -- how long Grip of Fate holds an enemy
    keepAfter = 1.0,        -- the target's keep goes back this long after the move (or the lift) is over
    hitWindow = 0.3,        -- the target's HP dropping this soon after the move's hit was out is that hit
    forceDelay = 0.1,       -- after Grip of Fate's hit, how long the game gets to bind the enemy itself
    refusedAfter = 0.35,    -- a forced bind that hasn't taken after this long was refused
    liftWait = 0.15,        -- after Skewer's stab, how long the game gets to lift the enemy
    throwOffAfter = 1.0,    -- when the game won't lift it: the throw-off hit comes this long after the stab
    teleport = {
        at = 0.3,           -- Skewer: he reappears in front of his target this long after the move starts ...
        minDistance = 300.0,-- ... when he is farther from it than this (cm, from its edge) ...
        gap = 120.0,        -- ... this far from its edge (cm)
    },
    launch = {
        wait = 0.25,        -- after the throw-off: how long before checking whether it flies
        minSpeed = 300.0,   -- an enemy already moving this fast (cm/s) is flying already
        push = 1100.0,      -- the launch: away from him (cm/s) ...
        up = 700.0,         -- ... and up (cm/s)
    },
    moves = {
        PC0010_T_BindFeeler = {
            kind = "bind", label = "Grip of Fate", seconds = 4.0, status = "Sephiroth_BindFeeler",
            sources = { "PC0010_10_BindFeeler_01" },                   -- the feeler bullet
        },
        PC0010_T_WarpStab = {
            kind = "skewer", label = "Skewer", seconds = 3.0,
            -- his sword's stab (the player's, then the boss's own) and the feeler's stab
            sources = { "PC0010_T_Stab_01", "PC0010_10_Stab_01", "PC0010_10_Stab_Feeler_01" },
            -- the throw-off hit, when the game won't lift the enemy (the player's has his sword's reach)
            throwOff = { PC0010_T_Stab_01 = "PC0010_T_StabDetach_01", PC0010_10_Stab_01 = "PC0010_10_StabDetach_01",
                         PC0010_10_Stab_Feeler_01 = "PC0010_10_StabDetachFeeler_01" },
            -- his lift, played on him when the game won't lift the enemy (EndBattleAPI PlayPartMotion: from the hips down,
            -- extra action layer 0 = HighPriority)
            liftMotion = "B_AtkStab02", liftBone = "C_Hip_a", liftLayer = 0,
        },
    },
}

local H = nil           -- from main.lua: log, valid, str, battleApi
local char = nil        -- your Sephiroth (main.lua's tick)
local ops = {}          -- the grabs in progress
local keeps = {}        -- full name -> { object, untilTime }: targets whose keep is 0
local current = "None"  -- his ability as this loop last saw it
local characterClass = nil

local function now() return os.clock() end
local function log(text) H.log("grabs: " .. text) end
local function valid(object) return H.valid(object) end

local names = {}
local function N(text)
    local n = names[text]
    if n == nil then
        n = FName(text)
        names[text] = n
    end
    return n
end

local function nameOf(object)
    if not valid(object) then return "nil" end
    return object:GetFName():ToString()
end

local function keyOf(object)
    return object:GetFullName()
end

local function api()
    return H.battleApi()
end

local function where(object)
    local v = object:K2_GetActorLocation()
    return { X = v.X, Y = v.Y, Z = v.Z }
end

-- radius and half height of a character's capsule (cm)
local function capsule(object)
    local comp = object.CapsuleComponent
    if not valid(comp) then return 50.0, 90.0 end
    return comp:GetScaledCapsuleRadius(), comp:GetScaledCapsuleHalfHeight()
end

-- Skewer's vanish: he reappears CONFIG.teleport.gap in front of the target's edge, on its ground, facing it
local function teleport(op)
    local me, it = where(char), where(op.target)
    local dx, dy = it.X - me.X, it.Y - me.Y
    local len = math.sqrt(dx * dx + dy * dy)
    local myRadius, myHalf = capsule(char)
    local itRadius, itHalf = capsule(op.target)
    local edge = len - itRadius - myRadius
    if edge <= CONFIG.teleport.minDistance or len < 1.0 then
        log(string.format("%s: %s is close (%.0f cm), no vanish", op.def.label, nameOf(op.target), edge))
        return
    end
    dx, dy = dx / len, dy / len
    local back = itRadius + myRadius + CONFIG.teleport.gap
    local dest = { X = it.X - dx * back, Y = it.Y - dy * back, Z = it.Z - itHalf + myHalf }
    local yaw = math.deg(math.atan(dy, dx))
    local ok = char:K2_TeleportTo(dest, { Pitch = 0.0, Yaw = yaw, Roll = 0.0 })
    log(string.format("%s: vanishes and reappears in front of %s (%.0f cm away)%s", op.def.label, nameOf(op.target), edge,
        ok and "" or " - the spot was blocked"))
end

-- ---------------------------------------------------------------------------------------------------------------
-- the target's keep
-- ---------------------------------------------------------------------------------------------------------------
local function lowerKeep(a, target, why, seconds)
    local key = keyOf(target)
    local t = now()
    local entry = keeps[key]
    if entry then
        if entry.untilTime < t + seconds then entry.untilTime = t + seconds end
        return
    end
    local before = a:GetKeep(target)
    a:SetOverrideKeep(target, 0)
    keeps[key] = { object = target, untilTime = t + seconds }
    log(string.format("%s: keep of %s %s -> %s", why, nameOf(target), tostring(before), tostring(a:GetKeep(target))))
end

local function holdKeep(target, seconds)
    local entry = keeps[keyOf(target)]
    if entry and entry.untilTime < now() + seconds then entry.untilTime = now() + seconds end
end

local function restoreKeeps(a, all)
    local t = now()
    for key, entry in pairs(keeps) do
        if not valid(entry.object) then
            keeps[key] = nil
        elseif all or entry.untilTime <= t then
            a:ResetOverrideKeep(entry.object)
            log(string.format("keep of %s back (%s)", nameOf(entry.object), tostring(a:GetKeep(entry.object))))
            keeps[key] = nil
        end
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- one use of a move
-- ---------------------------------------------------------------------------------------------------------------
local function liveSource(a, sources)
    for _, id in ipairs(sources) do
        if a:HasDamageSource(char, N(id)) then return id end
    end
    return nil
end

local function startOp(a, ability, def)
    local op = { ability = ability, def = def, start = now() }
    table.insert(ops, op)
    return op
end

-- the target the move goes to (its lock-on target), once there is one
local function aim(a, op)
    if op.target then return end
    local target = a:GetTargetCharacter(char)
    if not valid(target) or keyOf(target) == keyOf(char) then return end
    op.target = target
    op.hp = a:GetCharaHP(target)
    lowerKeep(a, target, op.def.label, op.def.seconds)
    log(string.format("%s on %s (HP %s, can sync %s, in sync %s)", op.def.label, nameOf(target), tostring(op.hp),
        tostring(a:CanSyncAction(target)), tostring(a:IsInSyncAction(target))))
end

-- the move's hit: its damage source was out and the target's HP dropped
local function watchHit(a, op, t)
    local live = liveSource(a, op.def.sources)
    if live then
        op.sourceAt = t
        op.source = live
        if not op.sourceSeen then
            op.sourceSeen = t
            log(string.format("%s: %s out", op.def.label, live))
        end
    end
    local hp = a:GetCharaHP(op.target)
    if op.hp and hp < op.hp and op.sourceAt and t <= op.sourceAt + CONFIG.hitWindow and not op.hit then
        op.hit = t
        log(string.format("%s hit %s (%s, HP %d -> %d)", op.def.label, nameOf(op.target), tostring(op.source), op.hp, hp))
    end
    op.hp = hp
end

local function launch(a, op)
    local target = op.target
    local flying = a:IsLaunchActionPlaying(target) or a:IsLaunchActionInAir(target)
    local v = target:GetVelocity()
    local speed = math.sqrt(v.X * v.X + v.Y * v.Y)
    if flying or speed >= CONFIG.launch.minSpeed then
        log(string.format("%s: %s flies (%s, %.0f cm/s)", op.def.label, nameOf(target), flying and "the game's launch" or "moving", speed))
        return
    end
    if not (characterClass and target:IsA(characterClass)) then
        log(string.format("%s: %s can't be launched (not a Character)", op.def.label, nameOf(target)))
        return
    end
    local from, to = where(char), where(target)
    local dx, dy = to.X - from.X, to.Y - from.Y
    local len = math.sqrt(dx * dx + dy * dy)
    if len < 1.0 then
        local f = char:GetActorForwardVector()
        dx, dy = f.X, f.Y
        len = math.sqrt(dx * dx + dy * dy)
    end
    if len < 0.001 then dx, dy, len = 1.0, 0.0, 1.0 end
    dx, dy = dx / len, dy / len
    target:LaunchCharacter({ X = dx * CONFIG.launch.push, Y = dy * CONFIG.launch.push, Z = CONFIG.launch.up }, true, true)
    log(string.format("%s: launched %s (it stood still after the throw-off)", op.def.label, nameOf(target)))
end

-- Grip of Fate: bind the target it hits, let go after CONFIG.bindSeconds
local function stepBind(a, op, t)
    local def = op.def
    if not op.bound then watchHit(a, op, t) end
    local bound = a:HasSpecialStatusChangeID(op.target, N(def.status))
    if bound and not op.bound then
        op.bound = t
        log(string.format("%s binds %s (%s)", def.label, nameOf(op.target), op.forced and "forced" or "the game"))
    end
    if op.hit and not op.bound and not op.forced and t >= op.hit + CONFIG.forceDelay then
        op.forced = t
        a:AddSpecialStatusChangeID(op.target, char, N(def.status))
        log(string.format("%s: the game didn't bind %s; binding it", def.label, nameOf(op.target)))
    end
    if op.forced and not op.bound and not op.refused and t >= op.forced + CONFIG.refusedAfter then
        op.refused = t
        log(string.format("%s: %s refused the bind", def.label, nameOf(op.target)))
    end
    if op.bound then
        holdKeep(op.target, CONFIG.keepAfter)
        if not bound and not op.release then
            op.released = t
            log(string.format("%s: the bind on %s ended by itself", def.label, nameOf(op.target)))
            return true
        end
        if not op.release and t >= op.bound + CONFIG.bindSeconds then
            op.release = t
            if bound then a:RemoveSpecialStatusChangeIDRequest(op.target, N(def.status)) end
        end
        if op.release and not op.released then
            if not bound then
                op.released = t
                log(string.format("%s lets %s go", def.label, nameOf(op.target)))
            elseif t >= op.release + 1.5 then
                op.released = t
                a:RemoveSpecialStatusChangeID(op.target, N(def.status))
                log(string.format("%s lets %s go (removed)", def.label, nameOf(op.target)))
            end
        end
        return op.released ~= nil
    end
    -- over: no hit while the move and its bullet were out, or the bind was refused
    if op.refused then return true end
    local busy = current == op.ability or (op.sourceAt and t <= op.sourceAt + CONFIG.hitWindow)
    return not busy and not op.hit and t > op.start + 1.0
end

-- Skewer: the game lifts the enemy it stabs (sync action PC0010_10_WarpStab) when that enemy can be lifted. An enemy the
-- game won't lift (big monsters, bosses) still gets the rest of the move: he does the lift (B_AtkStab02, played on him)
-- and the throw-off hit lands on it. (Never CreateSyncAction on such an enemy: the game crashes in the lift's next tick.)
-- Then the throw-off sends it flying.
local function stepSkewer(a, op, t)
    local def = op.def
    if CONFIG.teleport and not op.teleported and t >= op.start + CONFIG.teleport.at then
        op.teleported = t
        if current == op.ability then teleport(op) end
    end
    if not op.synced and not op.refused then watchHit(a, op, t) end
    local inSync = a:IsInSyncAction(op.target)
    if inSync and not op.synced and not op.refused then
        op.synced = t
        log(string.format("%s lifts %s (sync %s)", def.label, nameOf(op.target), H.str(a:GetSyncActionID(char))))
    end
    if inSync then holdKeep(op.target, CONFIG.keepAfter) end
    if op.hit and not op.synced and not op.refused and t >= op.hit + CONFIG.liftWait then
        op.refused = t
        if def.liftMotion then
            a:PlayPartMotion(char, N(def.liftMotion), N(def.liftBone), def.liftLayer, -1.0, -1.0)
        end
        log(string.format("%s: the game doesn't lift %s; he does the lift (%s) and throws it off in %.1f s", def.label,
            nameOf(op.target), tostring(def.liftMotion), CONFIG.throwOffAfter))
        holdKeep(op.target, CONFIG.throwOffAfter + CONFIG.keepAfter)
    end
    -- the throw-off: the lift ends (or, when it couldn't be lifted, the mod's throw-off hit)
    if op.synced and not inSync and not op.thrown then
        op.thrown = t
        log(string.format("%s throws %s off", def.label, nameOf(op.target)))
    end
    if op.refused and not op.thrown and t >= op.refused + CONFIG.throwOffAfter then
        op.thrown = t
        local hit = def.throwOff[op.source] or def.throwOff[def.sources[1]]
        a:CreateDamageSource(N(hit), char, op.target, N(op.ability), false, 0)
        log(string.format("%s throws %s off (%s)", def.label, nameOf(op.target), hit))
    end
    if op.thrown then
        holdKeep(op.target, CONFIG.keepAfter)
        if not op.launched and t >= op.thrown + CONFIG.launch.wait then
            op.launched = t
            launch(a, op)
        end
        return op.launched ~= nil
    end
    if op.synced then return t > op.start + 15.0 end   -- (a lift that never ends)
    local busy = current == op.ability or (op.sourceAt and t <= op.sourceAt + CONFIG.hitWindow)
    return not busy and not op.hit and t > op.start + 1.0
end

local function step()
    if not CONFIG.enabled or not valid(char) then return end
    local a = api()
    if not a then return end
    local t = now()
    local ability = H.str(a:GetCurrentAbilityID(char))
    if ability ~= current then
        local def = CONFIG.moves[ability]
        if def then startOp(a, ability, def) end
        current = ability
    end
    local still = {}
    for _, op in ipairs(ops) do
        if not op.target and t <= op.start + 1.5 then aim(a, op) end
        local done
        if not op.target then
            done = t > op.start + 1.5
            if done then log(string.format("%s: no target", op.def.label)) end
        elseif not valid(op.target) then
            done = true
        elseif op.def.kind == "bind" then
            done = stepBind(a, op, t)
        else
            done = stepSkewer(a, op, t)
        end
        if not done then table.insert(still, op) end
    end
    ops = still
    restoreKeeps(a, false)
end

-- main.lua's tick (every 200 ms): who your Sephiroth is. The work is in this module's own loop.
function M.tick(character, ability)
    char = character
end

function M.init(helpers)
    H = helpers
    characterClass = StaticFindObject("/Script/Engine.Character")
    if not valid(characterClass) then characterClass = nil end
    local ms = math.max(10, math.floor(CONFIG.stepSeconds * 1000))
    local queued = false   -- one step at a time (they don't pile up while the game thread is busy, as in a load)
    LoopAsync(ms, function()
        if CONFIG.enabled and char ~= nil and not queued then
            queued = true
            ExecuteInGameThread(function()
                queued = false
                local ok, err = pcall(step)
                if not ok then log("error " .. tostring(err)) end
            end)
        end
        return false
    end)
    H.log(string.format("ForceGrabs %s: Grip of Fate binds every enemy it hits (%.0f s), Skewer lifts every enemy it stabs and throws it off flying; bosses too",
        CONFIG.enabled and "on" or "off", CONFIG.bindSeconds))
end

return M
