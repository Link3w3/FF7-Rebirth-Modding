-- what Sora's mesh is animating with right now: the anim instance (and the skeleton it was made for), the montage, the
-- linked instances, and what the character is attached to (a mount)
local out = {}
local pawn = link.player()
if not pawn then return "no player" end
local m = pawn.Mesh
local function s(f) local ok, v = pcall(f); if ok then return v end return "ERR " .. tostring(v) end
out.pawn = link.fullName(pawn)
out.mesh_asset = s(function() return link.fullName(m.SkeletalMesh) end)
local ai = s(function() return m:GetAnimInstance() end)
out.anim_instance = type(ai) == "string" and ai or link.fullName(ai)
if type(ai) ~= "string" and link.valid(ai) then
  out.anim_class = s(function() return link.fullName(ai:GetClass()) end)
  out.montage = s(function() local mo = ai:GetCurrentActiveMontage(); return link.valid(mo) and link.fullName(mo) or "none" end)
  out.target_skeleton = s(function() return link.fullName(ai:GetClass().TargetSkeleton) end)
end
out.anim_mode = s(function() return m.AnimationMode end)
out.anim_class_prop = s(function() return link.fullName(m.AnimClass) end)
out.attach_parent = s(function() local p = pawn:GetAttachParentActor(); return link.valid(p) and link.fullName(p) or "none" end)
out.mesh_parent = s(function() local p = m:GetAttachParent(); return link.valid(p) and link.fullName(p) or "none" end)
out.movement_mode = s(function() return pawn.CharacterMovement.MovementMode end)
-- every anim instance whose outer is the player's mesh (linked layers, sub instances)
local subs = {}
local key = (link.fullName(pawn) or ""):match("^%S+ (.+)$") or "?"
for _, o in ipairs(FindAllOf("AnimInstance") or {}) do
  if link.valid(o) then
    local n = link.fullName(o) or ""
    if n:find(key, 1, true) then subs[#subs + 1] = n end
  end
end
out.anim_instances_on_player = subs
return out
