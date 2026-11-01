-- UI/NameText.lua: one name the client shows by itself (an item, a spell or skill, a zone, a faction), in Italian.
-- The rows are Blizzard's official names (Names/, keyed by the hash of the English, `make surface-names`).
-- Each kind is its own area, so the player chooses kind by kind (Core/Settings, area.name*), and the reveal key and the
-- master switch work as for any other text: everything goes through Render.
-- Never on the spellbook's rows: a FontString this addon writes there taints the action bars (UI/SpellBook, ADR-058).
local _, WFJ = ...
local NameText = {}
WFJ.NameText = NameText

function NameText.key(en)
  return WFJ.Hash.key(WFJ.Normalize.v1(en))
end

local function secret(value)
  local isSecret = WFJ.Compat.resolve("issecretvalue")
  return type(isSecret) == "function" and isSecret(value) and true or false
end

-- `fs` as record `recKey` of `surface`, if its text is a name of `kind`. `refit` (optional) lays its owner out again.
-- → 1 when it holds a name (shown, or still ours), else 0 and an earlier record is dropped: never restored
function NameText.show(surface, recKey, fs, kind, refit)
  if type(fs) ~= "table" or type(fs.GetText) ~= "function" then return 0 end
  local en = fs:GetText()
  if secret(en) then
    WFJ.SurfaceState.drop(surface, recKey)
    return 0
  end
  local rec = WFJ.SurfaceState.get(surface, recKey)
  if rec and rec.fs == fs and rec.applied ~= nil and en == rec.applied then return 1 end
  local key = type(en) == "string" and en ~= "" and NameText.key(en) or nil
  if not key or not WFJ.Lookup.keyed(kind, key) then
    WFJ.SurfaceState.drop(surface, recKey)
    return 0
  end
  WFJ.Render.show(surface, recKey, fs, en, kind, kind, key, { refit = refit, compact = true })
  return 1
end
