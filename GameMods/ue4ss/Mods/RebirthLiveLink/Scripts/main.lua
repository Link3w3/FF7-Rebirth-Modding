-- RebirthLiveLink: the End editor's live link to the running game.
--
-- The editor (or any tool) writes a command into link\command.lua next to this mod:
--     return { seq = 12, op = "spawn", path = "/Game/Effect/.../FX_PC0000_Limit01_CrossSlash_01", loop = true }
-- (or link\tool.lua, answered in link\tool_status.json: a second channel, so two tools never overwrite each other)
-- Each command runs once (a higher seq than the last one). What happened goes to link\status.json (the latest command's
-- result plus the state) and link\log.txt.
--
-- Commands (op):
--   ping                                    who is playing, what is spawned
--   spawn   path, forward, up, side, yaw, scale, loop, every, attach ("player"|"none"), socket
--                                           plays a Niagara system in front of the controlled character; loop replays it
--                                           every `every` seconds
--   stop                                    removes what the link spawned
--   probe   path                            an effect's emitters, scripts and data interfaces (what the live edits reach)
--   set_lut path, curve, hex [, samples, tmin, tmax] [, emitter] [, play, every, forward, up]
--                                           a colour/float curve's LUT values, written into every copy the game holds
--                                           (each script that samples the curve keeps its own frozen copy; a copy with
--                                           a different sample count gets the values resampled). Then the effect plays
--                                           at once so the change shows: replayed when it is the one playing, otherwise
--                                           played in front of the character again every `every` (4) seconds, like
--                                           spawn with loop (a game restart ends the replays; play = false skips this)
--   read    at, count                       raw memory (hex, at most 4096 bytes), for diagnostics
--   materials                               the controlled character's mesh components, their materials and values
--   set_material component, slot, params = { {type="vector"|"scalar"|"texture"|"texture_file", name=..., value=...}, ... }
--                                           (texture_file: a PNG file the game imports, ImportFileAsTexture2D: 8-bit as
--                                           an sRGB colour texture, 16-bit as half floats, the values as written)
--   slot_material component, slot, path    puts another material (an asset path) on the slot
--   material_params path, params            the values on every slot the character wears that uses material `path`
--   reset_material component, slot          the slot's original material back
--   reset_materials                         every slot the link changed back to its original material
--   mesh_swap component, path [, mode, force]
--                                           another model on a mesh component of the character: mode "follow" (any
--                                           skeleton: the component's own model stays on, hidden, and runs the game's
--                                           animation, physics and KDI; the other model is a mesh component of its own
--                                           following its pose by bone names) or "replace" (SetSkeletalMesh: a model of
--                                           the same skeleton only, unless force)
--   reset_models                            every model the link changed (or put on) back as the game had it
--   preset_put items = { {kind="material", mesh=, slot=, material=, params=}, {kind="mesh", mesh=, with=, mode=}, ...}
--                                           presets, kept in link\presets.lua for every game session: whenever a mesh
--                                           component anywhere wears the preset's model (`mesh`), the material goes on
--                                           its slot (with params) / the other model goes on it
--   preset_remove ids = {...} | all = true  takes presets off (and what they put on the character back)
--   presets                                 the presets and what they did
--   lua     code                            runs a Lua chunk on the game thread (UE4SS's globals, plus `link`: the link's
--                                           helpers, and link.every(name, fn) to run fn every frame until link.cancel(name))
--                                           and reports what it returns: for tools and diagnostics
--   pp_apply materials = { {path=..., weight=1.0}, ... } [, persist]
--                                           post-process materials on the scene: blendables of one unbound post process
--                                           volume (the link spawns its own when the level has none), put back after every
--                                           level change; kept in link\postprocess.lua for the next game session unless
--                                           persist = false
--   pp_clear [persist]                      takes them off again
--   pp_status                               what is applied, and the level's post process volumes
--
-- It runs on the game thread: every frame from RebirthSkelCompat 3.7.9+'s frame pump, else (and while the pump is paused:
-- photo mode, menus) from a 250 ms UE4SS loop.

local MOD = "RebirthLiveLink"
local VERSION = "1.8.4"
local STARTED = os.time()   -- this game session (status.json: the editor sends its live edits again after a restart)

local function scriptDir()
    local src = debug.getinfo(1, "S").source
    src = src:gsub("^@", "")
    return src:match("^(.*)[/\\][^/\\]+$") or "."
end
-- the mod's folder: the scripts folder's parent (UE4SS reports it as "scripts" or "Scripts")
local function modDir(dir)
    local base, last = dir:match("^(.*)[/\\]([^/\\]+)$")
    if last and last:lower() == "scripts" then return base end
    if dir:lower() == "scripts" then return "." end
    return dir
end
local SCRIPT_DIR = scriptDir()
local MOD_DIR = modDir(SCRIPT_DIR)
local LINK = MOD_DIR .. "/link"

-- ---------------------------------------------------------------------------------------------------------------
-- small helpers
-- ---------------------------------------------------------------------------------------------------------------
local logFile = nil
local function log(text)
    local line = string.format("[%s] %s", os.date("%H:%M:%S"), tostring(text))
    print("[" .. MOD .. "] " .. tostring(text) .. "\n")
    if not logFile then logFile = io.open(LINK .. "/log.txt", "a") end
    if logFile then logFile:write(line .. "\n"); logFile:flush() end
end

local function valid(o)
    if o == nil then return false end
    local ok, r = pcall(function() return o:IsValid() end)
    return ok and r
end

local function str(v)
    if v == nil then return "" end
    local ok, s = pcall(function() return v:ToString() end)
    if ok and s then return s end
    return tostring(v)
end

local function fullName(o)
    if not valid(o) then return nil end
    local ok, n = pcall(function() return o:GetFullName() end)
    return ok and n or nil
end

local function objPath(path)
    -- "/Game/A/B" -> "/Game/A/B.B"
    if path:find("%.") then return path end
    return path .. "." .. path:match("([^/]+)$")
end

-- JSON (just enough for status files)
local function jsonEscape(s)
    return (s:gsub('[%c"\\]', function(c)
        if c == '"' then return '\\"' elseif c == '\\' then return '\\\\' elseif c == '\n' then return '\\n'
        elseif c == '\r' then return '\\r' elseif c == '\t' then return '\\t' end
        return string.format('\\u%04x', c:byte())
    end))
end
local function isArray(t)
    local n = 0
    for k, _ in pairs(t) do
        if type(k) ~= "number" then return false end
        n = n + 1
    end
    return n == #t
end
local function json(v, seen, depth)
    local t = type(v)
    if t == "nil" then return "null" end
    if t == "boolean" then return v and "true" or "false" end
    if t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        if math.type and math.type(v) == "integer" then return tostring(v) end
        return string.format("%.7g", v)
    end
    if t == "string" then return '"' .. jsonEscape(v) .. '"' end
    if t == "table" then
        seen = seen or {}
        depth = depth or 0
        if seen[v] or depth > 24 then return '"(cycle)"' end
        seen[v] = true
        local parts = {}
        if isArray(v) then
            for _, x in ipairs(v) do parts[#parts + 1] = json(x, seen, depth + 1) end
            seen[v] = nil
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, x in pairs(v) do parts[#parts + 1] = json(tostring(k)) .. ":" .. json(x, seen, depth + 1) end
        seen[v] = nil
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return json(tostring(v))
end

local function writeFile(path, text)
    local tmp = path .. ".tmp"
    local f = io.open(tmp, "wb")
    if not f then return false end
    f:write(text); f:close()
    os.remove(path)
    return os.rename(tmp, path) and true or false
end

local function readFile(path)
    local f = io.open(path, "rb")
    if not f then return nil end
    local d = f:read("a"); f:close()
    return d
end

local function hexToFloats(hex)
    local out = {}
    for i = 1, #hex, 8 do
        local b = {}
        for j = 0, 3 do b[j + 1] = tonumber(hex:sub(i + 2 * j, i + 2 * j + 1), 16) end
        out[#out + 1] = string.unpack("<f", string.char(b[1], b[2], b[3], b[4]))
    end
    return out
end

local function floatsToHex(list)
    local parts = {}
    for i, v in ipairs(list) do
        local s = string.pack("<f", v)
        parts[i] = string.format("%02x%02x%02x%02x", s:byte(1, 4))
    end
    return table.concat(parts)
end

local haveMemory = (RebirthSkelCompatReadMemory ~= nil) and (RebirthSkelCompatWriteMemory ~= nil)

-- ---------------------------------------------------------------------------------------------------------------
-- the game
-- ---------------------------------------------------------------------------------------------------------------
local function player()
    local pc = FindFirstOf("PlayerController")
    if not valid(pc) then return nil, "no PlayerController" end
    local ok, pawn = pcall(function() return pc:K2_GetPawn() end)
    if not ok or not valid(pawn) then
        ok, pawn = pcall(function() return pc.Pawn end)
    end
    if not ok or not valid(pawn) then return nil, "no controlled character" end
    return pawn
end

local function vec(x, y, z) return { X = x, Y = y, Z = z } end

local pendingLoads = {} -- paths to load with LoadAsset in UE4SS's own game-thread call (it does not work under the pump)

-- UE4SS's LoadAsset looks the path up in the game's asset registry first, which does not list the new packages of
-- mods; FAssetData::GetAsset (AssetRegistryHelpers.GetAsset) loads its ObjectPath with the engine's own LoadObject
local registryHelpers = nil
local function loadByPath(path)
    if not valid(registryHelpers) then
        registryHelpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
    end
    if not valid(registryHelpers) then error("AssetRegistryHelpers not found") end
    local object = registryHelpers:GetAsset({ ObjectPath = FName(objPath(path)) })
    if valid(object) then return object end
    return nil
end

-- loads run on the game thread only: LoadObject on any other thread crashes in the game's async loader, and UE4SS 3.0.1
-- runs ExecuteInGameThread calls on whatever thread calls ProcessEvent next (RebirthSkelCompat's frame pump is the game
-- thread, after the world tick)
local function onGameThread()
    if RebirthSkelCompatIsGameThread == nil then return true end
    local ok, yes = pcall(RebirthSkelCompatIsGameThread)
    return (not ok) or yes == true
end

local pumping = false
local loadFailedAt = {}   -- path -> os.clock() of its last failed load (tried again after a few seconds)
local loadingNow = false

local function loadNow(path)
    local p = objPath(path)
    local last = loadFailedAt[p]
    if last and os.clock() - last < 5.0 then return nil end
    loadingNow = true
    local ok, loaded = pcall(loadByPath, p)
    loadingNow = false
    if ok and valid(loaded) then
        loadFailedAt[p] = nil
        log("load " .. p .. ": ok")
        return loaded
    end
    loadFailedAt[p] = os.clock()
    log("load " .. p .. ": failed" .. (ok and "" or (" (" .. tostring(loaded) .. ")")))
    return nil
end

local function findObject(path, wantLoad)
    local o = StaticFindObject(objPath(path))
    if valid(o) then return o end
    if wantLoad then
        if pumping and not loadingNow and onGameThread() then
            return loadNow(path)                     -- (from the frame pump: right away)
        end
        pendingLoads[objPath(path)] = true          -- (else in the next game-thread call)
    end
    return nil
end

-- ---------------------------------------------------------------------------------------------------------------
-- effects
-- ---------------------------------------------------------------------------------------------------------------
local spawned = {}      -- { path (the component's object path), at = os.clock() }
local looping = nil     -- the spawn command to replay, with nextAt

-- A component the link spawned is looked up again by its path before it is touched: a short effect destroys its own
-- component (auto destroy), and calling a game function on the old reference then raises an error that pcall cannot
-- catch (UE4SS's "UObject instance is nullptr"): 1.6 lost its frame pump that way after a replay.
local function liveComponent(e)
    if e.path == nil then return nil end
    local okF, o = pcall(StaticFindObject, e.path)
    if okF and valid(o) then return o end
    return nil
end

local function stopEffects()
    -- (the components were spawned with auto destroy: deactivating them is enough)
    local n = 0
    local list = spawned
    spawned = {}
    for _, e in ipairs(list) do
        local o = liveComponent(e)
        if o then
            pcall(function() o:DeactivateImmediate() end)
            n = n + 1
        end
    end
    return n
end

local function isNiagaraSystem(o)
    local name = fullName(o)
    return name ~= nil and name:find("^NiagaraSystem ") ~= nil
end

local function spawnOnce(cmd)
    local system = findObject(cmd.path, true)
    if not valid(system) then return nil, "the effect is not loaded yet (loading it; the next try plays it)" end
    if not isNiagaraSystem(system) then return nil, "not a Niagara effect: " .. tostring(fullName(system)) end
    local pawn, why = player()
    if not pawn then return nil, why end
    local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
    if not valid(lib) then return nil, "NiagaraFunctionLibrary not found" end
    local scale = cmd.scale or 1.0
    local comp
    if cmd.attach == "player" then
        local mesh = pawn.Mesh
        local socket = FName(cmd.socket or "None")
        comp = lib:SpawnSystemAttached(system, mesh, socket, vec(cmd.forward or 0, cmd.side or 0, cmd.up or 0), { Pitch = 0.0, Yaw = cmd.yaw or 0.0, Roll = 0.0 }, 2, true, true, 0, false)
    else
        local at = pawn:K2_GetActorLocation()
        local fwd = pawn:GetActorForwardVector()
        local right = pawn:GetActorRightVector()
        local f, s, u = cmd.forward or 250.0, cmd.side or 0.0, cmd.up or 0.0
        local where = vec(at.X + fwd.X * f + right.X * s, at.Y + fwd.Y * f + right.Y * s, at.Z + fwd.Z * f + u)
        local rot = pawn:K2_GetActorRotation()
        comp = lib:SpawnSystemAtLocation(pawn, system, where, { Pitch = 0.0, Yaw = rot.Yaw + (cmd.yaw or 0.0), Roll = 0.0 }, vec(scale, scale, scale), true, true, 0, false)
    end
    if not valid(comp) then return nil, "the game did not spawn it" end
    local name = fullName(comp)
    spawned[#spawned + 1] = { path = name and name:match("^%S+ (.+)$") or nil, at = os.clock() }
    return comp
end

local function scriptsOf(system)
    local out = {}
    local handles = system.EmitterHandles
    local n = handles:GetArrayNum()
    for i = 1, n do
        local h = handles[i]
        local em = h.Instance
        local emName = str(h.Name)
        if valid(em) then
            for _, key in ipairs({ "SpawnScriptProps", "UpdateScriptProps" }) do
                local okS, s = pcall(function() return em[key].Script end)
                if okS and valid(s) then out[#out + 1] = { emitter = emName, kind = key, script = s } end
            end
            local okG, g = pcall(function() return em.GPUComputeScript end)
            if okG and valid(g) then out[#out + 1] = { emitter = emName, kind = "GPUComputeScript", script = g } end
        end
    end
    for _, key in ipairs({ "SystemSpawnScript", "SystemUpdateScript" }) do
        local okS, s = pcall(function() return system[key] end)
        if okS and valid(s) then out[#out + 1] = { emitter = "(system)", kind = key, script = s } end
    end
    return out
end

-- ---------------------------------------------------------------------------------------------------------------
-- the curves' LUTs. Square Enix cooks every data interface of a script as a frozen memory image (no DataInterface
-- object at run time): each FNiagaraScriptDataInterfaceInfo of the script's CachedDefaultDataInterfaces (0x50 bytes)
-- points at its image (+0x40); a curve image holds its LUT as a frozen TArray at +0x18 (offset<<1|1, count, max), the
-- LUT's MinTime, MaxTime, InvTimeRange and NumSamples-1 at +0x28, the values after. The game samples those values (the
-- CPU VM reads them in place; GPU emitters got a copy on the graphics card when the effect loaded).
-- ---------------------------------------------------------------------------------------------------------------
local DI_INFO_SIZE = 0x50
local DI_INFO_IMAGE = 0x40

local function hexToBytes(hex)
    return (hex:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end))
end

local function readBytes(at, count)
    if not haveMemory or not at or at == 0 then return nil end
    local hex = RebirthSkelCompatReadMemory(at, count)
    if not hex or #hex ~= count * 2 then return nil end
    return hexToBytes(hex)
end

local function readU64(at)
    local b = readBytes(at, 8)
    if not b then return nil end
    return (string.unpack("<I8", b))
end

local function addressOf(userdata)
    -- "userdata: 00007FED89AE5C48" -> number
    local hex = tostring(userdata):match("(%x+)$")
    return hex and tonumber(hex, 16) or nil
end

local function arrayAddress(object, propertyName)
    local okP, prop = pcall(function() return object:Reflection():GetProperty(propertyName) end)
    if not okP or not prop then return nil end
    local okV, at = pcall(function() return prop:ContainerPtrToValuePtr(object, 0) end)
    if not okV or not at then return nil end
    return addressOf(at)
end

-- every frozen copy of `curveName` in `script`: { data, count, samples, tmin, tmax }
local function curveCopies(script, curveName)
    local out = {}
    local okA, arr = pcall(function() return script.CachedDefaultDataInterfaces end)
    if not okA or not arr then return out end
    local n = arr:GetArrayNum()
    local arrayAt = arrayAddress(script, "CachedDefaultDataInterfaces")
    if not arrayAt then return out end
    local head = readBytes(arrayAt, 16)
    if not head then return out end
    local data, num = string.unpack("<I8i4", head)
    if num ~= n or data == 0 then return out end
    for i = 1, n do
        local info = arr[i]
        if str(info.Name) == curveName then
            local elem = data + (i - 1) * DI_INFO_SIZE
            local nameOk = true
            local okI, index = pcall(function() return info.Name:GetComparisonIndex() end)
            if okI and type(index) == "number" then
                local nb = readBytes(elem + 8, 4)
                nameOk = nb ~= nil and string.unpack("<I4", nb) == index
            end
            local img = nameOk and readU64(elem + DI_INFO_IMAGE) or nil
            local ib = img and img ~= 0 and readBytes(img, 0x40) or nil
            if ib then
                local frozen, count, max = string.unpack("<I8i4i4", ib, 0x18 + 1)
                local tmin, tmax, _, last = string.unpack("<ffff", ib, 0x28 + 1)
                local samples = math.floor(last + 0.5) + 1
                if (frozen & 1) == 1 and count > 0 and count == max and samples > 0 and count % samples == 0 then
                    out[#out + 1] = { data = img + 0x18 + (frozen >> 1), count = count, samples = samples, tmin = tmin, tmax = tmax }
                end
            end
        end
    end
    return out
end

-- values (samples x elems, over [tmin, tmax]) at another sampling
local function resample(values, elems, tmin, tmax, samples, toMin, toMax)
    local n = #values // elems
    local out = {}
    for k = 0, samples - 1 do
        local t = (samples > 1) and (toMin + (toMax - toMin) * k / (samples - 1)) or toMin
        local u = (tmax > tmin) and ((t - tmin) / (tmax - tmin) * (n - 1)) or 0
        if u < 0 then u = 0 end
        if u > n - 1 then u = n - 1 end
        local i0 = math.floor(u)
        local i1 = math.min(i0 + 1, n - 1)
        local f = u - i0
        for e = 1, elems do
            local a, b = values[i0 * elems + e], values[i1 * elems + e]
            out[#out + 1] = a + (b - a) * f
        end
    end
    return out
end

local function looksLikePointer(v)
    return v >= 0x10000000000 and v < 0x7fffffff0000 and (v % 8) == 0
end

local function readU64s(hex)
    local out = {}
    for i = 1, #hex - 15, 16 do
        local bytes = {}
        for j = 0, 7 do bytes[j + 1] = tonumber(hex:sub(i + 2 * j, i + 2 * j + 1), 16) end
        out[#out + 1] = string.unpack("<I8", string.char(table.unpack(bytes)))
    end
    return out
end

local function probe(cmd)
    local system = findObject(cmd.path, true)
    if not valid(system) then return { ok = false, error = "the effect is not loaded yet (loading it; probe again)" } end
    if not isNiagaraSystem(system) then return { ok = false, error = "not a Niagara effect: " .. tostring(fullName(system)) } end
    local result = { ok = true, system = fullName(system), address = system:GetAddress(), scripts = {} }
    local dump = { system = fullName(system), scripts = {} }
    for _, s in ipairs(scriptsOf(system)) do
        local entry = { emitter = s.emitter, kind = s.kind, name = fullName(s.script), address = s.script:GetAddress(), dis = {} }
        local okA, arr = pcall(function() return s.script.CachedDefaultDataInterfaces end)
        if okA and arr then
            local n = arr:GetArrayNum()
            for i = 1, n do
                local info = arr[i]
                local di = info.DataInterface
                local d = { name = str(info.Name), object = fullName(di) }
                if valid(di) then
                    d.address = di:GetAddress()
                    d.class = fullName(di:GetClass())
                    local okL, lut = pcall(function() return di.ShaderLUT end)
                    if okL and lut then d.lut = lut:GetArrayNum() end
                end
                if haveMemory then
                    local copies = curveCopies(s.script, d.name)
                    if #copies > 0 then
                        d.frozen = string.format("0x%x", copies[1].data)
                        d.values = copies[1].count
                        d.samples = copies[1].samples
                    end
                end
                entry.dis[#entry.dis + 1] = d
            end
        end
        -- where the property's array lives (its data pointer, count, capacity), for the frozen copies
        local okP, prop = pcall(function() return s.script:Reflection():GetProperty("CachedDefaultDataInterfaces") end)
        if okP and prop then
            local okV, at = pcall(function() return prop:ContainerPtrToValuePtr(s.script, 0) end)
            if okV then entry.arrayAt = tostring(at) end
        end
        if haveMemory and cmd.dump then
            local base = s.script:GetAddress()
            local hex = RebirthSkelCompatReadMemory(base, 0x800)
            local d = { emitter = s.emitter, kind = s.kind, address = base, object = hex, targets = {} }
            local seen = 0
            for _, v in ipairs(readU64s(hex)) do
                if looksLikePointer(v) and d.targets[tostring(v)] == nil and seen < 96 then
                    local t = RebirthSkelCompatReadMemory(v, 0x200)
                    if t ~= "" then d.targets[tostring(v)] = t; seen = seen + 1 end
                end
            end
            dump.scripts[#dump.scripts + 1] = d
        end
        result.scripts[#result.scripts + 1] = entry
    end
    result.memory = haveMemory
    if haveMemory and cmd.dump then
        writeFile(LINK .. "/probe.json", json(dump))
        result.dump = LINK .. "/probe.json"
    end
    return result
end

local function setLut(cmd)
    local system = findObject(cmd.path, true)
    if not valid(system) then return { ok = false, loading = true, error = "the effect is not loaded yet (loading it; edit again)" } end
    if not isNiagaraSystem(system) then return { ok = false, error = "not a Niagara effect: " .. tostring(fullName(system)) } end
    if not haveMemory then return { ok = false, error = "RebirthSkelCompat 3.7.9+ is needed (memory access)" } end
    local floats = hexToFloats(cmd.hex)
    local copies, gpu = {}, false
    for _, s in ipairs(scriptsOf(system)) do
        if cmd.emitter == nil or cmd.emitter == s.emitter then
            for _, c in ipairs(curveCopies(s.script, cmd.curve)) do
                c.where = s.emitter .. " " .. s.kind
                c.gpu = (s.kind == "GPUComputeScript")
                copies[#copies + 1] = c
            end
        end
    end
    if #copies == 0 then return { ok = false, error = "no copy of " .. tostring(cmd.curve) .. " found in the game" } end
    -- the sampling the editor used: given, or the first copy with as many values
    local src = nil
    if cmd.samples and cmd.tmin and cmd.tmax then
        src = { samples = cmd.samples, tmin = cmd.tmin, tmax = cmd.tmax }
    else
        for _, c in ipairs(copies) do if c.count == #floats then src = c; break end end
    end
    local written, via = 0, {}
    for _, c in ipairs(copies) do
        local elems = c.count // c.samples
        local values = floats
        if #floats ~= c.count or (src and (src.tmin ~= c.tmin or src.tmax ~= c.tmax)) then
            local s = src or { tmin = c.tmin, tmax = c.tmax }
            values = resample(floats, elems, s.tmin, s.tmax, c.samples, c.tmin, c.tmax)
        end
        if #values == c.count and RebirthSkelCompatWriteMemory(c.data, floatsToHex(values)) then
            written = written + 1
            if c.gpu then gpu = true end
            via[#via + 1] = string.format("%s at 0x%x (%d values)", c.where, c.data, c.count)
        end
    end
    local result = { ok = written > 0, written = written, copies = #copies, via = via }
    if written == 0 then result.error = "the game's copies of the curve did not take the values" end
    if gpu then result.note = "GPU emitters keep the copy they uploaded when the effect loaded: their change shows after a game restart with the exported mod" end
    return result
end

-- ---------------------------------------------------------------------------------------------------------------
-- materials
-- ---------------------------------------------------------------------------------------------------------------
local originals = {} -- "component|slot" -> original material

-- a texture from a PNG file (KismetRenderingLibrary:ImportFileAsTexture2D: 8-bit as an sRGB BGRA texture, 16-bit as
-- half-float RGBA, the values as written); a transient texture, kept alive by the material it goes on
local renderingLib = nil
local function importTexture(file)
    if type(file) ~= "string" or file == "" then return nil, "no file" end
    if not valid(renderingLib) then renderingLib = StaticFindObject("/Script/Engine.Default__KismetRenderingLibrary") end
    if not valid(renderingLib) then return nil, "the game has no KismetRenderingLibrary" end
    local context = player() or FindFirstOf("PlayerController")
    if not valid(context) then return nil, "no world yet" end
    local ok, t = pcall(function() return renderingLib:ImportFileAsTexture2D(context, file) end)
    if ok and valid(t) then return t end
    return nil, "the game could not read " .. file
end

local function isMid(m)
    local n = fullName(m)
    return n ~= nil and n:find("MaterialInstanceDynamic", 1, true) ~= nil
end

-- params = { {type="scalar"|"vector"|"texture"|"texture_file", name=, value=}, ... } on a dynamic material instance
local function applyParams(mid, params)
    local done = {}
    for _, p in ipairs(params or {}) do
        local name = FName(p.name)
        local ok = false
        if p.type == "scalar" then
            ok = pcall(function() mid:SetScalarParameterValue(name, p.value) end)
        elseif p.type == "vector" then
            local v = p.value
            ok = pcall(function() mid:SetVectorParameterValue(name, { R = v[1], G = v[2], B = v[3], A = v[4] or 1.0 }) end)
        elseif p.type == "texture" then
            local tex = findObject(p.value, true)
            if valid(tex) then ok = pcall(function() mid:SetTextureParameterValue(name, tex) end) end
        elseif p.type == "texture_file" then
            local tex = importTexture(p.value)
            if valid(tex) then ok = pcall(function() mid:SetTextureParameterValue(name, tex) end) end
        end
        done[#done + 1] = { name = p.name, ok = ok }
    end
    return done
end

local function meshComponents(pawn)
    local out = {}
    for _, cls in ipairs({ "SkeletalMeshComponent", "StaticMeshComponent" }) do
        local list = FindAllOf(cls) or {}
        for _, comp in ipairs(list) do
            local okO, owner = pcall(function() return comp:GetOwner() end)
            if okO and valid(owner) then
                local mine = owner:GetAddress() == pawn:GetAddress()
                if not mine then
                    local okP, parent = pcall(function() return owner:GetAttachParentActor() end)
                    mine = okP and valid(parent) and parent:GetAddress() == pawn:GetAddress()
                end
                if mine then out[#out + 1] = comp end
            end
        end
    end
    return out
end

local function materialAt(comp, index)
    -- this game's GetMaterial takes (ElementIndex, LayerIndex)
    local ok, m = pcall(function() return comp:GetMaterial(index, 0) end)
    if ok and valid(m) then return m end
    return nil
end

local function paramsOf(material)
    local out = { scalars = {}, vectors = {}, textures = {} }
    local okS, s = pcall(function() return material.ScalarParameterValues end)
    if okS and s then
        for i = 1, s:GetArrayNum() do
            local v = s[i]
            out.scalars[#out.scalars + 1] = { name = str(v.ParameterInfo.Name), value = v.ParameterValue }
        end
    end
    local okV, vv = pcall(function() return material.VectorParameterValues end)
    if okV and vv then
        for i = 1, vv:GetArrayNum() do
            local v = vv[i]
            local c = v.ParameterValue
            out.vectors[#out.vectors + 1] = { name = str(v.ParameterInfo.Name), value = { c.R, c.G, c.B, c.A } }
        end
    end
    local okT, t = pcall(function() return material.TextureParameterValues end)
    if okT and t then
        for i = 1, t:GetArrayNum() do
            local v = t[i]
            out.textures[#out.textures + 1] = { name = str(v.ParameterInfo.Name), value = fullName(v.ParameterValue) }
        end
    end
    return out
end

local function chainOf(material)
    local chain = {}
    local m = material
    for _ = 1, 16 do
        if not valid(m) then break end
        chain[#chain + 1] = fullName(m)
        local ok, p = pcall(function() return m.Parent end)
        if not ok or not valid(p) then break end
        m = p
    end
    return chain
end

local function listMaterials()
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local result = { ok = true, character = fullName(pawn), components = {} }
    for ci, comp in ipairs(meshComponents(pawn)) do
        local entry = { index = ci, name = fullName(comp), slots = {} }
        local okM, mesh = pcall(function() return comp.SkeletalMesh end)
        if not okM or not valid(mesh) then okM, mesh = pcall(function() return comp.StaticMesh end) end
        entry.mesh = fullName(mesh)
        local okN, n = pcall(function() return comp:GetNumMaterials() end)
        n = okN and n or 0
        for slot = 0, n - 1 do
            local m = materialAt(comp, slot)
            if m then
                local base = m
                local okP, p = pcall(function() return m.Parent end)
                -- (a material this link made dynamic reports its source's values, with the edits on top)
                entry.slots[#entry.slots + 1] = { slot = slot, material = fullName(m), chain = chainOf(m), params = paramsOf(base) }
            end
        end
        result.components[#result.components + 1] = entry
    end
    return result
end

local function componentAt(pawn, index)
    local list = meshComponents(pawn)
    return list[index]
end

local function setMaterial(cmd)
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local comp = componentAt(pawn, cmd.component)
    if not valid(comp) then return { ok = false, error = "no component " .. tostring(cmd.component) } end
    local key = fullName(comp) .. "|" .. tostring(cmd.slot)
    local current = materialAt(comp, cmd.slot)
    if not current then return { ok = false, error = "no material in slot " .. tostring(cmd.slot) } end
    local mid = current
    local isMid = fullName(current) and fullName(current):find("MaterialInstanceDynamic", 1, true)
    if not isMid then
        originals[key] = current
        local ok, made = pcall(function() return comp:CreateDynamicMaterialInstance(cmd.slot, 0, current, FName("RebirthLiveLink")) end)
        if not ok or not valid(made) then return { ok = false, error = "could not make the slot dynamic" } end
        mid = made
    end
    local done = applyParams(mid, cmd.params)
    return { ok = true, material = fullName(mid), set = done }
end

local function resetMaterial(cmd)
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local comp = componentAt(pawn, cmd.component)
    if not valid(comp) then return { ok = false, error = "no component " .. tostring(cmd.component) } end
    local key = fullName(comp) .. "|" .. tostring(cmd.slot)
    local orig = originals[key]
    if not valid(orig) then return { ok = false, error = "nothing to reset" } end
    -- (a fresh dynamic copy of the original, with no edits: this game's SetMaterial signature is not known for sure)
    local ok = pcall(function() comp:CreateDynamicMaterialInstance(cmd.slot, 0, orig, FName("RebirthLiveLinkReset")) end)
    originals[key] = nil
    return { ok = ok }
end

-- values on every slot of the controlled character (and what it holds) that uses material `path`, directly or through a
-- dynamic instance this link made of it
local function pathOf(o)
    -- "MaterialInstanceConstant /Game/A/B.B" -> "/game/a/b.b"
    local n = fullName(o)
    return n and (n:match("^%S+ (.+)$") or n):lower() or ""
end

local function usesMaterial(comp, slot, want)
    local m = materialAt(comp, slot)
    if not m then return false end
    if pathOf(m) == want then return true end
    local key = fullName(comp) .. "|" .. tostring(slot)
    if valid(originals[key]) and pathOf(originals[key]) == want then return true end
    local okP, p = pcall(function() return m.Parent end)
    return okP and valid(p) and pathOf(p) == want
end

local function materialParams(cmd)
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local want = objPath(cmd.path):lower()
    local slots, failed = {}, 0
    for ci, comp in ipairs(meshComponents(pawn)) do
        local okN, n = pcall(function() return comp:GetNumMaterials() end)
        for slot = 0, (okN and n or 0) - 1 do
            if usesMaterial(comp, slot, want) then
                local r = setMaterial({ component = ci, slot = slot, params = cmd.params })
                if r.ok then slots[#slots + 1] = string.format("%s #%d", fullName(comp) or "?", slot) else failed = failed + 1 end
            end
        end
    end
    if #slots == 0 then
        return { ok = false, error = "nothing the character wears uses " .. tostring(cmd.path) .. (failed > 0 and " (or the game refused the change)" or "") }
    end
    return { ok = true, slots = slots }
end

-- every slot this link changed back to its original material
local function resetMaterials()
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local done = 0
    for ci, comp in ipairs(meshComponents(pawn)) do
        local okN, n = pcall(function() return comp:GetNumMaterials() end)
        for slot = 0, (okN and n or 0) - 1 do
            local key = fullName(comp) .. "|" .. tostring(slot)
            if valid(originals[key]) then
                local r = resetMaterial({ component = ci, slot = slot })
                if r.ok then done = done + 1 end
            end
        end
    end
    return { ok = true, reset = done }
end

-- another material on a slot (a dynamic instance of it: this game's SetMaterial signature is not known for sure)
local function slotMaterial(cmd)
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local comp = componentAt(pawn, cmd.component)
    if not valid(comp) then return { ok = false, error = "no component " .. tostring(cmd.component) } end
    local material = findObject(cmd.path, true)
    if not valid(material) then return { ok = false, error = "the material is not loaded yet (loading it; try again)" } end
    local key = fullName(comp) .. "|" .. tostring(cmd.slot)
    if not valid(originals[key]) then
        local current = materialAt(comp, cmd.slot)
        if current then originals[key] = current end
    end
    local ok, made = pcall(function() return comp:CreateDynamicMaterialInstance(cmd.slot, 0, material, FName("RebirthLiveLink")) end)
    if not ok or not valid(made) then return { ok = false, error = "the game did not take the material" } end
    return { ok = true, material = fullName(made), parent = fullName(material) }
end

local function readMemory(cmd)
    if not haveMemory then return { ok = false, error = "no memory access" } end
    local count = math.min(tonumber(cmd.count) or 256, 4096)
    local hex = RebirthSkelCompatReadMemory(cmd.at, count)
    return { ok = hex ~= nil and hex ~= "", at = cmd.at, hex = hex }
end

-- ---------------------------------------------------------------------------------------------------------------
-- Lua from tools (op "lua"): a chunk runs with UE4SS's globals and `link`
-- ---------------------------------------------------------------------------------------------------------------
local hooks = {}      -- name -> { fn, every, nextAt, errors }
local hookOrder = {}

local link = {
    log = log, valid = valid, str = str, fullName = fullName, json = json, player = player, objPath = objPath,
    readBytes = readBytes, readU64 = readU64, addressOf = addressOf, arrayAddress = arrayAddress,
    hexToBytes = hexToBytes, hexToFloats = hexToFloats, floatsToHex = floatsToHex, memory = haveMemory,
    dir = LINK, writeFile = writeFile, readFile = readFile, version = VERSION,
}
function link.find(path) return findObject(path, false) end
function link.load(path) return findObject(path, true) end   -- the object if loaded, else nil and it loads before long
function link.read(at, count) return haveMemory and RebirthSkelCompatReadMemory(at, count) or nil end
function link.write(at, hex) return haveMemory and RebirthSkelCompatWriteMemory(at, hex) or false end
function link.every(name, fn, seconds)
    if hooks[name] == nil then hookOrder[#hookOrder + 1] = name end
    hooks[name] = { fn = fn, every = seconds or 0, nextAt = 0, errors = 0 }
    return true
end
function link.cancel(name)
    if hooks[name] == nil then return false end
    hooks[name] = nil
    for i, n in ipairs(hookOrder) do if n == name then table.remove(hookOrder, i); break end end
    return true
end
function link.hooks()
    local out = {}
    for _, n in ipairs(hookOrder) do out[#out + 1] = n end
    return out
end
link.state = {}   -- kept from one chunk to the next

local function runHooks(now)
    for _, name in ipairs({ table.unpack(hookOrder) }) do
        local h = hooks[name]
        if h and now >= h.nextAt then
            h.nextAt = now + h.every
            local ok, err = pcall(h.fn, now)
            if not ok then
                h.errors = h.errors + 1
                log("hook " .. name .. ": " .. tostring(err))
                if h.errors >= 10 then
                    link.cancel(name)
                    log("hook " .. name .. " stopped after 10 errors")
                end
            end
        end
    end
end

local luaEnv = setmetatable({ link = link }, { __index = _G })
local function runLua(cmd)
    if type(cmd.code) ~= "string" then return { ok = false, error = "no code" } end
    local chunk, err = load(cmd.code, "=" .. tostring(cmd.name or "lua"), "t", luaEnv)
    if not chunk then return { ok = false, error = tostring(err) } end
    local out = table.pack(pcall(chunk, cmd.args))
    if not out[1] then return { ok = false, error = tostring(out[2]) } end
    if out.n <= 2 then return { ok = true, value = out[2] } end
    return { ok = true, value = { table.unpack(out, 2, out.n) } }
end

-- ---------------------------------------------------------------------------------------------------------------
-- post-process materials: blendables of one unbound post process volume of the current world (the link's own,
-- spawned when the world has none), kept there across level changes. link\postprocess.lua keeps the list between
-- game sessions: return { { path = "/Engine/EngineMaterials/DefaultPostProcessMaterial", weight = 1.0 }, ... }
-- ---------------------------------------------------------------------------------------------------------------
local ppWanted = {}
local ppVolume = nil
local ppVolumeKey = nil
local ppVolumeOwn = false -- spawned by the link (else a level's own volume)
local ppApplied = {}      -- material path -> weight applied to ppVolume
local ppCheckAt = 0
local ppLast = nil        -- what the last attempt did (for pp_status)

local function ppSave()
    local parts = {}
    for _, m in ipairs(ppWanted) do
        parts[#parts + 1] = string.format("    { path = %q, weight = %s },", m.path, tostring(m.weight or 1.0))
    end
    writeFile(LINK .. "/postprocess.lua", "return {\n" .. table.concat(parts, "\n") .. "\n}\n")
end

local function ppLoad()
    local text = readFile(LINK .. "/postprocess.lua")
    if not text then return end
    local chunk = load(text, "postprocess", "t", {})
    if not chunk then return end
    local ok, list = pcall(chunk)
    if ok and type(list) == "table" then
        ppWanted = {}
        for _, m in ipairs(list) do
            if type(m) == "table" and type(m.path) == "string" then
                ppWanted[#ppWanted + 1] = { path = m.path, weight = tonumber(m.weight) or 1.0 }
            end
        end
    end
end

local function spawnPPVolume()
    local pawn = player()
    if not pawn then return nil, "no character to spawn the volume next to" end
    local gs = StaticFindObject("/Script/Engine.Default__GameplayStatics")
    local cls = StaticFindObject("/Script/Engine.PostProcessVolume")
    if not valid(gs) or not valid(cls) then return nil, "GameplayStatics or PostProcessVolume not found" end
    local xform = { Rotation = { X = 0.0, Y = 0.0, Z = 0.0, W = 1.0 }, Translation = { X = 0.0, Y = 0.0, Z = 0.0 },
                    Scale3D = { X = 1.0, Y = 1.0, Z = 1.0 } }
    local ok, actor = pcall(function() return gs:BeginDeferredActorSpawnFromClass(pawn, cls, xform, 1, nil) end)
    if not ok or not valid(actor) then return nil, "spawn failed: " .. tostring(actor) end
    pcall(function() actor = gs:FinishSpawningActor(actor, xform) end)
    if not valid(actor) then return nil, "finish spawning failed" end
    pcall(function() actor.bUnbound = true end)
    pcall(function() actor.bEnabled = true end)
    pcall(function() actor.BlendWeight = 1.0 end)
    pcall(function() actor.Priority = 100000.0 end)
    return actor
end

local function worldOf(o)
    local ok, w = pcall(function() return o:GetWorld() end)
    if ok and valid(w) then return w:GetAddress() end
    return nil
end

-- the volume to put the materials on: the link's own (unbound, top priority, spawned in the character's world); a
-- level's own unbound volume when spawning does not work
-- (UE4SS's GetWorld is the actor's level's own world: a streamed level's actors report theirs, so the check is only
-- made for the link's own volume, spawned next to the character)
local function inOtherWorld(vol)
    if not ppVolumeOwn then return false end
    local pawn = player()
    local here, there = pawn and worldOf(pawn), worldOf(vol)
    return here ~= nil and there ~= nil and here ~= there
end

local function ppTarget()
    if ppVolume and valid(ppVolume) and not inOtherWorld(ppVolume) then return ppVolume end
    ppVolume, ppVolumeKey, ppApplied, ppVolumeOwn = nil, nil, {}, false
    local why
    ppVolume, why = spawnPPVolume()
    ppVolumeOwn = ppVolume ~= nil
    if not ppVolume then
        for _, v in ipairs(FindAllOf("PostProcessVolume") or {}) do
            local okU, unbound = pcall(function() return v.bUnbound end)
            local okE, enabled = pcall(function() return v.bEnabled end)
            local okW, weight = pcall(function() return v.BlendWeight end)
            if okU and unbound and (not okE or enabled) and (not okW or type(weight) ~= "number" or weight > 0) then
                ppVolume = v
                break
            end
        end
    end
    if ppVolume then ppVolumeKey = ppVolume:GetAddress() end
    return ppVolume, why
end

local function blendableCount(vol)
    local ok, n = pcall(function() return vol.Settings.WeightedBlendables.Array:GetArrayNum() end)
    return ok and n or nil
end

-- puts material `m` on the volume with its weight; returns ok, how
local function ppPut(vol, m)
    local mat = findObject(m.path, true)
    if not valid(mat) then return false, "not loaded yet" end
    local before = blendableCount(vol)
    local ok, err = pcall(function() vol:AddOrUpdateBlendable(mat, m.weight or 1.0) end)
    local after = blendableCount(vol)
    if ok and (after == nil or before == nil or after >= before) then return true, "AddOrUpdateBlendable" end
    -- fall back to the array itself (UE4SS appends when writing one past the end)
    local okA, errA = pcall(function()
        local arr = vol.Settings.WeightedBlendables.Array
        local n = arr:GetArrayNum()
        for i = 1, n do
            local e = arr[i]
            if valid(e.Object) and fullName(e.Object) == fullName(mat) then e.Weight = m.weight or 1.0; return end
        end
        arr[n + 1] = { Weight = m.weight or 1.0, Object = mat }
    end)
    if okA then return true, "array" end
    return false, "AddOrUpdateBlendable: " .. tostring(err) .. "; array: " .. tostring(errA)
end

local function ppApply(force)
    if #ppWanted == 0 then return { ok = true, info = "no post-process materials" } end
    local vol, why = ppTarget()
    if not vol then ppLast = { ok = false, error = why }; return ppLast end
    local done = {}
    local allOk = true
    for _, m in ipairs(ppWanted) do
        if force or ppApplied[m.path] ~= (m.weight or 1.0) then
            local ok, how = ppPut(vol, m)
            if ok then ppApplied[m.path] = m.weight or 1.0 else allOk = false end
            done[#done + 1] = { path = m.path, ok = ok, how = how }
        end
    end
    ppLast = { ok = allOk, volume = fullName(vol), blendables = blendableCount(vol), changed = done }
    return ppLast
end

local function ppRemove(path)
    local vol = ppVolume
    ppApplied[path] = nil
    if not (vol and valid(vol)) then return end
    local mat = findObject(path, false)
    if not valid(mat) then return end
    if pcall(function() vol:AddOrUpdateBlendable(mat, 0.0) end) then return end
    -- (a weight of 0 is not drawn)
    pcall(function()
        local arr = vol.Settings.WeightedBlendables.Array
        for i = 1, arr:GetArrayNum() do
            local e = arr[i]
            if valid(e.Object) and fullName(e.Object) == fullName(mat) then e.Weight = 0.0 end
        end
    end)
end

local function ppOp(cmd)
    if cmd.op == "pp_apply" then
        for _, m in ipairs(ppWanted) do ppRemove(m.path) end
        ppWanted = {}
        for _, m in ipairs(cmd.materials or {}) do
            ppWanted[#ppWanted + 1] = { path = objPath(m.path), weight = tonumber(m.weight) or 1.0 }
        end
        if cmd.persist ~= false then ppSave() end
        return ppApply(true)
    elseif cmd.op == "pp_clear" then
        for _, m in ipairs(ppWanted) do ppRemove(m.path) end
        ppWanted = {}
        if cmd.persist ~= false then ppSave() end
        return { ok = true, info = "post-process materials removed" }
    elseif cmd.op == "pp_status" then
        local vols = {}
        for _, v in ipairs(FindAllOf("PostProcessVolume") or {}) do
            local e = { name = fullName(v), blendables = blendableCount(v) }
            pcall(function() e.unbound = v.bUnbound end)
            pcall(function() e.enabled = v.bEnabled end)
            pcall(function() e.priority = v.Priority end)
            vols[#vols + 1] = e
            if #vols >= 30 then break end
        end
        return { ok = true, wanted = ppWanted, volume = fullName(ppVolume), last = ppLast, volumes = vols }
    end
end

local function ppTick(now)
    if #ppWanted == 0 or now < ppCheckAt then return end
    ppCheckAt = now + 2.0
    -- a new level: the volume we used is gone (or another world's), apply again
    if ppVolume and (not valid(ppVolume) or ppVolume:GetAddress() ~= ppVolumeKey) then ppVolume = nil end
    if ppVolume and inOtherWorld(ppVolume) then ppVolume = nil end
    local pending = not ppVolume
    for _, m in ipairs(ppWanted) do if ppApplied[m.path] ~= (m.weight or 1.0) then pending = true end end
    if pending then
        local r = ppApply(false)
        if r and r.changed and #r.changed > 0 then
            log("post-process: " .. (r.ok and "applied" or ("not yet: " .. tostring(r.changed[1].how))) .. " on " .. tostring(r.volume))
        end
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- models: another model on a mesh component, at once (mesh_swap) or whenever the component wears a model (presets)
--   follow   the component keeps its own model, all its parts hidden: the game's animation, physics and KDI go on as
--            always, on it. The other model is a mesh component of its own on the same actor, attached to it and
--            following its pose by bone names (the engine's master pose; a bone the character's model does not have
--            keeps its reference pose relative to its parent, so it rides along). Any skeleton whose bones are named as
--            the character's (Remake's and Rebirth's are).
--   replace  the other model on the component itself (SetSkeletalMesh, the game's own way of changing models): a model
--            of the same skeleton only (the anim instance stays), with its bones in the same order (the game's physics
--            and KDI tables are by bone index)
-- ---------------------------------------------------------------------------------------------------------------
local followers = {}      -- component name -> { follower, master, mesh (its model, lower path), with (lower path), tick }
local modelOriginals = {} -- component name -> { comp, mesh (object), static }
local skelMeshClass = nil

local function pathOf(o)
    -- "MaterialInstanceConstant /Game/A/B.B" -> "/game/a/b.b"
    local n = fullName(o)
    return n and (n:match("^%S+ (.+)$") or n):lower() or ""
end

local function meshOf(comp)
    local ok, m = pcall(function() return comp.SkeletalMesh end)
    if ok and valid(m) then return m, false end
    ok, m = pcall(function() return comp.StaticMesh end)
    if ok and valid(m) then return m, true end
    return nil, nil
end

local function skeletonOf(mesh)
    local ok, s = pcall(function() return mesh.Skeleton end)
    if ok and valid(s) then return s end
    return nil
end

local function materialCount(comp)
    local ok, n = pcall(function() return comp:GetNumMaterials() end)
    return ok and n or 0
end

-- every part (material section) of the component's model shown or hidden, on every LOD
local function showParts(comp, shown)
    local n = materialCount(comp)
    local okL, lods = pcall(function() return comp:GetNumLODs() end)
    lods = (okL and type(lods) == "number" and lods > 0) and lods or 8
    for lod = 0, lods - 1 do
        for i = 0, n - 1 do
            pcall(function() comp:ShowMaterialSection(i, -1, shown, lod) end)
        end
    end
end

local function retireFollower(key)
    local rec = followers[key]
    if not rec then return end
    followers[key] = nil
    if valid(rec.follower) then pcall(function() rec.follower:K2_DestroyComponent(rec.follower) end) end
    if valid(rec.master) then
        showParts(rec.master, true)
        if rec.tick ~= nil then pcall(function() rec.master.VisibilityBasedAnimTickOption = rec.tick end) end
    end
end

local function makeFollower(comp, with)
    local okO, owner = pcall(function() return comp:GetOwner() end)
    if not okO or not valid(owner) then return nil, "the mesh component has no actor" end
    if not valid(skelMeshClass) then skelMeshClass = StaticFindObject("/Script/Engine.SkeletalMeshComponent") end
    if not valid(skelMeshClass) then return nil, "no SkeletalMeshComponent class" end
    local identity = { Rotation = { X = 0.0, Y = 0.0, Z = 0.0, W = 1.0 }, Translation = { X = 0.0, Y = 0.0, Z = 0.0 },
                       Scale3D = { X = 1.0, Y = 1.0, Z = 1.0 } }
    -- (as Create a Character System adds a form's parts: AddComponentByClass, the model, attached, its master pose)
    local ok, f = pcall(function() return owner:AddComponentByClass(skelMeshClass, true, identity, false) end)
    if not ok or not valid(f) then return nil, "the game did not add a mesh component (" .. tostring(f) .. ")" end
    pcall(function() f:SetSkeletalMesh(with, true) end)
    pcall(function() f:K2_AttachToComponent(comp, FName("None"), 2, 2, 2, true) end)
    local okM = pcall(function() f:SetMasterPoseComponent(comp, true) end)
    if not okM then
        pcall(function() f:K2_DestroyComponent(f) end)
        return nil, "the new model could not follow the character's pose"
    end
    return f
end

-- `with` on mesh component `comp` (mode "follow" or "replace"); returns a result table
local function putModel(comp, with, mode, force)
    local mesh, static = meshOf(comp)
    if not mesh then return { ok = false, error = "the component has no model" } end
    local key = fullName(comp)
    local withName = fullName(with) or ""
    local withSkeletal = withName:find("^SkeletalMesh ") ~= nil
    if static then
        if withSkeletal or not withName:find("^StaticMesh ") then return { ok = false, error = "a static model goes on a static mesh component" } end
        if not modelOriginals[key] then modelOriginals[key] = { comp = comp, mesh = mesh, static = true } end
        local ok, err = pcall(function() comp:SetStaticMesh(with) end)
        return { ok = ok, mode = "replace", error = (not ok) and tostring(err) or nil }
    end
    if not withSkeletal then return { ok = false, error = "not a skeletal model: " .. withName } end
    local s1, s2 = skeletonOf(mesh), skeletonOf(with)
    local same = s1 ~= nil and s2 ~= nil and s1:GetAddress() == s2:GetAddress()
    if mode == "replace" then
        if not same and not force then
            return { ok = false, error = "its skeleton (" .. pathOf(s2) .. ") is not the character's (" .. pathOf(s1) ..
                     "): use follow, which keeps the character's own model under it", other_skeleton = true }
        end
        retireFollower(key)
        if not modelOriginals[key] then modelOriginals[key] = { comp = comp, mesh = mesh, static = false } end
        local ok, err = pcall(function() comp:SetSkeletalMesh(with, true) end)
        showParts(comp, true)
        return { ok = ok, mode = "replace", same_skeleton = same, error = (not ok) and tostring(err) or nil }
    end
    local rec = followers[key]
    if rec and valid(rec.follower) then
        if rec.with == pathOf(with) then return { ok = true, mode = "follow", follower = fullName(rec.follower), already = true } end
        retireFollower(key)
    end
    local f, why = makeFollower(comp, with)
    if not f then return { ok = false, error = why } end
    local okT, tick = pcall(function() return comp.VisibilityBasedAnimTickOption end)
    -- (its model hidden, the component must still animate: AlwaysTickPoseAndRefreshBones)
    pcall(function() comp.VisibilityBasedAnimTickOption = 0 end)
    showParts(comp, false)
    followers[key] = { follower = f, master = comp, mesh = pathOf(mesh), with = pathOf(with), tick = okT and tick or nil }
    return { ok = true, mode = "follow", follower = fullName(f), same_skeleton = same }
end

local function meshSwap(cmd)
    local pawn, why = player()
    if not pawn then return { ok = false, error = why } end
    local comp = componentAt(pawn, cmd.component)
    if not valid(comp) then return { ok = false, error = "no component " .. tostring(cmd.component) } end
    local with = findObject(cmd.path, true)
    if not valid(with) then return { ok = false, error = "the model is not loaded yet (loading it; try again)" } end
    return putModel(comp, with, cmd.mode or "follow", cmd.force)
end

local function resetModels()
    local n = 0
    for key, _ in pairs(followers) do retireFollower(key); n = n + 1 end
    for key, o in pairs(modelOriginals) do
        if valid(o.comp) and valid(o.mesh) then
            if o.static then pcall(function() o.comp:SetStaticMesh(o.mesh) end)
            else pcall(function() o.comp:SetSkeletalMesh(o.mesh, true) end) end
            n = n + 1
        end
        modelOriginals[key] = nil
    end
    return { ok = true, reset = n }
end

-- followers whose character's model changed (a form, a look) or that are gone; a character's model that something
-- showed again (its parts) hidden again
local function checkFollowers()
    for key, rec in pairs(followers) do
        if not valid(rec.master) or not valid(rec.follower) then
            followers[key] = nil
            if valid(rec.follower) then pcall(function() rec.follower:K2_DestroyComponent(rec.follower) end) end
        else
            local m = meshOf(rec.master)
            if not m or pathOf(m) ~= rec.mesh then
                retireFollower(key)
            else
                local okS, shown = pcall(function() return rec.master:IsMaterialSectionShown(0, 0) end)
                if okS and shown then showParts(rec.master, false) end
            end
        end
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- presets: link\presets.lua (kept for every game session), put on whenever a mesh component anywhere wears the
-- preset's model: the player's character, a party member, a cutscene's copy of the model, after a restart, a level
-- change, a respawn or a form change. The mesh components are looked over every second or so (less often when that
-- takes long), the player's own model every quarter second.
-- ---------------------------------------------------------------------------------------------------------------
local presets = {}        -- id -> item
local presetIndex = {}    -- lower mesh path -> { item, ... }
local presetStatic = false
local presetScan = { at = 0, every = 1.0, ms = 0, quickAt = 0, put = 0, lastPut = nil, errors = {} }

local function luaLiteral(v)
    local t = type(v)
    if t == "string" then return string.format("%q", v) end
    if t == "number" then
        if math.type and math.type(v) == "integer" then return tostring(v) end
        return string.format("%.9g", v)
    end
    if t == "boolean" then return v and "true" or "false" end
    if t == "table" then
        local parts = {}
        if isArray(v) then
            for _, x in ipairs(v) do parts[#parts + 1] = luaLiteral(x) end
        else
            local keys = {}
            for k, _ in pairs(v) do keys[#keys + 1] = tostring(k) end
            table.sort(keys)
            for _, k in ipairs(keys) do
                local x = v[k]
                if x == nil then x = v[tonumber(k)] end
                parts[#parts + 1] = (k:match("^[%a_][%w_]*$") and k or ("[" .. string.format("%q", k) .. "]")) .. " = " .. luaLiteral(x)
            end
        end
        return "{ " .. table.concat(parts, ", ") .. " }"
    end
    return "nil"
end

local function presetId(item)
    if item.kind == "mesh" then return "mesh|" .. item.mesh:lower() end
    return "material|" .. item.mesh:lower() .. "|" .. tostring(item.slot)
end

local function presetIndexRebuild()
    presetIndex, presetStatic = {}, false
    for _, it in pairs(presets) do
        local k = it.mesh:lower()
        presetIndex[k] = presetIndex[k] or {}
        table.insert(presetIndex[k], it)
        if it.static then presetStatic = true end
    end
end

local function presetSave()
    local list = {}
    for _, it in pairs(presets) do list[#list + 1] = it end
    table.sort(list, function(a, b) return a.id < b.id end)
    local parts = {}
    for _, it in ipairs(list) do parts[#parts + 1] = "    " .. luaLiteral(it) .. "," end
    writeFile(LINK .. "/presets.lua", "-- RebirthLiveLink presets (Rebirth FX > Materials in the End editor makes them)\nreturn {\n" ..
              table.concat(parts, "\n") .. "\n}\n")
end

local function presetNormal(it)
    if type(it) ~= "table" or type(it.mesh) ~= "string" then return nil end
    local item = { kind = it.kind == "mesh" and "mesh" or "material", mesh = objPath(it.mesh), note = it.note, added = it.added or os.date("%Y-%m-%d %H:%M:%S"),
                   static = it.static and true or nil }
    if item.kind == "mesh" then
        if type(it.with) ~= "string" then return nil end
        item.with = objPath(it.with)
        item.mode = it.mode == "replace" and "replace" or "follow"
        item.force = it.force and true or nil
    else
        if type(it.material) ~= "string" or tonumber(it.slot) == nil then return nil end
        item.slot = math.floor(tonumber(it.slot))
        item.material = objPath(it.material)
        item.params = type(it.params) == "table" and it.params or nil
    end
    item.id = presetId(item)
    return item
end

local function presetLoad()
    local text = readFile(LINK .. "/presets.lua")
    if not text then return end
    local chunk = load(text, "presets", "t", {})
    if not chunk then log("presets.lua does not read: left as it is"); return end
    local ok, list = pcall(chunk)
    if not ok or type(list) ~= "table" then return end
    presets = {}
    for _, it in ipairs(list) do
        local item = presetNormal(it)
        if item then presets[item.id] = item end
    end
    presetIndexRebuild()
end

local function presetMaterial(comp, it)
    if it.slot >= materialCount(comp) then return end
    local cur = materialAt(comp, it.slot)
    local want = it.material:lower()
    if cur then
        if pathOf(cur) == want then return end
        if isMid(cur) then
            local okP, par = pcall(function() return cur.Parent end)
            if okP and valid(par) and pathOf(par) == want then return end
        end
    end
    local mat = findObject(it.material, true)
    if not valid(mat) then return end            -- (loading: the next look puts it on)
    local key = (fullName(comp) or "?") .. "|" .. tostring(it.slot)
    if cur and not valid(originals[key]) then originals[key] = cur end
    local ok = false
    if it.params and #it.params > 0 then
        local okM, mid = pcall(function() return comp:CreateDynamicMaterialInstance(it.slot, 0, mat, FName("RebirthLivePreset")) end)
        if okM and valid(mid) then applyParams(mid, it.params); ok = true end
    else
        ok = pcall(function() comp:SetMaterial(it.slot, mat) end)
        if ok then
            local now = materialAt(comp, it.slot)
            ok = now ~= nil and pathOf(now) == want
        end
        if not ok then
            local okM, mid = pcall(function() return comp:CreateDynamicMaterialInstance(it.slot, 0, mat, FName("RebirthLivePreset")) end)
            ok = okM and valid(mid)
        end
    end
    if ok then
        presetScan.put = presetScan.put + 1
        presetScan.lastPut = it.id
    else
        presetScan.errors[it.id] = "the game did not take it"
    end
end

local function presetModel(comp, it)
    local key = fullName(comp)
    if it.mode ~= "replace" then
        local rec = followers[key]
        if rec and valid(rec.follower) and rec.with == it.with:lower() then return end
    end
    local with = findObject(it.with, true)
    if not valid(with) then return end
    local r = putModel(comp, with, it.mode, it.force)
    if r.ok then
        presetScan.put = presetScan.put + 1
        presetScan.lastPut = it.id
        presetScan.errors[it.id] = nil
    else
        presetScan.errors[it.id] = r.error
    end
end

local function presetOn(comp)
    local mesh = meshOf(comp)
    if not mesh then return end
    local items = presetIndex[pathOf(mesh)]
    if not items then return end
    for _, it in ipairs(items) do
        if it.kind == "mesh" then presetModel(comp, it) else presetMaterial(comp, it) end
    end
end

local function presetTick(now)
    -- the player's own model and the models following, often (a respawn, a form change, a level)
    if now < presetScan.quickAt then return end
    presetScan.quickAt = now + 0.25
    if next(followers) ~= nil then checkFollowers() end
    if next(presets) == nil then return end
    local pawn = player()
    if pawn then
        local okM, mesh = pcall(function() return pawn.Mesh end)
        if okM and valid(mesh) then presetOn(mesh) end
    end
    if now < presetScan.at then return end
    local t0 = os.clock()
    for _, cls in ipairs(presetStatic and { "SkeletalMeshComponent", "StaticMeshComponent" } or { "SkeletalMeshComponent" }) do
        for _, comp in ipairs(FindAllOf(cls) or {}) do
            if valid(comp) then presetOn(comp) end
        end
    end
    local ms = (os.clock() - t0) * 1000.0
    presetScan.ms = ms
    -- (at most about half a percent of the time on the look-over)
    presetScan.every = math.max(1.0, math.min(10.0, ms / 5.0))
    presetScan.at = os.clock() + presetScan.every
end

-- what presets put on the player's character goes back when they are taken off
local function presetUndo(item)
    local pawn = player()
    if not pawn then return end
    for ci, comp in ipairs(meshComponents(pawn)) do
        local mesh = meshOf(comp)
        if item.kind == "mesh" then
            local key = fullName(comp)
            local rec = followers[key]
            if rec and rec.mesh == item.mesh:lower() then retireFollower(key) end
            local o = modelOriginals[key]
            if o and mesh and pathOf(mesh) == item.with:lower() and valid(o.mesh) then
                pcall(function() comp:SetSkeletalMesh(o.mesh, true) end)
                modelOriginals[key] = nil
            end
        elseif mesh and pathOf(mesh) == item.mesh:lower() then
            local key = (fullName(comp) or "?") .. "|" .. tostring(item.slot)
            if valid(originals[key]) then
                resetMaterial({ component = ci, slot = item.slot })
            end
        end
    end
end

local function presetOp(cmd)
    if cmd.op == "preset_put" then
        local put = {}
        for _, it in ipairs(cmd.items or {}) do
            local item = presetNormal(it)
            if item then
                if presets[item.id] then presetUndo(presets[item.id]) end
                presets[item.id] = item
                presetScan.errors[item.id] = nil
                put[#put + 1] = item.id
            end
        end
        presetIndexRebuild()
        presetSave()
        presetScan.at, presetScan.quickAt = 0, 0
        return { ok = #put > 0, put = put, count = (function() local n = 0; for _ in pairs(presets) do n = n + 1 end; return n end)(),
                 error = #put == 0 and "no preset in the command" or nil }
    elseif cmd.op == "preset_remove" then
        local removed = {}
        for id, it in pairs(presets) do
            local wanted = cmd.all
            for _, x in ipairs(cmd.ids or {}) do if x == id then wanted = true end end
            if wanted then removed[#removed + 1] = id end
        end
        for _, id in ipairs(removed) do
            local it = presets[id]
            presets[id] = nil
            presetScan.errors[id] = nil
            pcall(presetUndo, it)
        end
        presetIndexRebuild()
        presetSave()
        return { ok = true, removed = removed }
    elseif cmd.op == "presets" then
        local list = {}
        for _, it in pairs(presets) do
            local e = {}
            for k, v in pairs(it) do e[k] = v end
            e.error = presetScan.errors[it.id]
            list[#list + 1] = e
        end
        table.sort(list, function(a, b) return a.id < b.id end)
        local fol = {}
        for key, rec in pairs(followers) do fol[#fol + 1] = { component = key, with = rec.with } end
        return { ok = true, presets = list, scan_ms = presetScan.ms, every = presetScan.every, put = presetScan.put,
                 last_put = presetScan.lastPut, followers = fol }
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- commands
-- ---------------------------------------------------------------------------------------------------------------
-- two channels, each with its own sequence and status file, so two tools never overwrite each other's commands:
-- command.lua / status.json (the editor) and tool.lua / tool_status.json (other tools)
local channels = {
    { file = "command.lua", status = "status.json", lastSeq = -1, lastResult = { ok = true, info = "ready" } },
    { file = "tool.lua", status = "tool_status.json", lastSeq = -1, lastResult = { ok = true, info = "ready" } },
}

local function status(ch)
    local pawn = player()
    local playing = 0
    for _, e in ipairs(spawned) do if liveComponent(e) then playing = playing + 1 end end
    writeFile(LINK .. "/" .. ch.status, json({
        mod = MOD, version = VERSION, seq = ch.lastSeq, time = os.time(), character = fullName(pawn),
        playing = playing, looping = looping and looping.path or nil, memory = haveMemory, result = ch.lastResult,
        started = STARTED,
    }))
end

local function readCommand(ch)
    local text = readFile(LINK .. "/" .. ch.file)
    if not text or text == "" then return nil end
    -- (1.8.4) the same file as the last read: no new command (it was compiled every quarter second)
    if text == ch.lastText then return nil end
    ch.lastText = text
    local chunk = load(text, "command", "t", {})
    if not chunk then return nil end
    local okC, cmd = pcall(chunk)
    if not okC or type(cmd) ~= "table" or type(cmd.seq) ~= "number" then return nil end
    return cmd
end

local function run(cmd)
    local op = cmd.op
    if op == "ping" then return { ok = true, info = "pong" } end
    if op == "spawn" then
        stopEffects()
        local comp, why = spawnOnce(cmd)
        if cmd.loop then
            looping = cmd
            looping.nextAt = os.clock() + (cmd.every or 3.0)
        else
            looping = nil
        end
        if not comp then return { ok = false, error = why, retrying = cmd.loop and true or false } end
        return { ok = true, component = fullName(comp) }
    end
    if op == "stop" then
        looping = nil
        return { ok = true, removed = stopEffects() }
    end
    if op == "probe" then return probe(cmd) end
    if op == "set_lut" then
        local r
        if type(cmd.curves) == "table" then
            -- several curves in one command: { curves = { {curve=..., hex=..., samples=, tmin=, tmax=}, ... } }
            r = { ok = true, written = 0, curves = {} }
            for _, c in ipairs(cmd.curves) do
                local one = setLut({ path = cmd.path, emitter = c.emitter, curve = c.curve, hex = c.hex,
                                     samples = c.samples, tmin = c.tmin, tmax = c.tmax })
                r.curves[#r.curves + 1] = { curve = c.curve, ok = one.ok, written = one.written, error = one.error, note = one.note }
                r.written = r.written + (one.written or 0)
                if not one.ok then r.ok = false; r.error = one.error; r.loading = one.loading end
                if one.note then r.note = one.note end
            end
        else
            r = setLut(cmd)
        end
        if (r.written or 0) > 0 then
            -- show the change at once: replay the effect when it is the one playing, otherwise play it (nothing plays
            -- after a game restart, and an edit with nothing playing would show nowhere)
            if looping and looping.path == cmd.path then
                looping.nextAt = 0
                r.play = "replayed"
            elseif cmd.play ~= false then
                looping = { op = "spawn", path = cmd.path, loop = true, every = cmd.every or 4.0,
                            forward = cmd.forward or 300.0, up = cmd.up or 50.0, nextAt = 0 }
                r.play = "started"
            end
        end
        return r
    end
    if op == "materials" then return listMaterials() end
    if op == "set_material" then return setMaterial(cmd) end
    if op == "slot_material" then return slotMaterial(cmd) end
    if op == "reset_material" then return resetMaterial(cmd) end
    if op == "material_params" then return materialParams(cmd) end
    if op == "reset_materials" then return resetMaterials() end
    if op == "read" then return readMemory(cmd) end
    if op == "lua" then return runLua(cmd) end
    if op == "pp_apply" or op == "pp_clear" or op == "pp_status" then return ppOp(cmd) end
    if op == "mesh_swap" then return meshSwap(cmd) end
    if op == "reset_models" then return resetModels() end
    if op == "preset_put" or op == "preset_remove" or op == "presets" then return presetOp(cmd) end
    return { ok = false, error = "unknown op " .. tostring(op) }
end

local checkAt = 0
local lastCommandAt = -100.0   -- (1.8.4) the command files are read 4 times a second for 30 s after a command, else twice a second
local function tick()
    local now = os.clock()
    if looping and now >= (looping.nextAt or 0) then
        local replay = looping
        replay.nextAt = now + (replay.every or 3.0)       -- (before spawning: spawning can run the pump again)
        stopEffects()
        local ok, err = pcall(spawnOnce, replay)
        if not ok then log("replay failed: " .. tostring(err)) end
    end
    if hookOrder[1] then runHooks(now) end
    if next(presets) ~= nil or next(followers) ~= nil then
        local okP, errP = pcall(presetTick, now)
        if not okP then log("presets: " .. tostring(errP)); presetScan.at = now + 10.0 end
    end
    if ppWanted[1] then
        local okP, errP = pcall(ppTick, now)
        if not okP then log("post-process: " .. tostring(errP)); ppCheckAt = now + 10.0 end
    end
    if now < checkAt then return end
    checkAt = now + ((now - lastCommandAt < 30.0) and 0.25 or 0.5)
    for _, ch in ipairs(channels) do
        local cmd = readCommand(ch)
        if cmd and cmd.seq > ch.lastSeq then
            lastCommandAt = now
            ch.lastSeq = cmd.seq
            local okR, result = pcall(run, cmd)
            if not okR or type(result) ~= "table" then result = { ok = false, error = tostring(result) } end
            result.op = cmd.op
            ch.lastResult = result
            log(string.format("#%d %s%s: %s%s", cmd.seq, tostring(cmd.op), ch.file == "command.lua" and "" or " (" .. ch.file .. ")",
                result.ok and "ok" or ("failed: " .. tostring(result.error)),
                result.play == "started" and " (playing it now, again every " .. string.format("%g", looping and looping.every or 4) .. " s)" or ""))
            status(ch)
        end
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- what drives it (see SephirothForms: UE4SS 3.0.1's ExecuteInGameThread is not safe at frame rate)
-- ---------------------------------------------------------------------------------------------------------------
local busy = false
local busySince = 0
local errors = 0
local function drive()
    -- the game can call back into the pump while the link spawns an effect: never run inside itself. A round that an
    -- error pcall cannot catch cut short (the pump's own handler caught it) leaves busy set: after 3 s the link goes on.
    if busy then
        if os.clock() - busySince < 3.0 then return end
        log("the last round stopped half way (an error inside a game call); the link goes on")
        loadingNow = false
    end
    busy = true
    busySince = os.clock()
    local ok, err = pcall(tick)
    busy = false
    if not ok then
        errors = errors + 1
        if errors <= 20 or errors % 500 == 0 then log("error " .. tostring(err)) end
        if looping and errors >= 20 then
            log("replays stop after repeated errors (send the effect again to restart them)")
            looping = nil
        end
    else
        errors = 0
    end
end

-- ---------------------------------------------------------------------------------------------------------------
-- start: the commands left from before this start are marked as seen FIRST, and only then are the pump and the UE4SS
-- loop connected (UE4SS's "restart all mods" runs this file while the game keeps calling the pump: a command from
-- before the restart must not run, and nothing may run half set up)
-- ---------------------------------------------------------------------------------------------------------------
for _, ch in ipairs(channels) do
    pcall(function()
        local cmd = readCommand(ch)
        if cmd then ch.lastSeq = cmd.seq end
    end)
    pcall(function() os.remove(LINK .. "/" .. ch.status) end)
end
pcall(ppLoad)
pcall(presetLoad)

-- (1.8.3) the main menu watch of 1.8.2 is gone: Create a Character System 3.11 puts the Customization item on the main menu

local function runLoads()
    if next(pendingLoads) == nil then return end
    if not onGameThread() then return end          -- (they stay pending for the next round)
    for path, _ in pairs(pendingLoads) do
        pendingLoads[path] = nil
        local ok, loaded = pcall(function() return LoadAsset(path) end)
        local how = "ok"
        if not (ok and valid(loaded)) then
            -- not in the game's asset registry (a mod's new package): the engine's loader, by path
            local ok2, loaded2 = pcall(loadByPath, path)
            if ok2 and valid(loaded2) then
                how = "ok (by path)"
            else
                how = "failed" .. (ok2 and "" or (" (" .. tostring(loaded2) .. ")"))
            end
        end
        log("load " .. path .. ": " .. how)
    end
end

local lastPumpAt = 0
-- the frame pump stops while the game is paused (photo mode, menus): the UE4SS loop takes over meanwhile
local queued = false
local stalledLogged = false
LoopAsync(250, function()
    local wantLoad = next(pendingLoads) ~= nil
    local stalled = pumping and (os.clock() - lastPumpAt) > 1.0
    if pumping and not stalled and not wantLoad then
        stalledLogged = false
        return false
    end
    if stalled and not stalledLogged then
        stalledLogged = true
        log("the frame pump is paused: the UE4SS loop drives the link until it runs again")
    end
    if not queued then
        queued = true
        ExecuteInGameThread(function()
            queued = false
            -- loads first (LoadAsset works only in UE4SS's own game-thread calls)
            runLoads()
            if not pumping or (os.clock() - lastPumpAt) > 1.0 then drive() end
        end)
    end
    return false
end)

RebirthSkelCompatPump = function()
    if not pumping then
        pumping = true
        log("RebirthSkelCompat's frame pump drives the link now (game thread, every frame)")
    end
    lastPumpAt = os.clock()
    drive()
end

log(string.format("%s %s ready: commands from %s/command.lua and tool.lua%s%s", MOD, VERSION, LINK, haveMemory and " (memory access on)" or "",
    #ppWanted > 0 and string.format(" (%d post-process material(s) to keep on the scene)", #ppWanted) or ""))
for _, ch in ipairs(channels) do status(ch) end
