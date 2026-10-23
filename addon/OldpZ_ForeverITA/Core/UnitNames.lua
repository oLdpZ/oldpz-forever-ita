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

local function compute(field, guid, shown)
  local id = WFJ.Collector.creatureId(guid)
  if id == nil then return nil end
  local entry = WFJ.Lookup.get("unit." .. field, id)
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

function UnitNames.forUnit(unit, shown)
  local unitGUID = WFJ.Compat.resolve("UnitGUID")
  if type(unitGUID) ~= "function" or unit == nil then return nil end
  return UnitNames.name(unitGUID(unit), shown)
end

WFJ.State.on("names", UnitNames.reset)
