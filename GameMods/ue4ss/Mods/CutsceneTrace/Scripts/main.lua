-- CutsceneTrace: logs what a cutscene loads and creates, to find where one stops. Read-only: it changes nothing.
-- Output: lines starting with [CutsceneTrace] in ue4ss\UE4SS.log. Delete or rename enabled.txt to turn it off.
-- Everything runs on the game thread, once a second (nothing is hooked).

local function log(text)
    print(string.format("[CutsceneTrace] %s %s\n", os.date("%H:%M:%S"), text))
end

local function nameOf(object)
    local ok, name = pcall(function() return object:GetFullName() end)
    if ok and name then return name end
    return "?"
end

-- New objects of a class since the last look (names only), with an optional name filter.
local known = {}
local function newOf(shortClass, label, filter, limit)
    local objects = FindAllOf(shortClass)
    if not objects then return end
    known[shortClass] = known[shortClass] or {}
    local seen = known[shortClass]
    local fresh = 0
    for _, object in ipairs(objects) do
        if object:IsValid() then
            local name = nameOf(object)
            if not seen[name] and (not filter or filter(name)) then
                seen[name] = true
                fresh = fresh + 1
                if not limit or fresh <= limit then log(label .. " " .. name) end
            end
        end
    end
    if limit and fresh > limit then log(label .. " ... and " .. (fresh - limit) .. " more") end
end

local states = {}
local function players()
    local list = FindAllOf("LevelSequencePlayer")
    if not list then return end
    for _, player in ipairs(list) do
        if player:IsValid() then
            local name = nameOf(player)
            local status, sequence, playing = "?", "?", "?"
            pcall(function() status = tostring(player.Status) end)
            pcall(function() sequence = nameOf(player.Sequence) end)
            pcall(function() playing = tostring(player:IsPlaying()) end)
            local state = "status " .. status .. " playing " .. playing .. " sequence " .. sequence
            if states[name] ~= state then
                states[name] = state
                log("player " .. name .. " " .. state)
            end
        end
    end
end

local tick = 0
local first = true
LoopAsync(1000, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
            tick = tick + 1
            players()
            newOf("LevelSequenceActor", "sequence actor")
            newOf("EndCinemaSequence", "cinema sequence")
            if tick % 3 == 0 then
                -- The first look only records what is already there.
                if first then
                    newOf("SkeletalMesh", "mesh", nil, 0)
                    newOf("AnimSequence", "cut animation", function(n) return string.find(n, "/Cut/", 1, true) ~= nil end, 0)
                    first = false
                    log("baseline taken; from now on new meshes and cut animations are listed")
                else
                    newOf("SkeletalMesh", "mesh")
                    newOf("AnimSequence", "cut animation", function(n) return string.find(n, "/Cut/", 1, true) ~= nil end, 12)
                end
            end
        end)
        if not ok then log("error " .. tostring(err)) end
    end)
    return false
end)

log("CutsceneTrace ready")
