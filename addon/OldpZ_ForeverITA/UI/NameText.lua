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

-- The ways a line can hold a name: the whole text, then without a colour code around it, then also without a count
-- before it ("3/5 " or "5 ", a reagent slot). → list of { before, words, after }
local function readings(text)
  local list = { { "", text, "" } }
  local before, rest, after = "", text, ""
  local code, inner = text:match("^(|c%x%x%x%x%x%x%x%x)(.*)$")
  if code then
    before, rest = code, inner
    local body = rest:match("^(.*)|r$")
    if body then rest, after = body, "|r" end
    list[#list + 1] = { before, rest, after }
  end
  local count, words = rest:match("^(%d+/%d+ )(.+)$")
  if not count then count, words = rest:match("^(%d+ )(.+)$") end
  if count then list[#list + 1] = { before .. count, words, after } end
  return list
end

-- The name `text` holds, of `kind` (a kind, or a list tried in order: the kind that knows the name is its area).
-- → kind, key, before, after (what the line shows around the name) | nil
function NameText.match(text, kind)
  local keyed = WFJ.Lookup and WFJ.Lookup.keyed
  if type(keyed) ~= "function" or type(text) ~= "string" or text == "" or secret(text) then return nil end
  local kinds = type(kind) == "table" and kind or { kind }
  for _, r in ipairs(readings(text)) do
    local key = NameText.key(r[2])
    for _, k in ipairs(kinds) do
      if keyed(k, key) then return k, key, r[1], r[3] end
    end
  end
  return nil
end

-- `fs` as record `recKey` of `surface`, if its text is a name of `kind` (a kind, or a list tried in order: the kind
-- that knows the name is its area). A colour code and a count around the name are kept. `refit` (optional) lays its
-- owner out again.
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
  local k, key, before, after = NameText.match(en, kind)
  if k then
    local wrap = (before ~= "" or after ~= "") and { before, after } or nil
    WFJ.Render.show(surface, recKey, fs, en, k, k, key, { refit = refit, compact = true, wrap = wrap })
    return 1
  end
  WFJ.SurfaceState.drop(surface, recKey)
  return 0
end
