-- Core/UnitNames.lua: an NPC's Italian name (or subname) from its GUID, for the unit tooltip, the target frames
-- and the nameplates (UI surfaces). Pure lookup over Core/Lookup's `unit` rows.
--   UnitNames.name(guid, shown)    → Italian name | nil     shown = the English the client shows for that unit
--   UnitNames.subname(guid, shown) → Italian subname | nil
--   UnitNames.forUnit(unit, shown) → UnitNames.name(UnitGUID(unit), shown)
--   UnitNames.reset()              drops the cache (fired on the "names" State event; safe on a data reload)
-- nil always means "leave the shown text as it is". An answer needs, in order: `names.style` = "it"; a guid and a
-- shown text that are not secret values (issecretvalue, resolved through Compat: never compared, never used as a
-- key); a Creature- or Vehicle- GUID (Collector.creatureId: players, pets and objects give nil); a shipped row
-- with an Italian string (a kept-English "e" slot has none); and the shown English hashing to the row's h1:
-- Hash.h32x2(Normalize.v1(shown)), the same canon as the pipeline's `normalize_for("unit", en)` + hash (vectors
-- unit-01). Another English on the same creature id (a Forever rename) keeps its own text.
-- Never: touches a frame, decides the reveal key (Alt shows the English through Translator/Render, ADR-018), or
-- writes to WFJ.Data. The cache is keyed by field, GUID and shown text and is reset past CACHE_MAX entries.
local _, WFJ = ...
local UnitNames = {}
WFJ.UnitNames = UnitNames

UnitNames.CACHE_MAX = 256

local cache, count = {}, 0 -- [field \0 guid \0 shown] = Italian | false

function UnitNames.reset()
  cache, count = {}, 0
end

function UnitNames.cacheSize()
  return count
end

local function secret(v)
  local isSecret = WFJ.Compat.resolve("issecretvalue")
  return type(isSecret) == "function" and isSecret(v) and true or false
end

-- A creature name the shipped data has no row for (a mob Forever added: it is in no table the pipeline reads, the
-- server sends it) or whose English is not the row's (a Forever rename) goes to the collector as an "npc" line, so the
-- next send brings it in for translation. A kept-English row with its own English is never recorded. Once per
-- creature and text: the answer cache below holds the miss. A creature a player controls (a summoned demon, a
-- hunter's pet) is never recorded: its shown name can be the one its owner gave it ("Makgrave" on a Voidwalker),
-- and on this client such a pet can carry a Creature- GUID.
local function controlled(guid)
  local fromGUID = WFJ.Compat.resolve("UnitTokenFromGUID")
  local isControlled = WFJ.Compat.resolve("UnitPlayerControlled")
  if type(fromGUID) ~= "function" or type(isControlled) ~= "function" then return false end
  local ok, token = pcall(fromGUID, guid)
  if not ok or type(token) ~= "string" or secret(token) then return false end
  local okC, yes = pcall(isControlled, token)
  return okC and not secret(yes) and yes == true
end

-- the client's placeholder for a creature whose name has not arrived yet (UNKNOWNOBJECT): never a name to translate
local function placeholder(shown)
  local unknown = WFJ.Compat.resolve("UNKNOWNOBJECT")
  return shown == "Unknown" or (type(unknown) == "string" and not secret(unknown) and shown == unknown)
end

local function recordMiss(field, id, entry, shown, guid)
  if field ~= "name" then return end
  if placeholder(shown) or controlled(guid) then return end
  if entry ~= nil and (entry.h1 == nil or WFJ.Hash.h32x2(WFJ.Normalize.v1(shown)) == entry.h1) then return end
  WFJ.Collector.record("npc", id, "name", shown)
end

local function compute(field, guid, shown)
  local id = WFJ.Collector.creatureId(guid)
  if id == nil then return nil end
  local entry = WFJ.Lookup.get("unit." .. field, id)
  recordMiss(field, id, entry, shown, guid)
  if entry == nil or type(entry.ja) ~= "string" or entry.ja == "" or entry.h1 == nil then return nil end
  if WFJ.Hash.h32x2(WFJ.Normalize.v1(shown)) ~= entry.h1 then return nil end
  return entry.ja
end

local function answer(field, guid, shown)
  if WFJ.Names and WFJ.Names.style() == "en" then return nil end
  if secret(guid) or secret(shown) then return nil end
  if type(guid) ~= "string" or type(shown) ~= "string" or shown == "" then return nil end
  local key = field .. "\0" .. guid .. "\0" .. shown
  local hit = cache[key]
  if hit ~= nil then return hit or nil end
  local ja = compute(field, guid, shown)
  if count >= UnitNames.CACHE_MAX then UnitNames.reset() end
  cache[key], count = ja or false, count + 1
  return ja
end

function UnitNames.name(guid, shown)
  return answer("name", guid, shown)
end

function UnitNames.subname(guid, shown)
  return answer("subname", guid, shown)
end

-- A text read from a widget the client reuses for another unit (a nameplate given to the next mob) can still be the
-- previous unit's name while the token already names the new one: such a pair is neither answered nor recorded
-- (a send paired a Durotar boar's name with Gamon's id). The check needs UnitName and a plain, non-secret answer.
local function bare(s) return (s:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")) end
local function stale(unit, shown)
  local unitName = WFJ.Compat.resolve("UnitName")
  if type(unitName) ~= "function" then return false end
  local ok, current = pcall(unitName, unit)
  if not ok or secret(current) or type(current) ~= "string" or current == "" then return false end
  return bare(current) ~= bare(shown)
end

function UnitNames.forUnit(unit, shown)
  local unitGUID = WFJ.Compat.resolve("UnitGUID")
  if type(unitGUID) ~= "function" or unit == nil then return nil end
  if secret(unit) or secret(shown) or type(shown) ~= "string" or stale(unit, shown) then return nil end
  return UnitNames.name(unitGUID(unit), shown)
end

-- ── by English: a name with no GUID ─────────────────────────────────────────────────────────────────────────────
-- An objective line ("0/4 Young Thistle Boar slain") or a system line names a mob by its English alone. The index,
-- built once at load (Main), maps the fingerprint of each shipped name's English (its h1) to its Italian, the marked
-- names inside it resolved to Italian whatever the style then. Two Italian names for one English: the most common;
-- a tie answers nothing (the shipped rows carry no provenance, so the official one cannot be told apart).
local byH1, counts = nil, { names = 0, ambiguous = 0 }

function UnitNames.buildIndex(rows)
  rows = rows or (WFJ.Data and WFJ.Data.unit) or {}
  local slots = WFJ.SLOTS.unit
  local i = slots.index.name
  local tally = {} -- [h1] = { [Italian] = count }
  for _, row in pairs(rows) do
    local ja, h1 = row[i], row[i + slots.hash]
    if type(ja) == "string" and ja ~= "" and h1 ~= nil then
      if WFJ.Names then ja = WFJ.Names.resolve(ja, "it") end
      local t = tally[h1] or {}
      tally[h1] = t
      t[ja] = (t[ja] or 0) + 1
    end
  end
  byH1, counts = {}, { names = 0, ambiguous = 0 }
  for h1, forms in pairs(tally) do
    local best, top, tie = nil, 0, false
    for ja, n in pairs(forms) do
      if n > top then best, top, tie = ja, n, false elseif n == top then tie = true end
    end
    if tie then
      counts.ambiguous = counts.ambiguous + 1
    else
      byH1[h1], counts.names = best, counts.names + 1
    end
  end
  return byH1
end

function UnitNames.indexCounts()
  return { names = counts.names, ambiguous = counts.ambiguous }
end

-- The Italian name for an NPC's English `en`, by the index. nil (leave `en`): no index, `names.style` = "en", a
-- secret value, not a string, or no shipped name. → Italian | nil
function UnitNames.byEnglish(en)
  if byH1 == nil then return nil end
  if WFJ.Names and WFJ.Names.style() == "en" then return nil end
  if secret(en) or type(en) ~= "string" or en == "" then return nil end
  return byH1[WFJ.Hash.h32x2(WFJ.Normalize.v1(en))]
end

-- the `creatureName` argument kind of Core/UIStrings (QUEST_MONSTERS_KILLED's mob)
WFJ.UIStrings = WFJ.UIStrings or {}
WFJ.UIStrings.creatureName = UnitNames.byEnglish

-- /fita nomi: the GUID cache and the UI index's memo (its matches hold the creatureName of the old style)
WFJ.State.on("names", function()
  UnitNames.reset()
  local index = WFJ.UIIndex
  if index and type(index.resetMemo) == "function" then index:resetMemo() end
end)
