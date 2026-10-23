-- Core/Voice.lua: the voice pack's registry and the decision whether a shown line is voiced, and with which file.
-- Pure: no frames, no sound API; the voice player (UI) plays what `decide` returns.
-- The audio lives in a separate addon whose folder starts with OldpZ_ForeverITA_Voce; its Register.lua hands its
-- table to the global OldpZ_ForeverITA_RegisterVoice (Main.lua). Each entry is keyed like the Italian it speaks
-- ("<questID>-<field>", "g-<gossip key>", "b-<book page key>") and carries the hash of the shipped Italian it was
-- made from, raw (name markers and tokens as generated): a line whose shipped Italian changed since stays silent,
-- never voices other words, and the hash does not depend on the names style the player chose.
-- A line that names the player or picks a word by sex (`{name}`, `<o/a>`) has a female take; a female character
-- never hears the male one. A line several differently cast creatures say has a file per voice; the speaker on
-- screen picks it.
local _, WFJ = ...
local Voice = {}
WFJ.Voice = Voice

-- every pack's addon folder starts with this; its files are read from its Sound folder
Voice.FOLDER = "OldpZ_ForeverITA_Voce"
Voice.FORMATS = { [3] = true } -- the Register.lua table shapes this file reads

-- The lines a pack may voice: surface → record key → the setting that turns that kind off. Objectives, titles and
-- option rows are never voiced. `voice.greeting` is a choice (once · always · never), the others are switches.
Voice.KINDS = {
  ["questframe.detail"] = { description = "voice.offer" },
  ["questframe.progress"] = { progress = "voice.progress" },
  ["questframe.reward"] = { completion = "voice.turnin" },
  ["questframe.greeting"] = { greeting = "voice.greeting" },
  gossip = { greeting = "voice.greeting" },
  itemtext = { page = "voice.books" },
}

-- pack key → { file, seconds, f = { file, seconds }, itHash, folder, v = { [voice] = { file, seconds, f } } };
-- nil until a pack registers
local lines
local creatures = {} -- creature id → voice id, or { m = male voice, f = female voice } (a creature shown as both)
local creatureBy = {} -- creature id → { [pack folder] = its voice }: several packs may carry one creature
local packs = {} -- pack folder → the number of its lines registered
local deps = {}

local function zero()
  return { registered = 0, invalid = 0, matched = 0, missing = 0, stale = 0 }
end
Voice.counts = zero()

-- deps: lookup(kind, id) → { ja } | nil (the shipped Italian, raw: Lookup.raw), hash(text) → 16 hex,
-- setting(id) → value, revealed() → bool (English showing: the reveal key held), enabled() → bool (translation on),
-- db → OFI_DB (greetings heard once are remembered in db.voiceHeard[creature id], created on the first one)
function Voice.init(d)
  deps = d or {}
end

-- A word the player's sex changes: `{name}` (said as eroe / eroina) or a `<a/b>` pair. The same rule as the
-- pipeline's needs_variants, which decides which lines get a female take.
local PAIR = "<[^<>/%s\"=]+/[^<>/%s\"=]+>"
function Voice.needsVariants(text)
  if type(text) ~= "string" then return false end
  return text:find("{name}", 1, true) ~= nil or text:find(PAIR) ~= nil
end

local function validFile(f)
  return type(f) == "string" and f:match("^[%w%-_]+%.mp3$") ~= nil
end

-- { file, seconds?, f = { file, seconds? }? }
local function validTake(t)
  if type(t) ~= "table" or not validFile(t[1]) or (t[2] ~= nil and type(t[2]) ~= "number") then
    return false
  end
  return t.f == nil or validTake(t.f)
end

local function validEntry(e)
  if not (type(e) == "table" and validFile(e[1]) and type(e[2]) == "string" and e[2]:match("^%x+$") ~= nil
    and #e[2] == 16 and (e[3] == nil or type(e[3]) == "number") and (e.f == nil or validTake(e.f))) then
    return false
  end
  if e.v == nil then return true end
  if type(e.v) ~= "table" then return false end
  for vid, t in pairs(e.v) do
    if type(vid) ~= "string" or not validTake(t) then return false end
  end
  return true
end

local function validVoice(v)
  if type(v) == "string" then return true end
  return type(v) == "table" and type(v.m) == "string" and type(v.f) == "string"
end

-- a take as kept: { file, seconds, f = { file, seconds } | nil }
local function take(file, seconds, f)
  return { file = file, seconds = seconds, f = f and { file = f[1], seconds = f[2] } or nil }
end

local function recount()
  local n = 0
  for _ in pairs(lines or {}) do n = n + 1 end
  Voice.counts.registered = n
end

-- A pack's table → registered, invalid. Packs merge: each line remembers the folder it came from, and a pack that
-- registers again replaces only what it brought. Entries that do not match the shape are dropped and counted, never
-- guessed at: a file name outside the pack's Sound folder would play another addon's file.
function Voice.register(tbl)
  if type(tbl) ~= "table" or not Voice.FORMATS[tbl.format] or type(tbl.folder) ~= "string"
    or tbl.folder:sub(1, #Voice.FOLDER) ~= Voice.FOLDER or not tbl.folder:match("^[%w_]+$")
    or type(tbl.lines) ~= "table" then
    Voice.counts.invalid = Voice.counts.invalid + 1
    return 0, 1
  end
  lines = lines or {}
  for key, e in pairs(lines) do
    if e.folder == tbl.folder then lines[key] = nil end
  end
  for c, by in pairs(creatureBy) do
    if by[tbl.folder] ~= nil then
      by[tbl.folder] = nil
      local _, other = next(by) -- kept while another pack still carries the creature
      creatures[c] = other
      if other == nil then creatureBy[c] = nil end
    end
  end
  local n, bad = 0, 0
  for key, e in pairs(tbl.lines) do
    if type(key) == "string" and validEntry(e) then
      local line = take(e[1], e[3], e.f)
      line.itHash, line.folder = e[2]:lower(), tbl.folder
      if e.v then
        line.v = {}
        for vid, t in pairs(e.v) do line.v[vid] = take(t[1], t[2], t.f) end
      end
      lines[key] = line
      n = n + 1
    else
      bad = bad + 1
    end
  end
  for c, v in pairs(type(tbl.creatures) == "table" and tbl.creatures or {}) do
    if type(c) == "number" and validVoice(v) then
      creatureBy[c] = creatureBy[c] or {}
      creatureBy[c][tbl.folder], creatures[c] = v, v
    else
      bad = bad + 1
    end
  end
  packs[tbl.folder] = n
  Voice.counts.invalid = Voice.counts.invalid + bad
  recount()
  return n, bad
end

-- → { [folder] = lines } of every registered pack (for the settings page and /fita debug)
function Voice.packs()
  return packs
end

function Voice.hasPack()
  return lines ~= nil
end

-- The pack key of a rendered line (its Translator kind and id): a quest field by quest id, gossip and book pages by
-- their key.
function Voice.packKey(kind, id)
  if kind == "gossip" and type(id) == "string" then return "g-" .. id end
  if kind == "book" and type(id) == "string" then return "b-" .. id end
  local field = type(kind) == "string" and kind:match("^quest%.(%a+)$")
  if field and type(id) == "number" then return ("%d-%s"):format(id, field) end
  return nil
end

local function setting(id)
  return type(deps.setting) == "function" and deps.setting(id)
end

local function heardTable()
  return type(deps.db) == "table" and type(deps.db.voiceHeard) == "table" and deps.db.voiceHeard or nil
end

local function heard(creature)
  local t = heardTable()
  return t ~= nil and t[creature] == true
end

local function markHeard(creature)
  if type(deps.db) ~= "table" then return end
  local t = heardTable()
  if not t then
    t = {}
    deps.db.voiceHeard = t
  end
  t[creature] = true
end

-- The take of a line for the speaker on screen: its voice's own take when the line has one for it, else the line's
-- main take. `who`: { creature = id, sex = the speaker's UnitSex (3 female) } or nil.
local function takeFor(entry, who)
  local voice = who and creatures[who.creature]
  if type(voice) == "table" then voice = who.sex == 3 and voice.f or voice.m end
  return voice and entry.v and entry.v[voice] or entry
end

-- A line just shown in Italian on `surface` under record key `recKey`, rendered as (kind, id), said by `who`
-- ({ creature = id, sex = the speaker's UnitSex } or nil), to a character of UnitSex `sex` (3 female).
-- → the file's path and its length in seconds, or nil and why ("kind" · "off" · "english" · "nopack" · "missing" ·
-- "notext" · "stale" · "nofemale"). A greeting set to play once per creature is "off" for a creature already heard.
-- `peek`: only asking (the replay button): /fita debug's counts are left as they are and nothing is remembered.
function Voice.decide(surface, recKey, kind, id, who, sex, peek)
  local byKey = Voice.KINDS[surface]
  local kindSetting = byKey and byKey[recKey]
  if not kindSetting then return nil, "kind" end
  local mode = setting(kindSetting)
  if not setting("voice.enabled") or not mode or mode == "never" then return nil, "off" end
  local creature = type(who) == "table" and who.creature or nil
  local once = mode == "once" and creature ~= nil
  if once and not peek and heard(creature) then return nil, "off" end
  if (type(deps.enabled) == "function" and not deps.enabled())
    or (type(deps.revealed) == "function" and deps.revealed()) then
    return nil, "english"
  end
  if not lines then return nil, "nopack" end
  local key = Voice.packKey(kind, id)
  local entry = key and lines[key]
  if not entry then
    if not peek then Voice.counts.missing = Voice.counts.missing + 1 end
    return nil, "missing"
  end
  local shipped = type(deps.lookup) == "function" and deps.lookup(kind, id) or nil
  if type(shipped) ~= "table" or type(shipped.ja) ~= "string" then return nil, "notext" end
  if type(deps.hash) ~= "function" or deps.hash(shipped.ja) ~= entry.itHash then
    if not peek then Voice.counts.stale = Voice.counts.stale + 1 end
    return nil, "stale"
  end
  local t = takeFor(entry, who)
  if sex == 3 then
    -- the pack made a female take of this line (its main take has one) or its words need one
    if t.f then
      t = t.f
    elseif entry.f or Voice.needsVariants(shipped.ja) then
      return nil, "nofemale"
    end
  end
  if not peek then
    Voice.counts.matched = Voice.counts.matched + 1
    if once then markHeard(creature) end
  end
  return "Interface\\AddOns\\" .. entry.folder .. "\\Sound\\" .. t.file, t.seconds
end
