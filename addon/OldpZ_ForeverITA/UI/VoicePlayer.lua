-- UI/VoicePlayer.lua: plays the voice pack's file for a line the quest, gossip or book window just showed in Italian.
-- Core/Voice decides which file; this file owns every sound and client-setting call; Core/VoiceQueue holds the
-- order; UI/VoicePanel draws what `state()` reports (State "voiceQueue" on every change).
--   * Start: State "lineShown" (fired by UI/Render after a write the client asked for, never on a refresh). A line
--     shown while one plays waits its turn, never twice for one key (the gossip window lays its first page out
--     twice), and plays when the one before it ends.
--   * The window closing does not stop its line: it plays to its end, and the lines waiting after it.
--   * Stop (the queue emptied): the panel's stop button, /fita voce stop, translation or voice switched off, the
--     reveal key going down (no voice while English shows), logout. Skip: the next waiting line now.
--   * Channel "Master", so silencing the dialog channel never silences our own line. PlaySoundFile(path, channel) →
--     willPlay, handle [unverified in the Forever client's own files; the in-game check is in docs/testing/
--     strategy.md]. The client reports no end: a line ends at the pack's length plus a margin.
--   * The game's English voice: while a line plays, Sound_EnableDialog is turned off when it was on, and the fact is
--     kept in OFI_DB.voiceDialogMuted, because the client saves the setting to Config.wtf: a crash in between would
--     otherwise leave the player's NPC voices off for good. It is put back when the queue runs out, on stop, at
--     logout and on the next load. A player who had the dialog channel off keeps it off.
-- Without a voice pack nothing here creates a frame or calls the sound API: `onShown` returns at once.
local _, WFJ = ...
local VoicePlayer = {}
WFJ.VoicePlayer = VoicePlayer

local Compat = WFJ.Compat
local Q = WFJ.VoiceQueue
local CHANNEL = "Master"
local DIALOG = "Sound_EnableDialog"
local END_MARGIN = 0.5 -- seconds after the pack's length before the line counts as ended
local UNKNOWN_LENGTH = 30 -- a pack entry without a length: the longest scoped line is well under this
-- the NPC whose window shows the line: its creature id picks the voice of a line several creatures say
local SPEAKER_UNIT = { QuestFrame = "questnpc", GossipFrame = "npc" }

VoicePlayer.counts = { played = 0, refused = 0 }

local db -- OFI_DB
local playing -- { handle, key, token } while a line plays
local tokens = 0 -- a stale end timer (a line stopped or skipped) finds a newer token and does nothing
local events -- the PLAYER_LOGOUT frame, made by the first line that plays

-- a line may start: translation and voice on, and the reveal key up (no voice starts while English shows)
local function allowed()
  return WFJ.State.enabled and not WFJ.State.modifierHeld and WFJ.Settings.get("voice.enabled") and true or false
end

local function notify(reason)
  pcall(WFJ.State.fire, "voiceQueue", reason)
end

local function getCVar(name)
  local C = Compat.resolve("C_CVar")
  if type(C) == "table" and type(C.GetCVar) == "function" then return C.GetCVar(name) end
  local get = Compat.resolve("GetCVar")
  return type(get) == "function" and get(name) or nil
end

local function setCVar(name, value)
  local C = Compat.resolve("C_CVar")
  if type(C) == "table" and type(C.SetCVar) == "function" then return C.SetCVar(name, value) end
  local set = Compat.resolve("SetCVar")
  if type(set) == "function" then return set(name, value) end
  return nil
end

local function windowOf(surface)
  if surface == "gossip" then return "GossipFrame" end
  if surface == "itemtext" then return "ItemTextFrame" end
  return "QuestFrame"
end

-- The NPC on screen for a window → { creature, sex, unit, guid } or nil (a book has no speaker; a unit token the
-- client does not answer leaves the line's main voice). UnitGUID("questnpc") is the token the quest window names its
-- giver by [verified: classic_era Classic/QuestFrame.lua:118]; UnitSex on an NPC unit [unverified on Forever].
function VoicePlayer.speaker(window)
  local unit = SPEAKER_UNIT[window]
  local guid = unit and Compat.resolve("UnitGUID")
  if type(guid) ~= "function" then return nil end
  local g = guid(unit)
  local id = WFJ.Collector.creatureId(g)
  if not id then return nil end
  local sex = Compat.resolve("UnitSex")
  return { creature = id, sex = type(sex) == "function" and sex(unit) or nil, unit = unit, guid = g }
end

-- The name the panel shows: the NPC's Italian name when one is shipped (Core/UnitNames), else the client's; a book's
-- own name.
function VoicePlayer.nameOf(window)
  local unit = SPEAKER_UNIT[window]
  if unit then
    local unitName = Compat.resolve("UnitName")
    local en = type(unitName) == "function" and unitName(unit) or nil
    local it = WFJ.UnitNames and type(en) == "string" and WFJ.UnitNames.forUnit(unit, en) or nil
    return it or en
  end
  if window == "ItemTextFrame" then
    local itemName = Compat.resolve("ItemTextGetItem")
    return type(itemName) == "function" and itemName() or nil
  end
  return nil
end

local function playerSex()
  local sex = Compat.resolve("UnitSex")
  return type(sex) == "function" and sex("player") or nil
end

-- Puts the dialog channel back if this addon turned it off. → true when it did
function VoicePlayer.restoreDialog()
  if not (db and db.voiceDialogMuted) then return false end
  db.voiceDialogMuted = nil
  setCVar(DIALOG, "1")
  return true
end

local function muteDialog()
  if not WFJ.Settings.get("voice.muteDialog") or not db or db.voiceDialogMuted then return end
  if tostring(getCVar(DIALOG)) ~= "1" then return end -- off already: the player's choice, left alone
  db.voiceDialogMuted = true
  setCVar(DIALOG, "0")
end

local function silence()
  if not playing then return end
  local stopSound = Compat.resolve("StopSound")
  if type(stopSound) == "function" and playing.handle then stopSound(playing.handle) end
  playing = nil
end

-- Logout (a /reload too) ends the line: the dialog channel must be back on before the client saves its settings.
local function watchLogout()
  if events then return end
  local createFrame = Compat.resolve("CreateFrame")
  if type(createFrame) ~= "function" then return end
  events = createFrame("Frame")
  events:RegisterEvent("PLAYER_LOGOUT")
  events:SetScript("OnEvent", function() VoicePlayer.stop() end)
end

-- Stops the line and empties the queue. → true when something was playing or waiting
function VoicePlayer.stop()
  local had = Q.size() > 0
  silence()
  Q.clear()
  VoicePlayer.restoreDialog()
  if had then notify("stop") end
  return had
end

-- → the key playing, or nil
function VoicePlayer.current()
  return playing and playing.key or nil
end

local startHead -- the queue's head, played (below)

local function finished()
  playing = nil
  Q.pop()
  if Q.current() and allowed() then
    startHead()
    return
  end
  Q.clear()
  VoicePlayer.restoreDialog()
  notify("ended")
end

local function play(item)
  local playSoundFile = Compat.resolve("PlaySoundFile")
  if type(playSoundFile) ~= "function" then return false end
  muteDialog()
  local willPlay, handle = playSoundFile(item.path, CHANNEL)
  if not willPlay then return false end
  tokens = tokens + 1
  local token = tokens
  playing = { handle = handle, key = item.key, token = token }
  VoicePlayer.counts.played = VoicePlayer.counts.played + 1
  watchLogout()
  -- a greeting set to play once per NPC counts as heard once it actually plays
  if item.greeting and item.speaker then WFJ.Voice.markHeard(item.speaker.creature) end
  local timer = Compat.resolve("C_Timer")
  if type(timer) == "table" and type(timer.After) == "function" then
    timer.After((item.seconds or UNKNOWN_LENGTH) + END_MARGIN, function()
      if playing and playing.token == token then finished() end
    end)
  end
  return true
end

-- Plays the queue's head; a file the client refuses is dropped and the next one tried. → true when one started
startHead = function()
  while Q.current() do
    if play(Q.current()) then
      notify("start")
      return true
    end
    VoicePlayer.counts.refused = VoicePlayer.counts.refused + 1
    Q.pop()
  end
  VoicePlayer.restoreDialog()
  notify("ended")
  return false
end

-- Adds a line to the queue (a window's line, the quest log's replay); it plays now when nothing else does.
-- `item`: { key, path, seconds, window, speaker, name, greeting }. → true when it started now
function VoicePlayer.enqueue(item)
  if not allowed() or not Q.push(item) then return false end
  if Q.size() == 1 then return startHead() end
  notify("queued")
  return false
end

-- The next waiting line now (the panel's next button); with none waiting, the line stops. → true when one started
function VoicePlayer.skip()
  if Q.size() == 0 then return false end
  silence()
  Q.pop()
  if Q.current() and allowed() then return startHead() end
  VoicePlayer.stop()
  return false
end

-- State "lineShown" listener. → true when the line started now
function VoicePlayer.onShown(surface, recKey, kind, id)
  if not WFJ.Voice.hasPack() then return false end
  local byKey = WFJ.Voice.KINDS[surface]
  if not (byKey and byKey[recKey]) then return false end -- a title, an objective: never voiced
  local window = windowOf(surface)
  local who = VoicePlayer.speaker(window)
  local path, seconds = WFJ.Voice.decide(surface, recKey, kind, id, who, playerSex())
  if not path then return false end
  return VoicePlayer.enqueue({ key = WFJ.Voice.packKey(kind, id), path = path, seconds = seconds, window = window,
    surface = surface, speaker = who, name = VoicePlayer.nameOf(window),
    greeting = byKey[recKey] == "voice.greeting" })
end

-- → { item = the line playing (the queue's head), playing, waiting = the number of lines after it } for the panel
function VoicePlayer.state()
  return { item = Q.current(), playing = playing ~= nil, waiting = Q.waiting() }
end

-- One line for /fita debug.
function VoicePlayer.describe()
  local V = WFJ.Voice
  if not V.hasPack() then return "no pack" end
  local packs = {}
  for folder, n in pairs(V.packs()) do packs[#packs + 1] = ("%s %d lines"):format(folder, n) end
  table.sort(packs)
  local c = V.counts
  local head = Q.current()
  return ("%s · registered %d invalid %d · matched %d missing %d stale %d · queue %d%s · played %d refused %d")
    :format(table.concat(packs, ", "), c.registered, c.invalid, c.matched, c.missing, c.stale, Q.size(),
      head and (" (" .. tostring(head.key) .. ")") or "", VoicePlayer.counts.played, VoicePlayer.counts.refused)
end

local function stopUnless(on)
  if not on then VoicePlayer.stop() end
end

-- Called by Main after Settings and Voice are loaded. `savedDb` is OFI_DB. Safe without a pack: nothing ever plays.
function VoicePlayer.init(savedDb)
  db = savedDb
  VoicePlayer.restoreDialog() -- a crash during a line left the dialog channel off
  if VoicePlayer.listening then return true end
  VoicePlayer.listening = true
  -- guarded: an error here must not reach the surface that rendered the line
  WFJ.State.on("lineShown", function(...) pcall(VoicePlayer.onShown, ...) end)
  WFJ.State.on("modifier", function(held) if held then VoicePlayer.stop() end end)
  WFJ.State.on("enabled", stopUnless)
  WFJ.State.on("voice", function() -- a voice setting changed
    if not WFJ.Settings.get("voice.enabled") then return VoicePlayer.stop() end
    if not WFJ.Settings.get("voice.muteDialog") then VoicePlayer.restoreDialog() end
  end)
  return true
end
