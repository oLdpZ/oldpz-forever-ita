-- Core/Placeholders.lua: the player tokens the human quest corpus carries, expanded when the Japanese is applied.
-- Pure: the player arrives as a table (Main.lua reads the client). Tokens stay literal in data/.
--   {name}  → player.name (the client's own spelling of the character name)
--   {class} → the Italian class word for the player's sex, by classFile (UnitClass 2nd return); else the
--             localized className
--   {race}  → the Italian race word for the player's sex, by raceFile (UnitRace 2nd return); else the
--             localized raceName
--   <a/b>   → b for a female character (UnitSex 3), else a; a and b are runs of ASCII letters or UTF-8 bytes
--             (`<il/la>`, `<caro/cara>`, `<è/é>`); an emote such as <Sirra ride…> is not a pair
--   any other {word} → left literal and recorded once in Placeholders.unknown (distinct tokens; /fita debug)
-- A token whose value is unavailable (no name yet, an unlisted class with no localized name) stays literal.
-- The words are `WFJ.PlaceholderNames` (Data/Placeholders.lua, generated, loaded before this file):
-- { CLASS = { [token] = { m = …, f = … } }, RACE = … }. Class and race are prose words, not proper names.
local _, WFJ = ...
local Placeholders = {}
WFJ.Placeholders = Placeholders

Placeholders.KNOWN = { "name", "class", "race" }

local names = type(WFJ.PlaceholderNames) == "table" and WFJ.PlaceholderNames or {}
Placeholders.CLASS = type(names.CLASS) == "table" and names.CLASS or {}
Placeholders.RACE = type(names.RACE) == "table" and names.RACE or {}

Placeholders.unknown = {} -- set of distinct unknown {word} tokens met this session

local FEMALE = 3 -- UnitSex: 1 unknown · 2 male · 3 female
local known = {}
for _, word in ipairs(Placeholders.KNOWN) do known[word] = true end

local function nonEmpty(s)
  if type(s) == "string" and s ~= "" then return s end
  return nil
end

-- { m = …, f = … } → the form for the player's sex (the male one when the female one is missing)
local function formFor(forms, female)
  if type(forms) ~= "table" then return nil end
  return nonEmpty(female and forms.f or nil) or nonEmpty(forms.m)
end

-- True when `text` could hold a token; lets a caller skip reading the client for token-free text.
function Placeholders.mayHaveTokens(text)
  return type(text) == "string" and (text:find("{", 1, true) ~= nil or text:find("<", 1, true) ~= nil)
end

-- Distinct unknown tokens met this session, sorted: → count, { "{foo}", … }.
function Placeholders.unknownTokens()
  local list = {}
  for token in pairs(Placeholders.unknown) do list[#list + 1] = token end
  table.sort(list)
  return #list, list
end

-- → expanded text, number of unknown {word} tokens left literal in this text
-- ASCII classes, not %a: %a follows the C locale in PUC Lua and could take high bytes of UTF-8 text.
function Placeholders.expand(text, player)
  if not Placeholders.mayHaveTokens(text) then
    return text, 0
  end
  player = player or {}
  local female = player.sex == FEMALE
  local values = {
    name = nonEmpty(player.name),
    class = formFor(Placeholders.CLASS[player.classFile], female) or nonEmpty(player.className),
    race = formFor(Placeholders.RACE[player.raceFile], female) or nonEmpty(player.raceName),
  }
  local unknown = 0
  local out = text:gsub("{([A-Za-z]+)}", function(word)
    if not known[word] then
      unknown = unknown + 1
      Placeholders.unknown["{" .. word .. "}"] = true
      return nil -- keep the token literal
    end
    return values[word] -- nil keeps a known token literal when its value is unavailable
  end)
  out = out:gsub("<([A-Za-z\128-\255]+)/([A-Za-z\128-\255]+)>", function(m, f)
    if female then return f end
    return m
  end)
  return out, unknown
end
