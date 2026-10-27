-- ForceGrabs: your Sephiroth's grabs catch every enemy, bosses too.
--   Grip of Fate (PC0010_T_BindFeeler): the feeler he throws binds the enemy it hits (special status Sephiroth_BindFeeler:
--     the feeler EN9000_20_Feeler_BlackEnd2 wraps around it and holds it) for CONFIG.bindSeconds, then lets it go.
--   Skewer (PC0010_T_WarpStab): he vanishes and reappears in front of his target (CONFIG.teleport), runs it through, lifts
--     it on his sword (the move's second part, his B_AtkStab02) and throws it off with its swing, a blow that sends it
--     flying. (2.0) Every enemy, bosses and big monsters too: from the stab on, the enemy is carried on his blade by
--     Create a Character System 3.12 (RebirthSkelCompatImpale: it stands still in time on the blade, whatever its size)
--     until the swing throws it off (CONFIG.carry). Its guard ("keep"), armor and invincibility don't stop it: its keep
--     is 0, the move goes through its invincibility and it reacts to the hits while he does it.
-- How: an enemy reacts to a hit only when the hit's cut (50 for these) beats its guard ("keep": 60 to 100 for most monsters
-- and bosses, more while they attack), so most shrug both off. While he does one of them, his target's keep is 0
-- (EndBattleAPI SetOverrideKeep), so the game's own bind, lift and blow happen. When the game still doesn't bind it, the
-- mod binds it (AddSpecialStatusChangeID). An enemy the game won't lift (big monsters, bosses) can't be put on his sword
-- (a lift forced on it crashes the game), so he does the lift motion by himself and the throw-off hit lands on it; when the
-- throw-off leaves an enemy standing, it is launched (LaunchCharacter). Its keep goes back (ResetOverrideKeep) after.
-- The feeler is a character the binder must have loaded: his rows list it in FullyPlayableSephirothDataAssets_P, as the boss
-- Sephiroth's row does. Skewer's hits (PC0010_T_Stab_01, PC0010_T_StabDetach_01) are in it too, with his sword's reach.
-- It looks every CONFIG.stepSeconds while he is in a battle (2.0: nothing at all outside battles). UE4SS.log lines start
-- with "grabs:".
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
        wait = 0.12,        -- after the throw-off: how long before checking whether it flies
        minSpeed = 300.0,   -- an enemy already moving this fast (cm/s) is flying already
        push = 1500.0,      -- the launch: away from him (cm/s) ...
        up = 900.0,         -- ... and up (cm/s); a big enemy goes less far (by its size)
    },
    -- (2.0) Skewer's carry (Create a Character System 3.12+): from the stab on, the enemy is on his blade, lifted with the
    -- move's second part and thrown off with its swing.
    carry = {
        enabled = true,
        reach = 450.0,      -- the stab catches an enemy this close (cm, edge to edge) when its hit doesn't show in its HP
        throwAt = 2.2,      -- the swing that throws it off: this long into the lift (B_AtkStab02's slash is at 2.23 s) ...
        endedAfter = 0.2,   -- ... or this long after the move ended, when it ends before the swing
        maxSeconds = 7.0,   -- a carry never lasts longer
        -- true: the move plays the lift itself (Create a Character System 3.12's compat files play Skewer as one move, the
        -- stab and then B_AtkStab02), the mod doesn't play it; false: the mod plays it; nil: true when the carry is there
        liftInMove = nil,
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

-- (2.0) how far the target is from him, edge to edge (cm)
local function edgeDistance(target)
    local me, it = where(char), where(target)
    local dx, dy = it.X - me.X, it.Y - me.Y
    local myRadius = capsule(char)
    local itRadius = capsule(target)
    return math.sqrt(dx * dx + dy * dy) - myRadius - itRadius
end

-- (2.0) Create a Character System 3.12's carry (nil without it)
local function carryApi()
    local start, release = RebirthSkelCompatImpale, RebirthSkelCompatImpaleRelease
    if type(start) == "function" and type(release) == "function" then return start, release end
    return nil, nil
end

local function liftInMove()
    local v = CONFIG.carry.liftInMove
    if v == nil then return carryApi() ~= nil end
    return v
end

local function addressOf(object)
    if not valid(object) then return nil end
    local ok, at = pcall(function() return object:GetAddress() end)
    if ok and type(at) == "number" and at > 0 then return math.tointeger(at) or at end
    return nil
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
    -- (2.0) through every guard and armor: the move goes through its invincibility, and it reacts to the hits
    a:AddInvincibleThroughAbilityID(target, N(op.ability))
    a:SetDamageHitResponse(target, true)
    op.hitResponse = true
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
    local radius = capsule(target)
    local size = math.max(0.3, math.min(1.0, 100.0 / math.max(radius, 1.0)))   -- (2.0: a big one goes less far)
    target:LaunchCharacter({ X = dx * CONFIG.launch.push * size, Y = dy * CONFIG.launch.push * size, Z = CONFIG.launch.up * size }, true, true)
    log(string.format("%s: launched %s (%.0f cm/s; it stood still after the throw-off)", op.def.label, nameOf(target), CONFIG.launch.push * size))
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

-- Skewer: the game lifts the enemy it stabs (sync action PC0010_10_WarpStab) when that enemy can be lifted. (2.0) Every
-- other enemy (big monsters, bosses: the game won't lift them) is carried on his blade from the stab on (Create a Character
-- System 3.12's carry), he does the lift (B_AtkStab02, played on him) and its swing throws the enemy off, flying. (Never
-- CreateSyncAction on such an enemy: the game crashes in the lift's next tick.)
local function letGo(op, why)
    if op.carried and not op.released then
        op.released = now()
        local _, release = carryApi()
        local target = addressOf(op.target)
        if release and target then release(target, 0.0, 0.0) end
        if why then log(string.format("%s lets %s go (%s)", op.def.label, nameOf(op.target), why)) end
    end
end

local function stepSkewer(a, op, t)
    local def = op.def
    if CONFIG.teleport and not op.teleported and t >= op.start + CONFIG.teleport.at then
        op.teleported = t
        if current == op.ability then teleport(op) end
    end
    local inSync = a:IsInSyncAction(op.target)
    if inSync and not op.synced and not op.carried then
        op.synced = t
        log(string.format("%s lifts %s (sync %s)", def.label, nameOf(op.target), H.str(a:GetSyncActionID(char))))
    end
    if inSync then holdKeep(op.target, CONFIG.keepAfter) end
    -- the stab: its hit shows in the target's HP, or (2.0) it is out with the target in reach (a guard or a barrier
    -- that takes the damage still has it run through)
    if not op.hit and not op.synced then
        watchHit(a, op, t)
        if not op.hit and op.sourceAt and t <= op.sourceAt + 0.05 then
            local edge = edgeDistance(op.target)
            if edge <= CONFIG.carry.reach then
                op.hit = t
                log(string.format("%s reaches %s (%s out, %.0f cm away)", def.label, nameOf(op.target), tostring(op.source), edge))
            end
        end
    end
    -- (2.0) the carry: on his blade from the stab on
    if op.hit and not op.synced and not op.carried and not op.noCarry then
        local start = carryApi()
        local holder, target = addressOf(char), addressOf(op.target)
        if CONFIG.carry.enabled and start and holder and target and start(holder, target, CONFIG.carry.maxSeconds) then
            op.carried = t
            holdKeep(op.target, CONFIG.carry.maxSeconds + CONFIG.keepAfter)
            log(string.format("%s runs %s through: it is on his blade", def.label, nameOf(op.target)))
        else
            op.noCarry = true
            log(string.format("%s: %s can't be carried on his blade (%s); he does the lift and the throw-off hits it", def.label, nameOf(op.target),
                start and "the carry refused it" or "needs Create a Character System 3.12"))
        end
    end
    -- the lift: the move's second part
    if op.hit and not op.synced and not op.lifted and t >= op.hit + CONFIG.liftWait then
        op.lifted = t
        if def.liftMotion and not liftInMove() then
            a:PlayPartMotion(char, N(def.liftMotion), N(def.liftBone), def.liftLayer, -1.0, -1.0)
        end
        log(string.format("%s: he lifts %s (%s), the swing throws it off in %.1f s", def.label, nameOf(op.target),
            liftInMove() and "the move's own lift" or tostring(def.liftMotion), CONFIG.carry.throwAt))
        holdKeep(op.target, CONFIG.carry.throwAt + CONFIG.keepAfter + 1.0)
    end
    -- the throw: with the lift's swing, or when the move ends before it
    if op.lifted and not op.thrown then
        local swing = t >= op.lifted + CONFIG.carry.throwAt
        local ended = current ~= op.ability and t >= op.lifted + CONFIG.carry.endedAfter
        if swing or ended then
            op.thrown = t
            letGo(op, nil)
            local hit = def.throwOff[op.source] or def.throwOff[def.sources[1]]
            a:CreateDamageSource(N(hit), char, op.target, N(op.ability), false, 0)
            log(string.format("%s throws %s off (%s, %s)", def.label, nameOf(op.target), hit, swing and "the swing" or "the move ended"))
        end
    end
    -- the game's own lift ends: it throws it off itself
    if op.synced and not inSync and not op.thrown then
        op.thrown = t
        log(string.format("%s throws %s off", def.label, nameOf(op.target)))
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

-- (2.0) An op over (or its target gone): its carry let go, the target's reactions back to its own.
local function finishOp(a, op)
    letGo(op, "the move is over")
    if op.hitResponse and valid(op.target) then
        a:ResetDamageHitResponse(op.target)
        op.hitResponse = nil
    end
end

local inBattle = false   -- (2.0) main.lua's tick says (4 times a second): nothing is looked at outside battles

local function step()
    if not CONFIG.enabled or not valid(char) then return end
    local a = api()
    if not a then return end
    if not inBattle and #ops == 0 then
        if next(keeps) ~= nil then restoreKeeps(a, true) end
        current = "None"
        return
    end
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
        if done and op.target then finishOp(a, op) end
        if not done then table.insert(still, op) end
    end
    ops = still
    restoreKeeps(a, false)
end

-- main.lua's tick (every 200 ms): who your Sephiroth is, and (2.0) whether it is a battle. The work is in this module's
-- own loop.
function M.tick(character, ability, battle)
    char = character
    if battle ~= nil then inBattle = battle end
end

-- RebirthSkelCompat's frame pump (main.lua calls this every frame, on the game thread). (Without the pump, the UE4SS
-- loop below does it.)
local lastPumpStep = -1.0
function M.pump()
    if not CONFIG.enabled or char == nil or (not inBattle and #ops == 0 and next(keeps) == nil) then return end
    local t = os.clock()
    if t - lastPumpStep < CONFIG.stepSeconds - 0.001 then return end
    lastPumpStep = t
    local ok, err = pcall(step)
    if not ok then log("error " .. tostring(err)) end
end

function M.init(helpers)
    H = helpers
    characterClass = StaticFindObject("/Script/Engine.Character")
    if not valid(characterClass) then characterClass = nil end
    local ms = math.max(10, math.floor(CONFIG.stepSeconds * 1000))
    local queued = false   -- one step at a time (they don't pile up while the game thread is busy, as in a load)
    local pumping = H.pumping or function() return false end
    local onGameThread = H.onGameThread or function() return true end
    LoopAsync(ms, function()
        if pumping() then return true end -- (the frame pump runs it now: this loop ends)
        if CONFIG.enabled and char ~= nil and not queued then
            queued = true
            ExecuteInGameThread(function()
                queued = false
                if pumping() or not onGameThread() then return end
                local ok, err = pcall(step)
                if not ok then log("error " .. tostring(err)) end
            end)
        end
        return false
    end)
    H.log(string.format("ForceGrabs 2.0 %s: Grip of Fate binds every enemy it hits (%.0f s), Skewer runs every enemy through, %s, and throws it off flying with its swing; bosses too, through their guard and armor",
        CONFIG.enabled and "on" or "off", CONFIG.bindSeconds, carryApi() and "carries it on his blade through the lift (Create a Character System's carry)" or "lifts it (no carry: Create a Character System 3.12 not found)"))
end

return M
