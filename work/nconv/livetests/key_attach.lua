-- the player's Kingdom Key (a SkeletalMeshComponent with WE0000_00 in the game world, visible), its socket frames,
-- and (args.play) the KH3 summon effect attached at its C_Body_a socket, replayed every args.every seconds
local args = ... or {}
local function weapon()
  local found, all = nil, {}
  for _, c in ipairs(FindAllOf("SkeletalMeshComponent") or {}) do
    if link.valid(c) then
      local okm, m = pcall(function() return c.SkeletalMesh end)
      local mn = okm and link.fullName(m) or ""
      local cn = link.fullName(c) or ""
      if mn:find("WE0000_00") and not cn:find("MenuRendering") then
        local okv, vis = pcall(function() return c:IsVisible() end)
        all[#all + 1] = { cn, okv and vis or false }
        if okv and vis and found == nil then found = c end
      end
    end
  end
  return found, all
end
link.state.kh3_weapon = weapon
local w, all = weapon()
local out = { candidates = all }
if w then
  local function v3(t) return { t.X, t.Y, t.Z } end
  local okc, cs = pcall(function() return v3(w:K2_GetComponentScale()) end)
  out.component_world_scale = okc and cs or tostring(cs)
  local okr, rs = pcall(function() return v3(w.RelativeScale3D) end)
  out.component_relative_scale = okr and rs or tostring(rs)
  out.sockets = {}
  for _, sn in ipairs({ "C_Body_a", "C_Body_End", "C_TrailA_a", "C_TrailA_b", "C_CharaA_a" }) do
    local ok, row = pcall(function()
      local t = w:GetSocketTransform(FName(sn), 0)
      local r = w:GetSocketRotation(FName(sn))
      return { sn, scale = v3(t.Scale3D), loc = v3(t.Translation), rot = { r.Pitch, r.Yaw, r.Roll } }
    end)
    out.sockets[#out.sockets + 1] = ok and row or { sn, tostring(row) }
  end
  local okq, cr = pcall(function() local r = w:K2_GetComponentRotation(); return { r.Pitch, r.Yaw, r.Roll } end)
  out.component_rotation = okq and cr or tostring(cr)
end
if args.play then
  local path = args.path or "/Game/KH3/RebirthFX/FX_SO010_APP0_Local.FX_SO010_APP0_Local"
  local socket = args.socket or "C_Body_a"
  local world_scale = args.world_scale or 1.0
  local function play()
    local sys = link.load(path)
    if not link.valid(sys) then return "loading" end
    local c = link.state.kh3_weapon()
    if not c then return "no visible keyblade" end
    local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
    local comp = lib:SpawnSystemAttached(sys, c, FName(socket), { X = 0.0, Y = 0.0, Z = 0.0 },
      { Pitch = args.pitch or 0.0, Yaw = args.yaw or 0.0, Roll = args.roll or 0.0 }, 2, true, true, 0, false)
    if link.valid(comp) and world_scale > 0 then comp:SetWorldScale3D({ X = world_scale, Y = world_scale, Z = world_scale }) end
    return link.valid(comp) and "spawned" or "not spawned"
  end
  out.first = play()
  link.cancel("kh3_key")
  link.every("kh3_key", function() play() end, args.every or 3.0)
  out.looping = true
end
if args.stop then out.cancelled = link.cancel("kh3_key") end
return out
