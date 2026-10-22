-- Core/Names.lua: marked names (spec §8, "stile dei nomi"), the Lua twin of pipeline/wfj/core/names.py (shared
-- vectors/names_vectors.lua). The pipeline stores a glossary name the Italian carries as `⟦<english>=<italian>⟧`;
-- the player sees one form, by the `names.style` setting: "it" (the official Italian, the default) or "en".
-- Pure: no globals, no frames; the setting is read through WFJ.Settings at call time.
--   Names.resolve(text[, style])  → the text with every marker as its chosen form (non-strings pass through)
--   Names.entry(entry)            → a Lookup entry with its `ja` / variants / sections resolved (a copy only when a
--                                   marker is there; the shipped rows are never edited)
-- Core/Lookup runs every entry through Names.entry: that one read path is what the quest window, gossip, books,
-- tooltips, speech and the collector's covered check all read, so no surface resolves on its own. The reveal key
-- (ADR-018) leaves the client's English before any lookup, so it is unaffected.
local _, WFJ = ...
local Names = {}
WFJ.Names = Names

Names.OPEN = "\226\159\166" -- ⟦ (U+27E6)
-- Lazy on both halves: ⟦⟧ are multibyte, so a `[^…]` set cannot exclude them (the Python twin is `⟦(.*?)=(.*?)⟧`)
local MARK = "\226\159\166(.-)=(.-)\226\159\167"

-- Style "en": an English name starting "The " right after one of these (case-insensitive, a whole word, then one
-- space) loses its "The ": "la The Bulwark" reads "la Bulwark". APOSTROPHE takes the apostrophe instead
-- ("dall'The Den" → "dall'Den"). Twin of core/names.py.
local ARTICLES = {}
for w in ("il lo la i gli le del dello della dei degli delle al allo alla ai agli alle dal dallo dalla dai dagli "
  .. "dalle nel nello nella nei negli nelle sul sullo sulla sui sugli sulle col"):gmatch("%a+") do
  ARTICLES[w] = true
end
local APOSTROPHE = { l = true, dell = true, all = true, dall = true, nell = true, sull = true }
local RIGHT_QUOTE = "\226\128\153" -- ’ (U+2019)

-- `before` (the text up to a marker) ends with an Italian article and one space, or an elided one and its apostrophe
local function afterArticle(before)
  local word, set
  if before:sub(-1) == " " then
    word, set = before:sub(1, -2), ARTICLES
  elseif before:sub(-1) == "'" then
    word, set = before:sub(1, -2), APOSTROPHE
  elseif before:sub(-3) == RIGHT_QUOTE then
    word, set = before:sub(1, -4), APOSTROPHE
  else
    return false
  end
  local w = word:match("[%a\128-\255]+$")
  return w ~= nil and set[w:lower()] == true
end

local function english(text)
  local out, at = {}, 1
  while true do
    local s, e, en = text:find(MARK, at)
    if s == nil then break end
    out[#out + 1] = text:sub(at, s - 1)
    if en:sub(1, 4) == "The " and afterArticle(text:sub(1, s - 1)) then en = en:sub(5) end
    out[#out + 1] = en
    at = e + 1
  end
  out[#out + 1] = text:sub(at)
  return table.concat(out)
end

local function style()
  local S = WFJ.Settings
  if S == nil then return "it" end
  local ok, v = pcall(S.get, "names.style")
  return (ok and v == "en") and "en" or "it"
end
Names.style = style

function Names.resolve(text, which)
  if type(text) ~= "string" or not text:find(Names.OPEN, 1, true) then return text end
  if (which or style()) == "en" then
    return english(text)
  end
  return (text:gsub(MARK, "%2"))
end

local function marked(list)
  for _, v in ipairs(list) do
    if type(v) == "string" and v:find(Names.OPEN, 1, true) then return true end
  end
  return false
end

-- A copy of `list` (its array part resolved, every other key kept as it is), or `list` itself when nothing is marked.
local function resolvedList(list, which)
  if type(list) ~= "table" or not marked(list) then return list end
  local out = {}
  for k, v in pairs(list) do out[k] = v end
  for i, v in ipairs(list) do out[i] = Names.resolve(v, which) end
  return out
end

-- A sectioned line's slot `{ head, hkey, { n, key, it, shape }… }` (Align.sections): a copy with `head` and every
-- section's `it` resolved, or the slot itself when nothing is marked.
function Names.sections(sec, which)
  local any = type(sec.head) == "string" and sec.head:find(Names.OPEN, 1, true)
  for _, s in ipairs(sec) do
    if type(s) == "table" and type(s.it) == "string" and s.it:find(Names.OPEN, 1, true) then any = true end
  end
  if not any then return sec end
  local out = {}
  for k, v in pairs(sec) do out[k] = v end
  out.head = Names.resolve(sec.head, which)
  for i, s in ipairs(sec) do
    local c = {}
    for k, v in pairs(s) do c[k] = v end
    c.it = Names.resolve(s.it, which)
    out[i] = c
  end
  return out
end

function Names.entry(e)
  if type(e) ~= "table" then return e end
  local which = style()
  if type(e.ja) == "string" then e.ja = Names.resolve(e.ja, which) end
  if e.variants ~= nil then e.variants = resolvedList(e.variants, which) end
  if type(e.sections) == "table" then e.sections = Names.sections(e.sections, which) end
  return e
end

