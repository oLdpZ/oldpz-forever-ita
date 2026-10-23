-- Core/Settings.lua: the settings registry and its persistence in OFI_DB (docs/systems/settings.md).
-- Registry: define/get/set/list/find. Persistence: load(db, schema, migrations) → db.
-- Defaults live only in `define`. Panel (UI/Options) and slash (UI/Slash) iterate the registry, never their own lists.
local _, WFJ = ...
local Settings = {}
WFJ.Settings = Settings

local defs, order = {}, {}
local db -- the live OFI_DB table, set by load()

-- Settings.MIGRATIONS[n](db) runs while db.schema < n, in order. Empty at schema 1.
Settings.MIGRATIONS = {}

-- ── Registry ────────────────────────────────────────────────────────────────

function Settings.define(d)
  assert(type(d) == "table" and type(d.id) == "string" and d.id ~= "", "Settings.define: id required")
  assert(defs[d.id] == nil, "Settings.define: duplicate id " .. d.id)
  assert(d.kind == "boolean" or d.kind == "choice" or d.kind == "key", "Settings.define: unknown kind for " .. d.id)
  if d.kind == "choice" then
    assert(type(d.choices) == "table" and #d.choices > 0, "Settings.define: choices required for " .. d.id)
  end
  if d.kind == "key" then
    assert(type(d.normalize) == "function", "Settings.define: normalize required for " .. d.id)
  end
  defs[d.id] = d
  order[#order + 1] = d.id
  return d
end

-- Case-insensitive lookup by id (slash input) → canonical id or nil.
function Settings.find(name)
  if type(name) ~= "string" then return nil end
  if defs[name] then return name end
  local lower = name:lower()
  for _, id in ipairs(order) do
    if id:lower() == lower then return id end
  end
  return nil
end

-- A definition's optional `hidden`: true, or a function asked each time (a setting that only exists while another
-- addon is installed). Hidden settings stay readable and settable; they are only left out of lists.
function Settings.isHidden(d)
  if type(d.hidden) == "function" then return d.hidden() and true or false end
  return d.hidden and true or false
end

function Settings.list()
  local out = {}
  for i, id in ipairs(order) do out[i] = defs[id] end
  return out
end

function Settings.get(id)
  local d = defs[id]
  assert(d, "Settings.get: unknown setting " .. tostring(id))
  if db and db.settings[id] ~= nil then return db.settings[id] end
  return d.default
end

-- Strings are matched case-insensitively (slash input: `/fita area quests OFF`). A `key` value is canonicalized by
-- its definition's `normalize` (`/fita modifier LAlt` → lalt, `q` → Q).
local function coerce(d, v)
  if d.kind == "key" then
    local n = d.normalize(v)
    if n == nil then return false, "expected a key (alt, lalt, button4, q, …)" end
    return true, n
  end
  if type(v) == "string" then v = v:lower() end
  if d.kind == "boolean" then
    if type(v) == "boolean" then return true, v end
    if v == "on" or v == "true" or v == "1" then return true, true end
    if v == "off" or v == "false" or v == "0" then return true, false end
    return false, "expected on|off"
  end
  for _, c in ipairs(d.choices) do
    if c == v then return true, v end
  end
  return false, "expected one of " .. table.concat(d.choices, "|")
end

-- Returns true, or false + reason. Invalid values leave the stored value untouched. A definition's optional
-- `check(value) → ok, reason` refuses a valid value that conflicts with live client state (the modifier
-- cannot be the toggle key); it runs on `set` only, since `load` never consults the client.
function Settings.set(id, v)
  local d = defs[id]
  if not d then return false, "unknown setting " .. tostring(id) end
  local ok, val = coerce(d, v)
  if not ok then return false, val end
  if d.check then
    local fine, why = d.check(val)
    if not fine then return false, why end
  end
  assert(db, "Settings.set before Settings.load")
  db.settings[id] = val
  if d.apply then d.apply(val) end
  return true
end

-- ── Persistence ─────────────────────────────────────────────────────────────

-- Takes the SavedVariables table (or nil on first run), returns the table to store back in OFI_DB.
-- Upgrade: MIGRATIONS run in order. Downgrade (db.schema > schema): the whole table is kept under `backup`,
-- settings reset, one line printed. Unknown keys are preserved and never read. Every `apply` runs once.
function Settings.load(saved, schema, migrations)
  schema = schema or WFJ.SCHEMA
  migrations = migrations or Settings.MIGRATIONS
  local d = saved
  if type(d) ~= "table" then d = { schema = schema, settings = {} } end
  if type(d.settings) ~= "table" then d.settings = {} end
  -- A non-integer (or NaN) schema can only come from a hand edit; treat it as current rather than looping or
  -- flipping into a downgrade next session.
  if type(d.schema) ~= "number" or d.schema ~= math.floor(d.schema) then d.schema = schema end

  if d.schema > schema then
    local old = d
    old.backup = nil -- keep only the newest backup; never nest them
    d = { schema = schema, settings = {}, backup = old }
    print(("OFI: settings from a newer version (schema %d > %d) were backed up and reset (downgrade)."):format(
      old.schema, schema))
  else
    while d.schema < schema do
      local n = d.schema + 1
      local m = migrations[n]
      if m then m(d) end
      d.schema = n
    end
  end

  -- Stored values are validated against the registry; anything a hand edit or another version left that no
  -- longer fits falls back to the default rather than reaching an `apply`.
  for _, id in ipairs(order) do
    local v = d.settings[id]
    if v ~= nil then
      local ok, val = coerce(defs[id], v)
      if ok then d.settings[id] = val else d.settings[id] = nil end
    end
  end

  d.build = { addon = WFJ.VERSION }
  db = d
  for _, id in ipairs(order) do
    local def = defs[id]
    if def.apply then def.apply(Settings.get(id)) end
  end
  return d
end

-- ── Definitions ─────────────────────────────────────────────────────────────
-- `apply` closures resolve their modules at call time (load runs after every file is loaded).
-- Collector settings (`collector.enabled`, `collector.capMB`) are defined by Core/Collector.lua.

local function area(id)
  return function(v) WFJ.State.setArea(id, v) end
end
local function markers()
  WFJ.State.fire("markers")
end

-- The modifier and the toggle binding may not share a key (either would swallow the other). The toggle key is
-- client state, read through Compat's injected env so Core stays frame-free.
local function notToggleKey(v)
  local getKey = WFJ.Compat and WFJ.Compat.resolve("GetBindingKey")
  if type(getKey) ~= "function" then return true end
  local keys = { getKey("OFI_TOGGLE") }
  for _, k in ipairs(keys) do
    if type(k) == "string" and k:upper() == v:upper() then
      return false, v .. " is already the key for turning translation on / off"
    end
  end
  return true
end

-- `it`: the Italian the settings page shows for the English `label` (addon interface copy, not game text).
Settings.define{ id = "enabled", kind = "boolean", default = true, label = "Enable translation",
  it = "Attiva la traduzione", apply = function(v) WFJ.State.setEnabled(v) end }
Settings.define{ id = "modifier", kind = "key", default = "alt", label = "Hold to show English",
  it = "Tieni premuto per l'inglese", normalize = function(v) return WFJ.Modifier.normalize(v) end,
  check = notToggleKey, apply = function(v) WFJ.Modifier.setKey(v) end } -- ADR-018
Settings.define{ id = "area.quests", kind = "boolean", default = true, group = "areas",
  label = "Quest windows & log", it = "Finestre e registro delle missioni", apply = area("quests") }
Settings.define{ id = "area.gossip", kind = "boolean", default = true, group = "areas",
  label = "NPC talk", it = "Dialoghi dei PNG", apply = area("gossip") }
Settings.define{ id = "area.itemTooltips", kind = "boolean", default = true, group = "areas",
  label = "Item tooltips", it = "Tooltip degli oggetti", apply = area("items") }
Settings.define{ id = "area.spellTooltips", kind = "boolean", default = true, group = "areas",
  label = "Spell tooltips", it = "Tooltip delle abilità", apply = area("spells") }
Settings.define{ id = "area.interface", kind = "boolean", default = true, group = "areas",
  label = "Interface text (buttons, headers, tooltip lines)",
  it = "Testo dell'interfaccia (pulsanti, intestazioni, righe dei tooltip)", apply = area("ui") }
Settings.define{ id = "area.books", kind = "boolean", default = true, group = "areas",
  label = "Books & letters", it = "Libri e lettere", apply = area("books") } -- the item text window
Settings.define{ id = "marker.stale", kind = "boolean", default = true,
  label = "Mark translations whose English changed", it = "Segna le traduzioni il cui inglese è cambiato",
  apply = markers }
-- On by default: a refused or absent translation says so instead of passing as untouched English.
Settings.define{ id = "marker.missing", kind = "boolean", default = true,
  label = "Mark untranslated text", it = "Segna il testo non tradotto", apply = markers }
-- Spec §8 "stile dei nomi": a name the pipeline marked (Core/Names) shows as Blizzard's official Italian (the default)
-- or as the original English, everywhere shipped text is read. Class and race words are never marked.
Settings.define{ id = "names.style", kind = "choice", choices = { "it", "en" }, default = "it",
  label = "Names of places, characters, factions, items and abilities",
  it = "Nomi di luoghi, personaggi, fazioni, oggetti e abilità",
  choiceText = { it = "Italiani ufficiali", en = "Originali inglesi" },
  apply = function(v) WFJ.State.fire("names", v) end }
-- The fix-report minimap button, on by default. UI/MinimapButton
-- listens for the State event; its right-click menu's "Hide this button" turns this off.
Settings.define{ id = "minimapButton", kind = "boolean", default = true,
  label = "Show the minimap button (report a line)", it = "Mostra il pulsante della minimappa (segnala una riga)",
  apply = function(v) WFJ.State.fire("minimapButton", v) end }

-- Italian voice over (Core/Voice): shown only once a voice pack has registered, so a player without the pack never
-- sees a setting that does nothing. The voice player listens for the State event and stops a line switched off.
local function voiceHidden() return not (WFJ.Voice and WFJ.Voice.hasPack()) end
local function voiceChanged() WFJ.State.fire("voice") end
local function voiceSetting(id, label, it)
  Settings.define{ id = id, kind = "boolean", default = true, hidden = voiceHidden, label = label, it = it,
    apply = voiceChanged }
end
voiceSetting("voice.enabled", "Read lines aloud in Italian", "Leggi le battute ad alta voce in italiano")
voiceSetting("voice.offer", "Quest offers", "Proposte delle missioni")
voiceSetting("voice.progress", "Quest progress", "Missioni in corso")
voiceSetting("voice.turnin", "Quest turn-ins", "Consegne delle missioni")
-- An NPC's greeting: the first time you meet each one (remembered in OFI_DB.voiceHeard), every time, or never.
Settings.define{ id = "voice.greeting", kind = "choice", choices = { "once", "always", "never" }, default = "once",
  hidden = voiceHidden, apply = voiceChanged,
  label = "NPC greetings", it = "Saluti dei PNG",
  choiceText = { once = "Una volta per PNG", always = "Sempre", never = "Mai" } }
voiceSetting("voice.books", "Books and letters", "Libri e lettere")
-- While a line plays the game's own English voice is turned off, and put back afterwards (the voice player).
voiceSetting("voice.muteDialog", "Silence the game's English voices while a line plays",
  "Silenzia le voci inglesi del gioco mentre parla un PNG")
