-- UI/NamePlates.lua: an NPC's name on its nameplate (surface "nameplates", area "ui", ADR-103, Task 10).
-- The client writes a plate's name in CompactUnitFrame_UpdateName (a global, shared/compactunitframe.lua:
-- frame.name:SetText(GetUnitName(frame.unit, true)), then a vertex colour and Show), reached from the plate driver's
-- SetUnit on NAME_PLATE_UNIT_ADDED (CompactUnitFrame_SetUnit → UpdateAll) and from the frame's UNIT_NAME_UPDATE. The
-- global is post-hooked; the name is replaced only when Core/UnitNames answers for the English just read (a
-- creature's GUID whose `unit` row translates that English), through Render (Alt shows the English; /fita nomi en
-- and back re-run every plate shown: refreshNames). A colour code around the name is kept (ctx.wrap).
-- Never written:
--   a compact raid / party frame: the same global writes them. Only a frame whose `unit` is a "nameplate<n>" token
--     AND which is that token's plate's own UnitFrame (C_NamePlate.GetNamePlateForUnit(token).UnitFrame == frame) is
--     looked at;
--   a forbidden plate (friendly plates in an instance): IsForbidden is asked first and nothing else is read from it;
--   a player's, a pet's or an object's plate, the personal plate ("player" is no nameplate token), a Forever rename:
--     UnitNames answers nil;
--   a secret value: the unit token, the text read back and the GUID are checked with issecretvalue before any string
--     operation or comparison (UnitNames guards the GUID and the shown text again).
-- Combat (always on, not a switch): from PLAYER_REGEN_DISABLED (Main → onCombatStart, still before the lockdown: every
--   plate's English goes back and its record is released) to PLAYER_REGEN_ENABLED (Main → onCombatEnd: the Italian on
--   every plate shown, C_NamePlate.GetNamePlates()) nothing of this addon writes a plate: no Italian, no English, no
--   font, no Alt, no /fita nomi. InCombatLockdown() counts too (a /reload in combat).
-- Pooled frames: the client reuses a plate's unit frame for the next unit. A record is released on
--   NAME_PLATE_UNIT_REMOVED (the client's English put back over our text) and whenever the frame turns up for another
--   unit token, so a reused frame never keeps the previous unit's Italian.
-- Performance: the hook runs for every compact frame's name update; it leaves at the first failed check (type,
--   IsForbidden, the token's prefix). No OnUpdate, no polling; the answers are cached in Core/UnitNames.
-- ADR-058 check [from the mainline / retail code family this client shares, recalled, NOT re-read against a Forever
--   1.60.1 extract: none is on this machine]: a nameplate's `name` FontString is anchored to the plate's health bar
--   (its width comes from the anchors, a long name is truncated). No Blizzard code found calls GetText /
--   GetStringWidth / GetStringHeight / GetLineHeight on it or lays anything out from it: the plate size goes through
--   C_NamePlate.SetNamePlate{Friendly,Enemy,Self}Size from the driver's options (CVars and a base width, out of
--   combat), the aura container anchors by ShouldShowName(frame), not by the text, and the base plate frames are
--   placed by the client. Not found measured on a path that ends in a protected call, so it is written (out of
--   combat only). UI/TaintWatch names it on the first block; Task 12 checks it in game (the report of Task 10 lists
--   the checks: /fita taint after combat with plates up, in a dungeon with friendly plates forbidden, a rename).
local _, WFJ = ...
local NamePlates = {}
WFJ.NamePlates = NamePlates

local SURFACE = "nameplates"
NamePlates.SURFACE = SURFACE
local Compat = WFJ.Compat
local SS = WFJ.SurfaceState

-- The plates are pooled and unnamed: no widget of theirs is addressed by name, and no dictionary key is shown here.
NamePlates.NEVER_TOUCH = {}

local function declareAll()
  Compat.declare(SURFACE, "updateName", { "CompactUnitFrame_UpdateName" })
  Compat.declare(SURFACE, "plates", { "C_NamePlate.GetNamePlates" })
  Compat.declare(SURFACE, "plateFor", { "C_NamePlate.GetNamePlateForUnit" })
  Compat.declare(SURFACE, "isSecret", { "issecretvalue" })
  Compat.declare(SURFACE, "inCombat", { "InCombatLockdown" })
  Compat.declare(SURFACE, "unitGUID", { "UnitGUID" })
end

local function get(key) return Compat.get(SURFACE, key) end

-- → true when `v` must not be read further (a secret value: comparing it from addon code can raise).
local function secret(v)
  local isSecret = get("isSecret")
  return type(isSecret) == "function" and isSecret(v) == true
end

local function inCombat()
  local fn = get("inCombat")
  return type(fn) == "function" and fn() and true or false
end

-- From PLAYER_REGEN_DISABLED to PLAYER_REGEN_ENABLED, or while InCombatLockdown() says so: no write at all.
local combatHeld = false
-- Set by init once the writer is hooked: without the hook nothing here writes (Main routes the events regardless).
local hooked = false
local function quiet()
  return combatHeld or inCombat()
end

local plateKey = WFJ.Labels.keyer("plate.") -- one record per unit frame (pooled: keyed by the frame object)
-- { [unit frame] = the token its Italian was written for }: weak-keyed; a frame here has a live record.
local written = setmetatable({}, { __mode = "k" })

-- Lets go of one frame's record: the client's English back over our text, or, in combat, forgotten unwritten.
local function release(frame)
  local key = plateKey(frame)
  written[frame] = nil
  if quiet() then
    SS.records(SURFACE)[key] = nil
  else
    SS.drop(SURFACE, key)
  end
end

-- A name's colour code around the words: → before, words, after
local function decoration(text)
  local before = text:match("^|c%x%x%x%x%x%x%x%x") or ""
  local rest = text:sub(#before + 1)
  local after = rest:match("|r$") or ""
  return before, rest:sub(1, #rest - #after), after
end

-- → the token when `frame` is a nameplate's own unit frame (not forbidden), else nil
local function plateToken(frame)
  if type(frame) ~= "table" then return nil end
  local isForbidden = frame.IsForbidden
  if type(isForbidden) ~= "function" or isForbidden(frame) then return nil end
  local unit = frame.unit
  if secret(unit) or type(unit) ~= "string" or not unit:find("^nameplate%d") then return nil end
  local plateFor = get("plateFor")
  local plate = type(plateFor) == "function" and plateFor(unit) or nil
  if type(plate) ~= "table" or plate.UnitFrame ~= frame then
    if written[frame] then release(frame) end -- a frame of ours that is no longer that token's plate
    return nil
  end
  return unit
end

-- hooksecurefunc target (CompactUnitFrame_UpdateName; also the plate events and the names / combat refreshes).
-- Written only over the English just read; our own text still showing for the same token is left alone; anything
-- else drops this frame's record without writing over the client. → true when the name was written
function NamePlates.onName(frame)
  local unit = plateToken(frame)
  local fs = unit and frame.name or nil
  if type(fs) ~= "table" or type(fs.GetText) ~= "function" then return false end
  if quiet() then -- released at PLAYER_REGEN_DISABLED already; a record left over is forgotten unwritten
    if written[frame] then release(frame) end
    return false
  end
  local key = plateKey(frame)
  local text = fs:GetText()
  if secret(text) or type(text) ~= "string" then
    written[frame] = nil
    SS.drop(SURFACE, key)
    return false
  end
  local rec = SS.get(SURFACE, key)
  if rec and rec.fs == fs and rec.applied ~= nil and text == rec.applied and written[frame] == unit then
    return false
  end
  local before, words, after = decoration(text)
  local U = WFJ.UnitNames
  local it = U and words ~= "" and U.forUnit(unit, words) or nil
  local unitGUID = get("unitGUID")
  local id = it and type(unitGUID) == "function" and WFJ.Collector.creatureId(unitGUID(unit)) or nil
  if not id then
    written[frame] = nil
    SS.drop(SURFACE, key)
    return false
  end
  written[frame] = unit
  return WFJ.Render.show(SURFACE, key, fs, text, "ui", "unit.name", id, { compact = true, wrap = { before, after } })
end

-- The plates shown now (non-forbidden ones only: GetNamePlates without its secure flag). → list
local function shownPlates()
  local fn = get("plates")
  local list = type(fn) == "function" and fn() or nil
  return type(list) == "table" and list or {}
end

-- Every plate shown again: the English back where our text still shows, then the Italian if the style asks for it.
-- → the number of names written
function NamePlates.refreshNames()
  if not hooked or quiet() then return 0 end -- in combat: onCombatEnd runs this again
  for frame in pairs(written) do written[frame] = nil end
  SS.dropAll(SURFACE)
  local n = 0
  for _, plate in ipairs(shownPlates()) do
    if type(plate) == "table" and NamePlates.onName(plate.UnitFrame) then n = n + 1 end
  end
  WFJ.Render.updateBanner(SURFACE)
  return n
end
-- The State "names" event (/fita nomi): Render's refresh does not consult the names style, so this surface does.
WFJ.State.on("names", function() NamePlates.refreshNames() end)

-- PLAYER_REGEN_DISABLED (Main), still before the lockdown: every plate's English back, every record released.
-- → records whose widget needed a write
function NamePlates.onCombatStart()
  combatHeld = false -- the drops' own writes happen now, before the hold
  for frame in pairs(written) do written[frame] = nil end
  local n = SS.dropAll(SURFACE)
  combatHeld = true
  WFJ.Render.updateBanner(SURFACE)
  return n
end

-- PLAYER_REGEN_ENABLED (Main): the Italian over every plate shown. → names written
function NamePlates.onCombatEnd()
  combatHeld = false
  return NamePlates.refreshNames()
end

-- NAME_PLATE_UNIT_ADDED: the client's SetUnit has written the name through the hooked global already; the plate is
-- looked at once more in case this client wrote it another way.
function NamePlates.onAdded(token)
  if not hooked or secret(token) or type(token) ~= "string" then return false end
  local plateFor = get("plateFor")
  local plate = type(plateFor) == "function" and plateFor(token) or nil
  return type(plate) == "table" and NamePlates.onName(plate.UnitFrame) or false
end

-- NAME_PLATE_UNIT_REMOVED: the frame that showed `token` goes back to the pool; its record is released.
function NamePlates.onRemoved(token)
  if not hooked or secret(token) or type(token) ~= "string" then return 0 end
  local n = 0
  for frame, unit in pairs(written) do
    if unit == token then
      release(frame)
      n = n + 1
    end
  end
  if n > 0 then WFJ.Render.updateBanner(SURFACE) end
  return n
end

-- Called by Main (the Forever surface list); Main's own frame routes NAME_PLATE_UNIT_ADDED / _REMOVED and the combat
-- events here (frames are Main's, ADR-016). → false when this client has no nameplate writer or no C_NamePlate.
function NamePlates.init()
  declareAll()
  if hooked or type(get("updateName")) ~= "function" or type(get("plates")) ~= "function"
    or type(get("plateFor")) ~= "function" then
    return false
  end
  hooked = true
  hooksecurefunc("CompactUnitFrame_UpdateName", function(frame) NamePlates.onName(frame) end)
  NamePlates.refreshNames() -- plates already shown (a /reload)
  return true
end
