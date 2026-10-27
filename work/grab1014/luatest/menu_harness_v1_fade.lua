-- Plain-Lua test of main.lua + FormMenu.lua (the moveset menu, the wing's slots and fades) with strict UE4SS stand-ins:
-- wrong parameter types or counts fail like UE4SS, ExecuteInGameThread from inside a game-thread action fails.
local SCRIPTS = "/work/sephforms/mod/SephirothForms/Scripts/"
package.path = SCRIPTS .. "?.lua;" .. package.path
package.preload["ForceGrabs"] = function() return { init = function() end, tick = function() end } end
package.preload["MeteorStrike"] = function() return { init = function() end, tick = function() end } end

local logs = {}
local realPrint = print
print = function(text)
    text = tostring(text):gsub("\n$", "")
    table.insert(logs, text)
    realPrint("  | " .. text)
end
local function found(pattern)
    for _, line in ipairs(logs) do if line:find(pattern, 1, true) then return true end end
    return false
end
local function count(pattern)
    local n = 0
    for _, line in ipairs(logs) do if line:find(pattern, 1, true) then n = n + 1 end end
    return n
end
local clock = 100.0
os.clock = function() return clock end
os.date = function() return "00:00:00" end

local FNameMeta = { __index = { ToString = function(self) return self.__text end } }
function FName(s)
    assert(type(s) == "string", "FName wants a string")
    return setmetatable({ __text = s, __fname = true }, FNameMeta)
end
local FTextMeta = { __index = { ToString = function(self) return self.__text end } }
FText = setmetatable({}, { __call = function(_, s)
    assert(type(s) == "string", "FText wants a string")
    return setmetatable({ __text = s, __ftext = true }, FTextMeta)
end })

local nullMeta = {}
local function Null() return setmetatable({ __null = true }, nullMeta) end
nullMeta.__index = function(self, k)
    if k == "IsValid" then return function() return false end end
    return function() error("Tried calling a member function but the UObject instance is nullptr") end
end

local function chk(v, kind, what)
    local ok
    if kind == "obj" then ok = type(v) == "table" and (v.__obj == true or v.__null == true)
    elseif kind == "objornil" then ok = v == nil or (type(v) == "table" and (v.__obj == true or v.__null == true))
    elseif kind == "name" then ok = type(v) == "table" and v.__fname == true
    elseif kind == "text" then ok = type(v) == "table" and v.__ftext == true
    elseif kind == "int" then ok = math.type(v) == "integer"
    elseif kind == "num" then ok = type(v) == "number"
    elseif kind == "bool" then ok = type(v) == "boolean"
    elseif kind == "v2" then ok = type(v) == "table" and type(v.X) == "number" and type(v.Y) == "number" and v.__obj == nil
    elseif kind == "color" then ok = type(v) == "table" and type(v.R) == "number" and type(v.G) == "number" and type(v.B) == "number" and type(v.A) == "number"
    elseif kind == "slatecolor" then ok = type(v) == "table" and type(v.SpecifiedColor) == "table" and type(v.SpecifiedColor.R) == "number" and math.type(v.ColorUseRule) == "integer"
    elseif kind == "anchors" then ok = type(v) == "table" and type(v.Minimum) == "table" and type(v.Maximum) == "table" and type(v.Minimum.X) == "number"
    elseif kind == "font" then ok = type(v) == "table" and (v.FontObject == nil or v.FontObject.__obj == true) and math.type(v.Size) == "integer" and (v.TypefaceFontName == nil or v.TypefaceFontName.__fname)
    elseif kind == "key" then ok = type(v) == "table" and type(v.KeyName) == "table" and v.KeyName.__fname == true
    elseif kind == "rot" then ok = type(v) == "table" and type(v.Pitch) == "number" and type(v.Yaw) == "number" and type(v.Roll) == "number"
    elseif kind == "table" then ok = type(v) == "table" and v.__obj == nil
    end
    if not ok then error("bad parameter " .. tostring(what) .. " (want " .. kind .. ", got " .. type(v) .. ")", 3) end
end
-- UE4SS 3.0.1 failures that pcall does not catch (C++ exceptions: the whole callback ends): recorded, the test fails.
FATAL = {}
local function hasObject(t, depth)
    if depth > 4 then return false end
    for _, v in pairs(t) do
        if type(v) == "table" then
            if v.__obj or v.__null then return true end
            if hasObject(v, depth + 1) then return true end
        end
    end
    return false
end
local function sig(kinds, f)
    return function(self, ...)
        local n = select("#", ...)
        if n ~= #kinds then error("wrong number of parameters: " .. n .. " for " .. #kinds, 2) end
        local args = { ... }
        for i, k in ipairs(kinds) do
            if type(args[i]) == "table" and not args[i].__obj and not args[i].__null and hasObject(args[i], 0) then
                table.insert(FATAL, "a struct with an object in it, parameter " .. i)
            end
            if args[i] == nil and k == "objornil" then table.insert(FATAL, "nil for an object parameter " .. i) end
            chk(args[i], k, i)
        end
        return f(self, ...)
    end
end

local nextAddr = 0x7ff600000000
local function Obj(name, methods, props)
    nextAddr = nextAddr + 0x40
    local o = { __obj = true, __valid = true, __name = name, __addr = nextAddr, __props = props or {} }
    setmetatable(o, {
        __index = function(self, k)
            if k == "IsValid" then return function(s) return s.__valid end end
            local p = rawget(self, "__props")
            if p[k] ~= nil then return p[k] end
            local m = methods[k] or (k == "GetFName" and function() return FName(name) end) or (k == "GetFullName" and function(s) return name .. "@" .. rawget(s, "__addr") end)
            if not m then
                if k:match("^[A-Z]") and not k:match("^[A-Z][a-z]*[A-Z]") then return Null() end
                return Null()
            end
            return function(s, ...)
                if not s.__valid then error("Tried calling a member function but the UObject instance is nullptr") end
                return m(s, ...)
            end
        end,
        __newindex = function(self, k, v)
            if type(k) == "string" and k:sub(1, 2) == "__" then return rawset(self, k, v) end -- (the stand-ins' own bookkeeping)
            local setters = rawget(self, "__setters")
            if not setters or not setters[k] then error("property " .. k .. " cannot be set on " .. name) end
            setters[k](self, v)
        end,
    })
    return o
end

-- ---------------------------------------------------------------------------------------------------------------
-- The world
-- ---------------------------------------------------------------------------------------------------------------
local W = { inBattle = true, held = 0.0, stickX = 0.0, stickY = 0.0, packs = {}, built = 0, viewport = {}, constructFails = false }

-- His mesh: material slots by model ("kh2": Wing; "transform": PC0010_10_Wing; "plain": none)
W.model = "kh2"
local slotNames = { kh2 = { "PC0010_00_Eye", "Sep_BodyA", "Sep_BodyB", "Wing" }, transform = { "PC0010_10_Body", "PC0010_10_Wing" }, plain = { "PC0010_00_Body" } }
W.sections = {} -- [lod][index] = shown
W.materials = {} -- [index] = material object
W.params = {} -- MID name -> value
local function resetMesh()
    W.sections = {}
    for lod = 0, 2 do
        W.sections[lod] = {}
        for i = 0, #slotNames[W.model] - 1 do W.sections[lod][i] = true end
    end
    W.materials = {}
    for i = 0, #slotNames[W.model] - 1 do W.materials[i] = Obj("MaterialInstanceConstant " .. slotNames[W.model][i + 1], {}) end
end
resetMesh()
local mids = 0
local function MID(parent)
    mids = mids + 1
    local mid = Obj("MaterialInstanceDynamic SephirothFormsWingFade_" .. mids, {
        SetScalarParameterValue = sig({ "name", "num" }, function(self, n, v)
            W.params[n:ToString()] = v
            W.paramLog = W.paramLog or {}
            table.insert(W.paramLog, v)
        end),
        SetTextureParameterValue = sig({ "name", "obj" }, function() end),
    })
    return mid
end
local mesh = Obj("SkeletalMeshComponent CharacterMesh0", {
    GetMaterialIndex = sig({ "name" }, function(self, n)
        for i, s in ipairs(slotNames[W.model]) do if s == n:ToString() then return i - 1 end end
        return -1
    end),
    GetNumLODs = sig({}, function() return 3 end),
    ShowMaterialSection = sig({ "int", "int", "bool", "int" }, function(self, index, section, visible, lod)
        assert(section == -1)
        if W.sections[lod] then W.sections[lod][index] = visible end
    end),
    IsMaterialSectionShown = sig({ "int", "int" }, function(self, index, lod) return W.sections[lod][index] end),
    GetMaterial = sig({ "int", "int" }, function(self, index, layer) assert(layer == 0); return W.materials[index] or Null() end),
    SetMaterial = sig({ "int", "int", "obj" }, function(self, index, layer, m) W.materials[index] = m end),
    K2_SetRelativeRotation = sig({ "rot", "bool", "table", "bool" }, function(self, r)
        rawget(self, "__props").RelativeRotation = { Pitch = r.Pitch, Yaw = r.Yaw, Roll = r.Roll }
        W.turns = (W.turns or 0) + 1
    end),
    CreateDynamicMaterialInstance = sig({ "int", "int", "objornil", "name" }, function(self, index, layer, source, name)
        assert(layer == 0)
        local current = W.materials[index]
        if current and current.__name:find("MaterialInstanceDynamic", 1, true) then return current end
        local mid = MID(source or current)
        W.materials[index] = mid
        W.midsMade = (W.midsMade or 0) + 1
        return mid
    end),
}, { SkeletalMesh = Obj("SkeletalMesh PC0010_00", {}), RelativeRotation = { Pitch = 0.0, Yaw = -90.0, Roll = 0.0 } })
mesh.__props.SkeletalMesh = Obj("SkeletalMesh PC0010_00", {})
mesh.__props.SkeletalMesh.__props = {}

local seph = Obj("BP_PC0000_Cloud_C Seph", {
    GetClass = function() return Obj("Class BP_PC0000_Cloud_C", { GetFName = function() return FName("BP_PC0000_Cloud_C") end }) end,
}, { Mesh = mesh })

local api = Obj("EndBattleAPI Default__EndBattleAPI", {
    GetPlayerCharacter = sig({ "int" }, function() return seph end),
    GetCharaSpecName = sig({ "obj" }, function() return FName("CharaSpec_PC0000_00_Cloud_Standard") end),
    IsInBattle = sig({}, function() return W.inBattle end),
    GetPartyLeader = sig({}, function() return seph end),
    GetCurrentAbilityID = sig({ "obj" }, function() return FName("None") end),
    SetPrimaryAnimPack = sig({ "obj", "name", "bool" }, function(self, c, p) table.insert(W.packs, p:ToString()) end),
    ResetPrimaryAnimPack = sig({ "obj" }, function() table.insert(W.packs, "reset") end),
})

local controller = Obj("BP_EndPlayerController_C PC", {
    GetInputKeyTimeDown = sig({ "key" }, function(self, k)
        assert(k.KeyName:ToString() == "Gamepad_FaceButton_Top")
        return W.held
    end),
    GetInputAnalogKeyState = sig({ "key" }, function(self, k)
        local n = k.KeyName:ToString()
        if n == "Gamepad_LeftX" then return W.stickX end
        if n == "Gamepad_LeftY" then return W.stickY end
        error("unexpected key " .. n)
    end),
})
local gameInstance = Obj("EndGameInstance GameInstance", {})
local largeFont = Obj("Font Roboto", {})
local engine = Obj("EndGameEngine Engine", {}, { LargeFont = largeFont })

-- UMG
local function umgClass(kind) return Obj("Class " .. kind, {}, { __kind = kind }) end
local classes = {
    ["/Script/UMG.UserWidget"] = umgClass("UserWidget"),
    ["/Script/UMG.WidgetTree"] = umgClass("WidgetTree"),
    ["/Script/UMG.CanvasPanel"] = umgClass("CanvasPanel"),
    ["/Script/UMG.Border"] = umgClass("Border"),
    ["/Script/UMG.TextBlock"] = umgClass("TextBlock"),
}
W.texts = {}
local function makeSlot(child)
    return Obj("CanvasPanelSlot", {
        SetAnchors = sig({ "anchors" }, function() end),
        SetAlignment = sig({ "v2" }, function() end),
        SetPosition = sig({ "v2" }, function(self, p) rawset(child, "__pos", p) end),
        SetAutoSize = sig({ "bool" }, function() end),
        SetSize = sig({ "v2" }, function() end),
    })
end
local function construct(kind, outer)
    if W.constructFails then return Null() end
    local o
    if kind == "UserWidget" then
        o = Obj("UserWidget", {
            SetVisibility = sig({ "int" }, function(self, v) self.__visibility = v end),
            AddToViewport = sig({ "int" }, function(self, z)
                assert(rawget(self, "__tree") and rawget(self, "__tree").__root, "no widget tree / root before AddToViewport")
                W.viewport[self] = true
                W.built = W.built + 1
            end),
            IsInViewport = sig({}, function(self) return W.viewport[self] == true end),
        })
        rawset(o, "__setters", { WidgetTree = function(self, v) assert(v.__obj); rawset(self, "__tree", v) end })
    elseif kind == "WidgetTree" then
        o = Obj("WidgetTree", {})
        rawset(o, "__setters", { RootWidget = function(self, v) assert(v.__obj); rawset(self, "__root", v) end })
    elseif kind == "CanvasPanel" then
        o = Obj("CanvasPanel", { AddChildToCanvas = sig({ "obj" }, function(self, child) return makeSlot(child) end) })
    elseif kind == "Border" then
        o = Obj("Border", { SetBrushColor = sig({ "color" }, function() end) })
    elseif kind == "TextBlock" then
        o = Obj("TextBlock", {
            SetText = sig({ "text" }, function(self, t) self.__props.__text = t:ToString() end),
            SetJustification = sig({ "int" }, function() end),
            SetShadowOffset = sig({ "v2" }, function() end),
            SetShadowColorAndOpacity = sig({ "color" }, function() end),
            SetColorAndOpacity = sig({ "slatecolor" }, function(self, c) self.__props.__color = c.SpecifiedColor end),
        }, { Font = { FontObject = Null(), Size = 24 } })
        table.insert(W.texts, o)
    end
    return o
end

local function UFunction(names)
    return Obj("Function", {
        ForEachProperty = function(self, fn)
            for _, n in ipairs(names) do
                if fn(Obj("Property " .. n, { GetFName = function() return FName(n) end })) == true then break end
            end
        end,
    })
end
local functions = {
    ["/Script/Engine.PrimitiveComponent:GetMaterial"] = UFunction({ "ElementIndex", "LayerIndex", "ReturnValue" }),
    ["/Script/Engine.PrimitiveComponent:SetMaterial"] = UFunction({ "ElementIndex", "LayerIndex", "Material" }),
    ["/Script/Engine.PrimitiveComponent:CreateDynamicMaterialInstance"] = UFunction({ "ElementIndex", "LayerIndex", "SourceMaterial", "OptionalName", "ReturnValue" }),
    ["/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue"] = UFunction({ "ParameterName", "Value" }),
}
function StaticFindObject(path)
    if functions[path] then return functions[path] end
    if path == "/Script/EndGame.Default__EndBattleAPI" then return api end
    if classes[path] then return classes[path] end
    return Null()
end
function StaticConstructObject(class, outer, ...)
    assert(select("#", ...) == 0, "the menu names nothing")
    chk(class, "obj", "class"); chk(outer, "obj", "outer")
    return construct(class.__props.__kind, outer)
end
function FindFirstOf(name)
    if name == "PlayerController" then return controller end
    if name == "GameInstance" then return gameInstance end
    if name == "Engine" then return engine end
    return Null()
end
function FindAllOf() return {} end
function LoadAsset() return Null() end
function NotifyOnNewObject() end
Key = setmetatable({}, { __index = function(_, k) return k end })
local keybinds = {}
function RegisterKeyBind(key, fn) keybinds[key] = fn end

local loops, queue, inGame = {}, {}, false
function LoopAsync(ms, fn) table.insert(loops, { ms = ms, fn = fn, next = 0 }) end
function ExecuteInGameThread(fn)
    if inGame then error("ExecuteInGameThread from inside a game-thread action (UE4SS 3.0.1 would crash)") end
    table.insert(queue, fn)
end

local now = 0
local function run(ms)
    local stop = now + ms
    while now < stop do
        now = now + 10
        clock = clock + 0.01
        if W.held > 0 then W.held = W.held + 0.01 end
        for _, loop in ipairs(loops) do
            if now >= loop.next then
                loop.next = now + loop.ms
                loop.fn()
            end
        end
        local q = queue
        queue = {}
        inGame = true
        for _, fn in ipairs(q) do fn() end
        inGame = false
    end
end

-- ---------------------------------------------------------------------------------------------------------------
dofile(SCRIPTS .. "main.lua")
assert(found("SephirothForms ready (hold Triangle 0.35 s in battle: the moveset menu"), "ready line names the menu")
assert(found("slot PC0010_10_Wing / Wing, fading 0.6 s"), "ready line names both slots and the fade")

local function wingShownAll(index)
    for lod = 0, 2 do if not W.sections[lod][index] then return false end end
    return true
end
local function wingHiddenAll(index)
    for lod = 0, 2 do if W.sections[lod][index] then return false end end
    return true
end
local function textOf(name)
    for _, t in ipairs(W.texts) do if t.__props.__text and t.__props.__text:find(name, 1, true) then return t end end
end

run(500)
assert(found("watching BP_PC0000_Cloud_C Seph"), "tracks him")
assert(wingHiddenAll(3), "KH2 model: his normal form hides the Wing slot")
assert(found("wing hidden (section, slot Wing)"), "the log names the KH2 model's slot")

-- 1: a tap does nothing
W.held = 0.01; run(200); W.held = 0; run(200)
assert(not found("menu open"), "a tap opens no menu")

-- 2: hold: the menu; stick down: KH2; let go: KH2 pack, wing fades in
W.held = 0.01; run(500)
assert(found("menu built"), "menu built")
assert(found("menu open (Triangle held"), "menu open")
assert(W.built == 1)
local kh2 = textOf("KH2")
local normal = textOf("NORMAL")
assert(kh2 and normal, "the forms are on the menu")
assert(normal.__props.__text == "NORMAL  (now)", "his form is marked: " .. tostring(normal.__props.__text))
assert(normal.__props.Font.FontObject == largeFont and normal.__props.Font.Size == 36, "the engine's font at 36, written into Font")
W.stickY = -0.9; run(150)
assert(kh2.__props.__color.R == 1.0 and kh2.__props.__color.B == 0.30, "KH2 lit")
W.stickY = 0.0; run(150) -- (the stick back in the middle: KH2 stays lit)
assert(kh2.__props.__color.B == 0.30, "KH2 still lit")
W.held = 0; run(100)
assert(W.packs[#W.packs] == "Battle04", "KH2 pack: " .. tostring(W.packs[#W.packs]))
assert(found("stage KH2 (moveset menu)"))
assert(wingShownAll(3), "the wing is out at once (fading in)")
assert(W.params.NativePrimitiveCoverage ~= nil and W.params.NativePrimitiveCoverage < 0.5, "starts faded")
run(700)
assert(W.params.NativePrimitiveCoverage == 1.0, "fully in after 0.6 s: " .. tostring(W.params.NativePrimitiveCoverage))
assert(W.midsMade == 1, "one copy of the wing's material")
assert(found("wing out (section, slot Wing, fading 0.6 s)"))
assert(mesh.__props.RelativeRotation.Yaw == 90.0, "KH2: his model turned 180 (from -90): " .. tostring(mesh.__props.RelativeRotation.Yaw))
assert(found("his model turned 180 degrees for the KH2 moves (yaw -90 -> 90)"))
assert(found("stage KH2 (moveset menu)") and found("menu open"), "KH2 recorded")
-- the game resets his model's turn: it comes back
mesh.__props.RelativeRotation = { Pitch = 0.0, Yaw = -90.0, Roll = 0.0 }
run(400)
assert(mesh.__props.RelativeRotation.Yaw == 90.0 and found("(again: the game had reset it)"), "turn kept")
-- F2: another 90
keybinds["F2"](); run(100)
assert(mesh.__props.RelativeRotation.Yaw == 180.0, "F2 turned it to 270 from his own: " .. tostring(mesh.__props.RelativeRotation.Yaw))
keybinds["F2"](); keybinds["F2"](); keybinds["F2"](); run(100)
assert(mesh.__props.RelativeRotation.Yaw == 90.0, "back to 180 after four presses")

-- 3: hold, stick left: normal; let go: reset, the wing fades out, then the section hides
W.held = 0.01; run(500)
assert(textOf("KH2").__props.__text == "KH2  (now)", "KH2 marked now")
W.stickX = -1.0; run(100); W.stickX = 0.0
W.held = 0; run(100)
assert(W.packs[#W.packs] == "reset", "normal: pack reset")
assert(mesh.__props.RelativeRotation.Yaw == -90.0, "his model's own turn back: " .. tostring(mesh.__props.RelativeRotation.Yaw))
assert(wingShownAll(3), "still drawn while it fades out")
local mid = W.params.NativePrimitiveCoverage
run(300)
assert(W.params.NativePrimitiveCoverage < mid, "fading out")
run(500)
assert(W.params.NativePrimitiveCoverage == 0.0, "faded out")
assert(wingHiddenAll(3), "hidden when the fade is done")
assert(W.midsMade == 1, "the same copy of the material")
assert(W.built == 1, "the menu is reused")
run(1000)
assert(count("wing hidden again") == 0, "no reset fights the fade")

-- 4: hold and let go without the stick: nothing
local packs = #W.packs
W.held = 0.01; run(500); W.held = 0; run(100)
assert(#W.packs == packs, "no switch")
assert(found("menu: nothing chosen, no switch"))

-- 5: winged (stick up), then flying (right) on the transformed model (slot PC0010_10_Wing)
W.model = "transform"; resetMesh()
run(300)
W.held = 0.01; run(450); W.stickY = 0.8; run(100); W.stickY = 0; W.held = 0; run(100)
assert(W.packs[#W.packs] == "Battle02", "winged")
run(700)
assert(wingShownAll(1), "transform model: PC0010_10_Wing out")
assert(found("wing out (section, slot PC0010_10_Wing, fading 0.6 s)"))
W.held = 0.01; run(450); W.stickX = 0.7; run(100); W.stickX = 0; W.held = 0; run(100)
assert(W.packs[#W.packs] == "Battle03", "flying")
assert(wingShownAll(1), "the wing stays out (winged -> flying)")

-- 6: the menu closes when the battle ends while it is up
W.held = 0.01; run(450)
W.inBattle = false; run(300)
assert(found("menu closed (not in battle, or you control someone else)"), "closed at the battle's end")
W.held = 0; run(300)
assert(W.packs[#W.packs] == "reset", "the battle's end puts him back")
W.inBattle = true; run(300)

-- 7: a map load took the menu off the screen: built again
W.viewport = {}
W.held = 0.01; run(450); W.held = 0; run(100)
assert(W.built == 2, "built again")

-- 8: no wing on the model: one line, no error
W.model = "plain"; resetMesh()
W.held = 0.01; run(450); W.stickY = -1; run(100); W.stickY = 0; W.held = 0; run(300)
assert(found("wing: no PC0010_10_Wing / Wing material slot"), "names both slots")

assert(#FATAL == 0, "UE4SS would have ended the callback: " .. table.concat(FATAL, "; "))
print("ALL MENU TESTS PASSED (" .. #logs .. " log lines)")
