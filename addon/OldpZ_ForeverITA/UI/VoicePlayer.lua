-- UI/VoicePlayer.lua: plays the voice pack's file for a line the quest, gossip or book window just showed in Italian.
-- Core/Voice decides which file; this file owns every sound and client-setting call; Core/VoiceQueue holds the
-- order; UI/VoicePanel draws what `state()` reports (State "voiceQueue" on every change).
--   * Start: State "lineShown" (fired by UI/Render after a write the client asked for, never on a refresh). A line
--     shown while one plays waits its turn, never twice for one key (the gossip window lays its first page out
--     twice), and plays when the one before it ends.
--   * The window closing does not stop its line: it plays to its end, and the lines waiting after it.
--   * The reveal key (Alt) never stops a line already playing: a player holds it to compare the English while
--     listening. While it is held no line starts: a line shown then (UI/Render fires "lineShown" for a line the key
--     kept English) or the next one in the queue waits, and starts when the key is let go. A line shown while it was
--     held that the window still shows in English once it is let go (unaligned, a value not filled) never plays.
--   * Stop (the queue emptied): the panel's stop button, /fita voce stop, translation or voice switched off, a
--     loading screen, logout. Skip: the next waiting line now.
--   * Channel "Master", so silencing the dialog channel never silences our own line. PlaySoundFile(path, channel) →
--     willPlay, handle [unverified in the Forever client's own files; the in-game check is in docs/testing/
--     strategy.md]. The client reports no end: a line ends at the pack's length plus a margin.
--   * The game's English voice: while a line plays, Sound_EnableDialog is turned off when it was on, and the fact is
--     kept in OFI_DB.voiceDialogMuted, because the client saves the setting to Config.wtf: a crash in between would
--     otherwise leave the player's NPC voices off for good. It is put back when the queue runs out, on stop, at
--     logout and on the next load. A player who had the dialog channel off keeps it off; one who changed it by hand
--     while the line played keeps what they chose.
--   * An NPC's line in chat (`onSpeech`, from UI/Speech): no window and no queue, one at a time. It never starts
--     while a window's line plays or waits, and a window's line stops it. While one plays a new line is dropped,
--     unless it is a yell or a whisper, which takes over. The chat repeats a line once per tab: a line id plays once.
--   * A race intro (the subtitles' lines, "cinematic.subtitles"): its English narration is one file with the music
--     in it, on no channel a setting turns off. From its first Italian line to CINEMATIC_STOP the race's narration
--     files are silenced (MuteSoundFile) and the race's starting-zone music plays (PlayMusic); a race whose
--     narration file is unknown stays English. Each subtitle plays once per showing (the scroll shows it again).
--   * A game file silenced (an intro's narration, a line in chat's own English voice) is kept in
--     OFI_DB.voiceMutedFiles and given back on stop, at logout and on the next load (a /reload lifts it too).
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
local speaking -- { handle, key, token, mute } while a line in chat plays
local spoken = {} -- chat line id → true: a line shown in several tabs plays once
local spokenCount = 0
local SPOKEN_MAX = 200 -- line ids remembered before the list starts over
-- a yell or a whisper takes over from a line in chat already playing; anything else waits for silence
local URGENT = { MONSTER_YELL = true, MONSTER_WHISPER = true, RAID_BOSS_WHISPER = true }
local intro -- the race row (Core/VoiceIntro) whose narration is silenced, from the first line to CINEMATIC_STOP
local introReady -- (race, surface, recKey) → whether the pack voices the whole intro (below)
local introHeard = {} -- pack key → true: the subtitles played in this showing of the intro
local events -- the loading screen / logout frame, made by the first line queued

-- a line may play or wait: translation and voice on
local function allowed()
  return WFJ.State.enabled and WFJ.Settings.get("voice.enabled") and true or false
end

-- the reveal key held: English shows, so no line starts (one playing goes on)
local function held()
  return WFJ.State.modifierHeld and true or false
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
  if surface == "cinematic.subtitles" then return "CinematicFrame" end -- no speaker: the race's narrator
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

-- Puts the dialog channel back if this addon turned it off. Only while it is still off as we left it ("0"): a
-- player who switched it by hand in the meantime keeps their choice. → true when it did
function VoicePlayer.restoreDialog()
  if not (db and db.voiceDialogMuted) then return false end
  db.voiceDialogMuted = nil
  if tostring(getCVar(DIALOG)) ~= "0" then return false end
  setCVar(DIALOG, "1")
  return true
end

local function muteDialog()
  if not WFJ.Settings.get("voice.muteDialog") or not db or db.voiceDialogMuted then return end
  if tostring(getCVar(DIALOG)) ~= "1" then return end -- off already: the player's choice, left alone
  db.voiceDialogMuted = true
  setCVar(DIALOG, "0")
end

-- Silences game files by id, remembered in OFI_DB.voiceMutedFiles until given back.
local function muteFiles(ids)
  local mute = Compat.resolve("MuteSoundFile")
  if type(mute) ~= "function" or not db or type(ids) ~= "table" then return end
  db.voiceMutedFiles = db.voiceMutedFiles or {}
  for _, id in ipairs(ids) do
    mute(id)
    db.voiceMutedFiles[id] = true
  end
end

-- Gives back the files of `ids`, or every file this addon silenced (nil).
local function unmuteFiles(ids)
  local saved = db and db.voiceMutedFiles
  if type(saved) ~= "table" then return end
  local unmute = Compat.resolve("UnmuteSoundFile")
  local list = ids
  if list == nil then
    list = {}
    for id in pairs(saved) do list[#list + 1] = id end
  end
  for _, id in ipairs(list) do
    if saved[id] and type(unmute) == "function" then unmute(id) end
    saved[id] = nil
  end
  if next(saved) == nil then db.voiceMutedFiles = nil end
end

local function silence()
  if not playing then return end
  local stopSound = Compat.resolve("StopSound")
  if type(stopSound) == "function" and playing.handle then stopSound(playing.handle) end
  playing = nil
end

-- The line in chat ends or is cut: its own English file is given back.
local function stopSpeech()
  if not speaking then return false end
  local stopSound = Compat.resolve("StopSound")
  if type(stopSound) == "function" and speaking.handle then stopSound(speaking.handle) end
  unmuteFiles(speaking.mute)
  speaking = nil
  return true
end

-- The intro is over (or stopped): its narration and the game's own music come back.
local function endIntro()
  introHeard = {}
  if not intro then return end
  unmuteFiles(intro.files)
  local stopMusic = Compat.resolve("StopMusic")
  if type(stopMusic) == "function" then stopMusic() end
  intro = nil
end

local function startIntro(race)
  if intro then return end
  intro = race
  muteFiles(race.files)
  local playMusic = Compat.resolve("PlayMusic")
  if type(playMusic) == "function" then playMusic(race.music) end
end

-- A loading screen ends the line and the queue (the player is somewhere else now); logout (a /reload too) as well:
-- the dialog channel must be back on before the client saves its settings. LOADING_SCREEN_ENABLED [likely on
-- Forever; in-game check: a portal or a hearthstone stops the voice]. A cinematic's end ends its intro; its start
-- forgets the subtitles heard in the last showing.
local function watchEvents()
  if events then return end
  local createFrame = Compat.resolve("CreateFrame")
  if type(createFrame) ~= "function" then return end
  events = createFrame("Frame")
  events:RegisterEvent("PLAYER_LOGOUT")
  events:RegisterEvent("LOADING_SCREEN_ENABLED")
  events:RegisterEvent("CINEMATIC_START")
  events:RegisterEvent("CINEMATIC_STOP")
  events:SetScript("OnEvent", function(_, event)
    if event == "CINEMATIC_START" then
      introHeard = {}
    elseif event == "CINEMATIC_STOP" then
      -- the intro's lines stop with it (Esc skips the cinematic); a window's line was not part of it
      local head = Q.current()
      if head and head.intro then VoicePlayer.stop() else endIntro() end
    else
      VoicePlayer.stop()
    end
  end)
end

-- Stops the line, the line in chat and the intro, and empties the queue. → true when something was playing or
-- waiting
function VoicePlayer.stop()
  local had = Q.size() > 0
  silence()
  Q.clear()
  had = stopSpeech() or had
  endIntro()
  unmuteFiles()
  VoicePlayer.restoreDialog()
  if had then notify("stop") end
  return had
end

-- → the key playing, or nil
function VoicePlayer.current()
  return playing and playing.key or nil
end

local startHead -- the queue's head, played (below)

-- The head is done (ended or skipped): the next line plays, or waits for the reveal key, or the queue is over.
local function advance()
  playing = nil
  Q.pop()
  if Q.current() and allowed() then
    if not held() then return startHead() end
    VoicePlayer.restoreDialog() -- nothing plays while the next line waits
    notify("waiting")
    return false
  end
  Q.clear()
  VoicePlayer.restoreDialog()
  notify("ended")
  return false
end

local function play(item)
  local playSoundFile = Compat.resolve("PlaySoundFile")
  if type(playSoundFile) ~= "function" then return false end
  muteDialog()
  -- the intro's English narration goes quiet before our narrator starts, and stays so until the cinematic ends
  if item.intro then startIntro(item.intro) end
  local willPlay, handle = playSoundFile(item.path, CHANNEL)
  if not willPlay then return false end
  if item.intro then introHeard[item.key] = true end
  tokens = tokens + 1
  local token = tokens
  playing = { handle = handle, key = item.key, token = token }
  VoicePlayer.counts.played = VoicePlayer.counts.played + 1
  -- a greeting set to play once per NPC counts as heard once it actually plays
  if item.greeting and item.speaker then WFJ.Voice.markHeard(item.speaker.creature) end
  local timer = Compat.resolve("C_Timer")
  if type(timer) == "table" and type(timer.After) == "function" then
    timer.After((item.seconds or UNKNOWN_LENGTH) + END_MARGIN, function()
      if playing and playing.token == token then advance() end
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

-- Adds a line to the queue (a window's line, the quest log's replay); it plays now when nothing else does and the
-- reveal key is up. `item`: { key, path, seconds, window, speaker, name, greeting }. → true when it started now
function VoicePlayer.enqueue(item)
  if not allowed() or not Q.push(item) then return false end
  watchEvents()
  stopSpeech() -- a window's line goes before what an NPC says in chat
  if Q.size() == 1 and not held() then return startHead() end
  notify("queued")
  return false
end

-- The next waiting line now (the panel's next button); with none waiting, the line stops and the panel goes after
-- its usual linger. → true when one started
function VoicePlayer.skip()
  if Q.size() == 0 then return false end
  silence()
  return advance()
end

-- The lines shown while the reveal key was held, once it is let go: UI/Render's refresh (a "modifier" listener added
-- before ours) has written each one again, so a line whose record now shows the Italian keeps its place and one the
-- window left English (unaligned, a value it could not fill, kept English) is dropped: its voice would read Italian
-- over an English window. → the number dropped
local function settleHeld()
  local SS, dropped = WFJ.SurfaceState, 0
  for i = #Q.items, 1, -1 do
    local item = Q.items[i]
    if item.heldKey then
      local rec = SS and SS.get(item.surface, item.heldKey)
      if rec and rec.applied ~= nil then
        item.heldKey = nil
      else
        table.remove(Q.items, i)
        dropped = dropped + 1
      end
    end
  end
  return dropped
end

-- The reveal key let go: the line that waited for it starts, when its window now shows it in Italian.
local function released()
  if not allowed() or held() then return false end
  if settleHeld() > 0 and (playing or not Q.current()) then
    if not playing then VoicePlayer.restoreDialog() end
    notify(Q.current() and "queued" or "ended")
  end
  if playing or not Q.current() then return false end
  return startHead()
end

-- An intro silences its English narration whole, so it is voiced only when every subtitle of the race that ships
-- Italian has a take that matches it: one line left without a voice would be heard as silence. An id with neither
-- Italian nor a take is no subtitle (the ranges have gaps).
introReady = function(race, surface, recKey)
  local V, sex = WFJ.Voice, playerSex()
  for n = race.first, race.last do
    local path, why = V.decide(surface, recKey, "ui", "BroadcastText:" .. n, nil, sex, true)
    if not path and not (why == "missing" and not V.shipped("ui", "BroadcastText:" .. n)) then return false end
  end
  return true
end

-- State "lineShown" listener. → true when the line started now
function VoicePlayer.onShown(surface, recKey, kind, id)
  if not WFJ.Voice.hasPack() then return false end
  local setting = WFJ.Voice.kindSetting(surface, recKey)
  if not setting then return false end -- a title, an objective: never voiced
  local key = WFJ.Voice.packKey(kind, id)
  local race
  if setting == "voice.intro" then
    -- an intro's line: once per showing, and only for a race whose English narration can be silenced
    race = key and WFJ.VoiceIntro.of(tonumber(key:sub(3)))
    if not race or #race.files == 0 or introHeard[key] then return false end
    if intro ~= race and not introReady(race, surface, recKey) then return false end
  end
  local window = windowOf(surface)
  local who = VoicePlayer.speaker(window)
  local path, seconds = WFJ.Voice.decide(surface, recKey, kind, id, who, playerSex())
  if not path then return false end
  -- shown while the reveal key is held, the line is still English: `heldKey` names its record, read when the key
  -- is let go (settleHeld)
  return VoicePlayer.enqueue({ key = key, path = path, seconds = seconds, window = window,
    surface = surface, speaker = who, name = VoicePlayer.nameOf(window), intro = race,
    greeting = setting == "voice.greeting", heldKey = held() and recKey or nil })
end

local function endSpeech(token)
  if speaking and speaking.token == token then stopSpeech() end
end

-- What an NPC said in chat (UI/Speech, a line it showed in Italian): `key` its gossip key, `chatType` the chat
-- type's name (MONSTER_SAY …), `creature` the speaker's creature id from the line's GUID, `lineID` the chat's id
-- of the line. Plays at once or not at all (see the file's head). → true when it started
function VoicePlayer.onSpeech(key, chatType, creature, lineID)
  if not WFJ.Voice.hasPack() or not allowed() or type(key) ~= "string" then return false end
  if lineID ~= nil then
    if spoken[lineID] then return false end
    if spokenCount >= SPOKEN_MAX then spoken, spokenCount = {}, 0 end
    spoken[lineID], spokenCount = true, spokenCount + 1
  end
  if Q.size() > 0 or held() then return false end
  if speaking and not URGENT[chatType] then return false end
  local path, seconds, mute = WFJ.Voice.decide("speech", "line", "speech", key,
    creature and { creature = creature } or nil, playerSex())
  if not path then return false end
  local playSoundFile = Compat.resolve("PlaySoundFile")
  if type(playSoundFile) ~= "function" then return false end
  stopSpeech()
  muteFiles(mute)
  local willPlay, handle = playSoundFile(path, CHANNEL)
  if not willPlay then
    unmuteFiles(mute)
    return false
  end
  watchEvents()
  tokens = tokens + 1
  local token = tokens
  speaking = { handle = handle, key = key, token = token, mute = mute }
  VoicePlayer.counts.played = VoicePlayer.counts.played + 1
  local timer = Compat.resolve("C_Timer")
  if type(timer) == "table" and type(timer.After) == "function" then
    timer.After((seconds or UNKNOWN_LENGTH) + END_MARGIN, function() endSpeech(token) end)
  end
  return true
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
  unmuteFiles() -- or a game file silenced
  if VoicePlayer.listening then return true end
  VoicePlayer.listening = true
  -- guarded: an error here must not reach the surface that rendered the line
  WFJ.State.on("lineShown", function(...) pcall(VoicePlayer.onShown, ...) end)
  WFJ.State.on("modifier", function(down) if not down then pcall(released) end end)
  WFJ.State.on("enabled", stopUnless)
  WFJ.State.on("voice", function() -- a voice setting changed
    if not WFJ.Settings.get("voice.enabled") then return VoicePlayer.stop() end
    if not WFJ.Settings.get("voice.muteDialog") then VoicePlayer.restoreDialog() end
  end)
  return true
end
