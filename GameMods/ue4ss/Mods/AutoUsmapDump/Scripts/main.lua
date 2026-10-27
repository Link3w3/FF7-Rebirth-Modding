-- AutoUsmapDump: writes UE4SS's Mappings.usmap once, without needing the Ctrl+Numpad6 key.
-- About 45 seconds after the game starts (by then it is at the title screen), it does the same as
-- the Keybinds mod's DumpUSMAP key. It does nothing when a Mappings.usmap is already there.
-- To turn it off, rename enabled.txt in this folder to enabled.txt.off.

local function fileExists(path)
    local f = io.open(path, "rb")
    if f ~= nil then f:close() return true end
    return false
end

local function alreadyThere()
    return fileExists("Mappings.usmap") or fileExists("ue4ss/Mappings.usmap")
end

if alreadyThere() then
    print("[AutoUsmapDump] Mappings.usmap is already there; nothing to do.\n")
else
    print("[AutoUsmapDump] will write Mappings.usmap in about 45 seconds.\n")
    ExecuteWithDelay(45000, function()
        local function dump()
            if alreadyThere() then return end
            print("[AutoUsmapDump] writing Mappings.usmap...\n")
            DumpUSMAP()
            print("[AutoUsmapDump] Mappings.usmap written.\n")
        end
        if ExecuteInGameThread ~= nil then
            ExecuteInGameThread(dump)
        else
            dump()
        end
    end)
end
