-- UI/Questie.lua: Italian quest titles, quest objectives and NPC names for the Questie addon (ADR-105).
-- Questie reads one global, QUESTIE_LOCALES_OVERRIDE, the contract external translation addons use
-- (Questie: Localization/l10n.lua, docs/adr/0003-external-locale-addons-through-provider-corrections.md):
--   { locale, localeName, translations = { [English UI string] = text },
--     questLookup = fn → { [questId] = { title, { objective line, … } } },
--     npcNameLookup = fn → { [npcId] = { name, subName } } }
-- At login (QuestieInit Stage 1, after every ADDON_LOADED) it selects `locale` for its own UI and publishes the
-- lookups to QuestieDB as that locale's names; a missing or empty field falls back to its English. Its own UI strings
-- stay English: `translations` is empty, so every key falls back to the English key.
-- What is published is what this addon would show: Core/Lookup rows with their marked names resolved to the player's
-- `names.style`; a text still holding a token (`$N1`, `{name}`) is left out, there is no live value to fill it with.
-- NPC names follow UnitNames: none with `names.style` = "en".
-- Questie also matches a gossip quest's title, as the client's API gives it (English), with its database's title
-- (QuestieDB.GetQuestIDFromName, QuestgiverFrame / QuestieCompat): with Italian titles that match fails and the gossip
-- icon falls back. `wrap` retries a failed match with the Italian titles of the quests whose English fingerprint (h1)
-- is the one asked.
--   Questie.install(env)  → true when the global was set (never over another addon's)
--   Questie.quests() / Questie.npcs()  → the lookup tables
--   Questie.titlesFor(english) → { Italian title, … }
--   Questie.wrap(questieDB)  → true when GetQuestIDFromName was wrapped
--   Questie.wrapTracker(trackerData) → true when the tracker's title and objective writers were wrapped
local _, WFJ = ...
local Questie = {}
WFJ.Questie = Questie

Questie.LOCALE = "itIT"
Questie.GLOBAL = "QUESTIE_LOCALES_OVERRIDE"

-- a text Questie can show as it is: no token for a live value
local function usable(text)
  return type(text) == "string" and text ~= "" and not text:find("[%$%{]")
end

local function ja(kind, id)
  local entry = WFJ.Lookup.get(kind, id)
  if entry ~= nil and usable(entry.ja) then return entry.ja end
  return nil
end

local function lines(text)
  local out = {}
  for line in (text .. "\n"):gmatch("(.-)\n") do
    line = line:gsub("^%s+", ""):gsub("%s+$", "")
    if line ~= "" then out[#out + 1] = line end
  end
  return out
end

function Questie.quests()
  local out = {}
  for id in pairs(WFJ.Data.quest) do
    if type(id) == "number" then
      local title, objectives = ja("quest.title", id), ja("quest.objectives", id)
      local list = objectives and lines(objectives) or {}
      if title or #list > 0 then out[id] = { title or "", list } end
    end
  end
  return out
end

function Questie.npcs()
  local out = {}
  if WFJ.Names and WFJ.Names.style() == "en" then return out end
  for id in pairs(WFJ.Data.unit) do
    if type(id) == "number" then
      local name, sub = ja("unit.name", id), ja("unit.subname", id)
      if name or sub then out[id] = { name or "", sub or "" } end
    end
  end
  return out
end

function Questie.install(env)
  if type(env) ~= "table" or env[Questie.GLOBAL] ~= nil then return false end
  env[Questie.GLOBAL] = { locale = Questie.LOCALE, localeName = "Italiano", translations = {},
    questLookup = Questie.quests, npcNameLookup = Questie.npcs }
  return true
end

-- English title fingerprint (h1) → { quest id, … }, built on the first failed match
local byH1 = nil

local function index()
  if byH1 then return byH1 end
  byH1 = {}
  for id in pairs(WFJ.Data.quest) do
    local entry = type(id) == "number" and WFJ.Lookup.raw("quest.title", id) or nil
    if entry ~= nil and entry.h1 ~= nil then
      local list = byH1[entry.h1] or {}
      list[#list + 1] = id
      byH1[entry.h1] = list
    end
  end
  return byH1
end

function Questie.reset()
  byH1 = nil
end

function Questie.titlesFor(english)
  local out = {}
  if type(english) ~= "string" or english == "" then return out end
  local ids = index()[WFJ.Hash.h32x2(WFJ.Normalize.v1(english))]
  local seen = {}
  for _, id in ipairs(ids or {}) do
    local title = ja("quest.title", id)
    if title and title ~= english and not seen[title] then
      seen[title] = true
      out[#out + 1] = title
    end
  end
  return out
end

local wrapped = setmetatable({}, { __mode = "k" })

function Questie.wrap(db)
  if type(db) ~= "table" or type(db.GetQuestIDFromName) ~= "function" or wrapped[db] then return false end
  local original = db.GetQuestIDFromName
  db.GetQuestIDFromName = function(name, giver, starter)
    local id = original(name, giver, starter)
    if id ~= nil and id ~= 0 then return id end
    for _, title in ipairs(Questie.titlesFor(name)) do
      local found = original(title, giver, starter)
      if found ~= nil and found ~= 0 then return found end
    end
    return id
  end
  wrapped[db] = true
  return true
end

-- ── The tracker ─────────────────────────────────────────────────────────────────────────────────────────────────
-- Questie's tracker does not read its database for what it shows: the quest's title and each objective line come
-- from the client's quest log (TrackerData: "never replaces the native title, objective wording or live progress
-- with database values"), so they are the client's English. The tracker writes them through two functions of the
-- TrackerData module, looked up on the module at every call (QuestSection, TrackerLinePool, TrackerMenu):
--   TrackerData.GetColoredQuestName(displayQuest, showLevel, showState)  displayQuest.name, displayQuest.Id
--   TrackerData.GetObjectiveText(objective)                              objective.Description
-- `wrapTracker` hands each the Italian through a stand-in table that reads every other field from the original
-- (the original record is never written), so Questie colours, levels and tags the Italian as it does the English.
-- What is shown is this addon's: the quest's title row when the English shown is the one it translates (its h1), and
-- an objective line by the same lookups as the quest map's objective lines (QuestMap.objectiveJapanese). The
-- translation off, the quest area off or the reveal key held at the moment Questie draws → its English.
-- The chat link (GetQuestLink) stays English: it is read by other players.

local function trackerOn()
  if WFJ.State.enabled == false or not WFJ.State.areaEnabled("quests") then return false end
  return not (WFJ.Modifier and WFJ.Modifier.isDown())
end

-- → the Italian title of quest `id` when `en` is the English it translates, else nil
function Questie.trackerTitle(id, en)
  if type(id) ~= "number" or type(en) ~= "string" or en == "" or not trackerOn() then return nil end
  local entry = WFJ.Lookup.get("quest.title", id)
  if entry == nil or not usable(entry.ja) or entry.ja == en then return nil end
  if entry.h1 ~= nil and WFJ.Hash.h32x2(WFJ.Normalize.v1(en)) ~= entry.h1 then return nil end
  return entry.ja
end

-- → the Italian of one live objective line, else nil
function Questie.trackerObjective(en)
  if type(en) ~= "string" or en == "" or not trackerOn() then return nil end
  local QuestMap = WFJ.QuestMap
  if not QuestMap or type(QuestMap.objectiveJapanese) ~= "function" then return nil end
  local ok, text = pcall(QuestMap.objectiveJapanese, en, "questie")
  if not ok or type(text) ~= "string" or text == "" or text:find(en, 1, true) then return nil end
  return text
end

local function standIn(original, field, value)
  return setmetatable({ [field] = value }, { __index = original })
end

function Questie.wrapTracker(data)
  if type(data) ~= "table" or wrapped[data] then return false end
  local name, objective = data.GetColoredQuestName, data.GetObjectiveText
  if type(name) ~= "function" and type(objective) ~= "function" then return false end
  if type(name) == "function" then
    data.GetColoredQuestName = function(quest, ...)
      local it = type(quest) == "table" and Questie.trackerTitle(quest.Id, quest.name) or nil
      return name(it and standIn(quest, "name", it) or quest, ...)
    end
  end
  if type(objective) == "function" then
    data.GetObjectiveText = function(line, ...)
      local it = type(line) == "table" and Questie.trackerObjective(line.Description) or nil
      return objective(it and standIn(line, "Description", it) or line, ...)
    end
  end
  wrapped[data] = true
  return true
end
