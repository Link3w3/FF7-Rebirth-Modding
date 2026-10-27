-- FormMenu.lua: the moveset menu of SephirothForms (main.lua opens it, picks with it and closes it).
--   Hold Triangle in battle: a command window like the game's own shows his forms, one row each, the one he is in
--   marked with a blue square. Each row has the way to tilt the left stick for it (its chevron); tilt the stick and that
--   row lights up (the game's blue command bar and cursor), then let go of Triangle: he switches to it. Let go without
--   lighting one up: nothing changes.
--   Made of the engine's own widgets (UMG: a canvas, images, text) drawn with the game's command menu art (the Paper2D
--   sprites of /Game/Menu/Resident/Texture: the window, the rows, the blue bar, the chevrons), built the first time it
--   opens and kept on screen hidden between uses (built again after a map load, which takes widgets off the screen). A
--   piece whose art is not loaded is drawn plain instead (a dark or blue panel), so the menu always works.
--   It never takes input: the game keeps every button.
local M = {}

local log = function() end
local valid = function(object) return object ~= nil end
local load = function(path) return StaticFindObject(path) end

local CLASSES = {
    UserWidget = "/Script/UMG.UserWidget",
    WidgetTree = "/Script/UMG.WidgetTree",
    CanvasPanel = "/Script/UMG.CanvasPanel",
    Border = "/Script/UMG.Border",
    Image = "/Script/UMG.Image",
    TextBlock = "/Script/UMG.TextBlock",
}

-- The game's command menu art (Paper2D sprites; size in pixels at 1080p).
local ART = "/Game/Menu/Resident/Texture/"
local SPRITES = {
    window = { "U_Command_Base_11", 365, 202 },    -- the command window (misty dark, a blue glow at the top)
    row = { "U_Command_BtnBase_06", 365, 41 },     -- a command row (dark, a notch at its left)
    lit = { "U_Command_Base_03", 326, 41 },        -- the blue bar of the chosen command
    accent = { "U_Command_Header_02", 4, 30 },     -- the header's bright line
    chevron = { "U_Command_Arrow_01", 20, 13 },    -- a chevron pointing up (turned for each stick direction)
    cursor = { "U_TargetCursor_Arrow_00", 32, 35 }, -- the double chevron cursor (points down; turned to point at the row)
    now = { "U_Command_BtnBase_08", 14, 14 },      -- a blue square: the form he is in
}
M.SPRITE_PATHS = {}
for _, sprite in pairs(SPRITES) do table.insert(M.SPRITE_PATHS, ART .. sprite[1] .. "." .. sprite[1]) end

-- ESlateVisibility
local VISIBLE, COLLAPSED, HIDDEN, HIT_TEST_INVISIBLE = 0, 1, 2, 3

local SCALE = 1.2                 -- the art at 1.2 times its size
local LOOK = {
    plain = { R = 0.80, G = 0.82, B = 0.86, A = 1.0 },
    now = { R = 0.55, G = 0.82, B = 1.0, A = 1.0 },     -- the form he is in
    lit = { R = 1.0, G = 1.0, B = 1.0, A = 1.0 },       -- the form the stick points at
    title = { R = 0.92, G = 0.95, B = 1.0, A = 1.0 },
    hint = { R = 0.78, G = 0.80, B = 0.84, A = 0.95 },
    windowPlain = { R = 0.02, G = 0.03, B = 0.06, A = 0.78 }, -- the plain pieces (art not loaded)
    rowPlain = { R = 0.10, G = 0.11, B = 0.13, A = 0.85 },
    litPlain = { R = 0.10, G = 0.42, B = 0.85, A = 0.95 },
    rowTint = { R = 1.0, G = 1.0, B = 1.0, A = 0.92 },
    optionSize = 26,
    titleSize = 22,
    hintSize = 17,
    zOrder = 60,
}
-- The rows top to bottom by the stick's way, and each way's chevron turn (it points up).
local WAYS = { "up", "left", "right", "down" }
local TURN = { up = 0.0, right = 90.0, down = 180.0, left = -90.0 }

local ui = nil      -- { widget, rows = { [form] = { text, lit, now, y } }, cursor, shown = { [form] = key } }
local broken = nil  -- why the menu could not be built (not tried again this session)
local names = {}    -- form -> its name on the menu
local sticks = {}   -- form -> "up"/"right"/"down"/"left"

local function newObject(kind, outer)
    local class = StaticFindObject(CLASSES[kind])
    if not valid(class) then error(kind .. " class not found") end
    local object = StaticConstructObject(class, outer)
    if not valid(object) then error("the engine made no " .. kind) end
    return object
end

-- A child of the canvas centred on (x, y) from the middle of the screen (align: its point there, 0..1 each way), at a
-- fixed size (else its own).
local function place(slot, x, y, size, align)
    if not valid(slot) then error("the canvas gave no slot") end
    slot:SetAnchors({ Minimum = { X = 0.5, Y = 0.5 }, Maximum = { X = 0.5, Y = 0.5 } })
    slot:SetAlignment(align or { X = 0.5, Y = 0.5 })
    slot:SetPosition({ X = x, Y = y })
    if size then
        slot:SetAutoSize(false)
        slot:SetSize(size)
    else
        slot:SetAutoSize(true)
    end
    return slot
end

-- The game's sprite (found loaded, else loaded), or nil.
local found = {}
local function sprite(key)
    if found[key] and valid(found[key]) then return found[key] end
    local path = ART .. SPRITES[key][1] .. "." .. SPRITES[key][1]
    local ok, object = pcall(load, path)
    found[key] = (ok and valid(object)) and object or nil
    return found[key]
end

-- An image of a sprite at its size times SCALE (w, h: another size), or a plain panel in `plain` when the sprite is not
-- there (nil: nothing). Returns the widget and its slot.
local art = { drawn = 0, plain = 0 }
local function newArt(tree, canvas, key, x, y, w, h, plain, align)
    local width, height = w or SPRITES[key][2] * SCALE, h or SPRITES[key][3] * SCALE
    local object = sprite(key)
    local widget
    if object then
        widget = newObject("Image", tree)
        local ok = pcall(function() widget:SetBrushResourceObject(object) end)
        if not ok then ok = pcall(function() widget.Brush.ResourceObject = object end) end
        pcall(function() widget:SetBrushSize({ X = width, Y = height }) end)
        if ok then
            art.drawn = art.drawn + 1
        else
            -- (an image with no art draws white: tinted to the plain colour)
            pcall(function() widget:SetColorAndOpacity(plain or { R = 0.0, G = 0.0, B = 0.0, A = 0.0 }) end)
            art.plain = art.plain + 1
        end
    elseif plain then
        widget = newObject("Border", tree)
        widget:SetBrushColor(plain)
        art.plain = art.plain + 1
    else
        art.plain = art.plain + 1
        return nil, nil
    end
    local slot = place(canvas:AddChildToCanvas(widget), x, y, { X = width, Y = height }, align)
    return widget, slot
end

-- Text in the engine's font (Roboto) bold with a dark outline, the size given. Written straight into the text block's
-- Font before it is on screen (the engine takes it when it builds the text): UE4SS 3.0.1 cannot pass a struct with an
-- object in it (SetFont's FSlateFontInfo) from Lua, and that error is not one pcall catches.
local fontObject = nil
local function setFont(text, size)
    local own = nil
    pcall(function() own = text.Font.FontObject end)
    if not valid(own) then
        if not valid(fontObject) then
            local engine = FindFirstOf("Engine")
            if valid(engine) then
                for _, which in ipairs({ "LargeFont", "MediumFont", "SubtitleFont", "SmallFont" }) do
                    local ok, font = pcall(function() return engine[which] end)
                    if ok and valid(font) then
                        fontObject = font
                        break
                    end
                end
            end
        end
        if valid(fontObject) then pcall(function() text.Font.FontObject = fontObject end) end
    end
    pcall(function() text.Font.Size = size end)
    pcall(function() text.Font.TypefaceFontName = FName("Bold") end)
    pcall(function() text.Font.OutlineSettings.OutlineSize = 1 end) -- (its colour: black, the engine's)
end

local function setColor(text, color)
    text:SetColorAndOpacity({ SpecifiedColor = color, ColorUseRule = 0 })
end

-- justify: 0 left, 1 centre; align: the text's point at (x, y).
local function newText(tree, canvas, words, size, color, x, y, justify, align)
    local text = newObject("TextBlock", tree)
    text:SetText(FText(words))
    setFont(text, size)
    pcall(function() text:SetJustification(justify or 1) end)
    pcall(function() text:SetShadowOffset({ X = 1.5, Y = 1.5 }) end)
    pcall(function() text:SetShadowColorAndOpacity({ R = 0.0, G = 0.0, B = 0.0, A = 0.75 }) end)
    setColor(text, color)
    place(canvas:AddChildToCanvas(text), x, y, nil, align)
    return text
end

local function show(widget, on)
    if valid(widget) then pcall(function() widget:SetVisibility(on and HIT_TEST_INVISIBLE or HIDDEN) end) end
end

local function build()
    local owner = FindFirstOf("GameInstance")
    if not valid(owner) then owner = FindFirstOf("PlayerController") end
    if not valid(owner) then error("no game instance to own it") end
    art.drawn, art.plain = 0, 0
    local widget = newObject("UserWidget", owner)
    local tree = newObject("WidgetTree", widget)
    widget.WidgetTree = tree
    local canvas = newObject("CanvasPanel", tree)
    tree.RootWidget = canvas

    local W, H = SPRITES.window[2] * SCALE, SPRITES.window[3] * SCALE
    local left, top = -W / 2, -H / 2
    local headerH = 39 * SCALE
    local rowH = SPRITES.row[3] * SCALE
    newArt(tree, canvas, "window", 0.0, 0.0, W, H, LOOK.windowPlain)
    local accentX = left + 16 * SCALE
    local headerY = top + headerH / 2 + 4
    newArt(tree, canvas, "accent", accentX, headerY, nil, nil, nil)
    newText(tree, canvas, "MOVESET", LOOK.titleSize, LOOK.title, accentX + 12 * SCALE, headerY, 0, { X = 0.0, Y = 0.5 })

    local made = { widget = widget, rows = {}, shown = {} }
    local row = 0
    for _, way in ipairs(WAYS) do
        local form = nil
        for f, w in pairs(sticks) do if w == way then form = f end end
        if form ~= nil then
            local y = top + headerH + rowH * row + rowH / 2
            row = row + 1
            local bar = newArt(tree, canvas, "row", 0.0, y, W, rowH, LOOK.rowPlain)
            if valid(bar) and sprite("row") then pcall(function() bar:SetColorAndOpacity(LOOK.rowTint) end) end
            local litW = SPRITES.lit[2] * SCALE
            local lit = newArt(tree, canvas, "lit", left + W - litW / 2, y, litW, rowH - 2, LOOK.litPlain)
            local now = newArt(tree, canvas, "now", left + 20 * SCALE, y, nil, nil, LOOK.now)
            local text = newText(tree, canvas, names[form] or tostring(form), LOOK.optionSize, LOOK.plain, left + 52 * SCALE, y, 0, { X = 0.0, Y = 0.5 })
            local chevron = newArt(tree, canvas, "chevron", left + W - 26 * SCALE, y, nil, nil, nil)
            if valid(chevron) then pcall(function() chevron:SetRenderTransformAngle(TURN[way]) end) end
            show(lit, false)
            show(now, false)
            made.rows[form] = { text = text, lit = lit, now = now, y = y }
        end
    end
    -- the cursor: the double chevron turned to point right, at the left of the lit row
    local cursor, cursorSlot = newArt(tree, canvas, "cursor", left - 14 * SCALE, 0.0, nil, nil, nil)
    if valid(cursor) then pcall(function() cursor:SetRenderTransformAngle(-90.0) end) end
    made.cursor, made.cursorSlot, made.cursorX = cursor, cursorSlot, left - 14 * SCALE
    show(cursor, false)
    newText(tree, canvas, "Left stick: choose        Let go of Triangle: switch", LOOK.hintSize, LOOK.hint, 0.0, H / 2 + 24, 1)

    widget:SetVisibility(COLLAPSED)
    widget:AddToViewport(LOOK.zOrder)
    log(string.format("menu built (%d pieces with the game's command menu art%s)", art.drawn,
        art.plain > 0 and string.format(", %d drawn plain: art not loaded", art.plain) or ""))
    return made
end

local function onScreen(made)
    if not made or not valid(made.widget) then return false end
    local ok, inViewport = pcall(function() return made.widget:IsInViewport() end)
    return ok and inViewport == true
end

-- env: { log, valid, load (path -> object or nil) }; options: { names = { [form] = name }, sticks = { [form] = way } }
function M.init(env, options)
    log = env.log or log
    valid = env.valid or valid
    load = env.load or load
    names = options.names or names
    sticks = options.sticks or sticks
end

-- Shows the menu: `current` is the form he is in, `lit` the one the stick points at (nil: none). Returns true when shown.
function M.open(current, lit)
    if broken then return false end
    if not onScreen(ui) then
        local ok, made = pcall(build)
        if not ok then
            broken = tostring(made)
            log("menu could not be built: " .. broken .. " (holding Triangle switches to the next form instead)")
            return false
        end
        ui = made
    end
    ui.shown = {}
    ui.cursorShownAt = nil
    M.update(current, lit)
    local ok, err = pcall(function() ui.widget:SetVisibility(HIT_TEST_INVISIBLE) end)
    if not ok then
        log("menu could not be shown: " .. tostring(err))
        return false
    end
    return true
end

-- The rows: the lit one on the blue bar with the cursor at it, his own with the blue square; colours to match.
function M.update(current, lit)
    if not ui then return end
    for form, row in pairs(ui.rows) do
        local look = (form == lit) and "lit" or ((form == current) and "now" or "plain")
        local key = look .. (form == current and "*" or "")
        if ui.shown[form] ~= key then
            ui.shown[form] = key
            pcall(function()
                show(row.lit, form == lit)
                show(row.now, form == current)
                if valid(row.text) then setColor(row.text, LOOK[look]) end
            end)
        end
    end
    local row = lit ~= nil and ui.rows[lit] or nil
    if ui.cursorShownAt ~= (row and row.y or false) then
        ui.cursorShownAt = row and row.y or false
        pcall(function()
            if row and valid(ui.cursorSlot) then ui.cursorSlot:SetPosition({ X = ui.cursorX, Y = row.y }) end
            show(ui.cursor, row ~= nil)
        end)
    end
end

function M.close()
    if ui and valid(ui.widget) then pcall(function() ui.widget:SetVisibility(COLLAPSED) end) end
end

function M.problem() return broken end

return M
