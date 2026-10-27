return { seq = 1793055661100, op = "lua", name = "voice_langs", code = [==[
  local out = { langs = {}, examples = {}, packages = {} }
  local sounds = FindAllOf("SQEXSEADSound") or {}
  for _, s in ipairs(sounds) do
    local ok, n = pcall(function() return s:GetFullName() end)
    if ok and n then
      local lang = n:match("/Game/Sound/Voice/(%w+)/")
      if lang then
        out.langs[lang] = (out.langs[lang] or 0) + 1
        if not out.examples[lang] then out.examples[lang] = n end
      end
    end
  end
  local pk = FindAllOf("Package") or {}
  out.package_total = #pk
  local n = 0
  for _, p in ipairs(pk) do
    local ok, nm = pcall(function() return p:GetFullName() end)
    if ok and nm and nm:find("/Game/Sound/Voice/") and nm:find("PC0000") then
      n = n + 1
      if n <= 20 then out.packages[#out.packages + 1] = nm end
    end
  end
  return out
]==] }
