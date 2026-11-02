-- UI/VoiceQuestLog.lua: the quest log's play button and the remembered speaker.
--   * The quest log (the world map's quest pane) shows a quest's text but plays nothing by itself (opening the log is
--     browsing). A play button at the right end of the details' top bar plays that quest's offer as the pane shows
--     it, through UI/VoicePlayer's queue like any other line (it waits while another line plays). It shows only for
--     a quest whose description has a file. [verified: forever 1.60.1.70245 mainline/questmapframe.xml 701–720
--     (DetailsFrame.BackFrame, 307 × 52, BackButton at its left); questmapframe.lua:1044–1056
--     (QuestMapFrame_ShowQuestDetails)]
--   * Who showed each quest line, remembered when the quest window shows it (State "questShown", fired by
--     UI/QuestFrame whether or not the line is translated), while a voice pack is installed:
--     OFI_DB.voiceSpeakers["<quest id>-<field>"] = { c = creature id, s = UnitSex, n = name }, as the client showed
--     them; seeing the NPC again refreshes it. At most one entry per quest line the game has. The log's replays take
--     their head (by creature id), name and voice from it. A quest taken before this existed, or from an item or an
--     object, has none: no head, and the quest's title as the name.
-- Without a voice pack nothing is hooked, built or saved: the pack's arrival (State "voicePack") installs the hook.
-- The button follows forever-vo's ForeverVO/UI/QuestLog.lua (MIT License; see ATTRIBUTION.md).
local _, WFJ = ...
local QuestLog = {}
WFJ.VoiceQuestLog = QuestLog

local Compat = WFJ.Compat

local LOG_SURFACE = "questmap.info" -- UI/QuestMap's records for the details pane's QuestInfo text
local FIELD_OF = { detail = "description", progress = "progress", reward = "completion" }
-- the details pane's top bar: the Forever path first, then the older one (UI/QuestMap's candidates)
local BARS = { "QuestMapFrame.QuestsFrame.DetailsFrame", "QuestMapFrame.DetailsFrame" }
local BUTTON_SIZE, BUTTON_LIFT = 28, 10
local ICON_PLAY = "Interface\\Buttons\\UI-SpellbookIcon-NextPage-Up" -- the client's own arrow
local ICON_HIGHLIGHT = "Interface\\Buttons\\UI-Common-MouseHilight"

local db -- OFI_DB
local button, hooked

local function details()
  for _, path in ipairs(BARS) do
    local d = Compat.resolve(path)
    if type(d) == "table" then return d end
  end
  return nil
end

local function rememberSpeaker(questID, panelName)
  local field = FIELD_OF[panelName]
  -- only with a voice pack: without one nothing is ever replayed, so nothing is kept
  if not field or type(questID) ~= "number" or type(db) ~= "table" or not WFJ.Voice.hasPack() then return end
  local P = WFJ.VoicePlayer
  local who = P.speaker("QuestFrame")
  if not who then return end
  if type(db.voiceSpeakers) ~= "table" then db.voiceSpeakers = {} end
  db.voiceSpeakers[questID .. "-" .. field] = { c = who.creature, s = who.sex, n = P.nameOf("QuestFrame") }
end

-- → the remembered speaker of a quest line, or nil
function QuestLog.rememberedSpeaker(questID, field)
  local all = type(db) == "table" and db.voiceSpeakers
  return type(all) == "table" and type(questID) == "number" and all[questID .. "-" .. field] or nil
end

-- → the queue item for the pane's description, or nil when it has no file (or nothing is shown)
local function logLine()
  local rec = WFJ.SurfaceState and WFJ.SurfaceState.get(LOG_SURFACE, "description")
  local m = rec and rec.meta
  if not m or type(rec.applied) ~= "string" then return nil end
  -- the pane's quest: its own id, also for a description keyed by its English (m.id is then that key)
  local d = details()
  local qid = d and d.questID
  if type(qid) ~= "number" then qid = type(m.id) == "number" and m.id or nil end
  local saw = QuestLog.rememberedSpeaker(qid, "description")
  local who = saw and { creature = saw.c, sex = saw.s } or nil
  local sex = Compat.resolve("UnitSex")
  local path, seconds = WFJ.Voice.decide("questframe.detail", "description", m.kind, m.id, who,
    type(sex) == "function" and sex("player") or nil, true)
  if not path then return nil end
  local title = WFJ.SurfaceState.get(LOG_SURFACE, "title")
  local name = saw and saw.n or (title and type(title.applied) == "string" and title.applied or nil)
  return { key = WFJ.Voice.packKey(m.kind, m.id), path = path, seconds = seconds, window = "QuestMapFrame",
    surface = "questframe.detail", speaker = who, name = name }
end

-- The button as things stand: shown only for a description with a file.
function QuestLog.refresh()
  if not button then return end
  if logLine() then button:Show() else button:Hide() end
end

local function click()
  local item = logLine()
  if item then WFJ.VoicePlayer.enqueue(item) end
end

local function setup()
  if button then return end
  local d = details()
  local bar = d and d.BackFrame
  local createFrame = Compat.resolve("CreateFrame")
  if type(bar) ~= "table" or type(createFrame) ~= "function" then return end
  button = createFrame("Button", nil, bar)
  button:SetSize(BUTTON_SIZE, BUTTON_SIZE)
  button:SetPoint("RIGHT", bar, "RIGHT", -8, 4)
  button:SetFrameLevel(bar:GetFrameLevel() + BUTTON_LIFT)
  button:SetNormalTexture(ICON_PLAY)
  button:SetHighlightTexture(ICON_HIGHLIGHT, "ADD")
  button:SetScript("OnClick", click)
  button:Hide()
end

-- → the button, or nil (for the specs)
function QuestLog.button()
  return button
end

-- Installs the details pane's post-hook, once, when a pack is there. → true when hooked
function QuestLog.enable()
  if hooked or not WFJ.Voice.hasPack() then return hooked or false end
  local hook = Compat.resolve("hooksecurefunc")
  if type(hook) ~= "function" or type(Compat.resolve("QuestMapFrame_ShowQuestDetails")) ~= "function" then
    return false
  end
  hooked = true
  hook("QuestMapFrame_ShowQuestDetails", function()
    pcall(function() setup(); QuestLog.refresh() end)
  end)
  return true
end

-- Called by Main after VoicePlayer. `savedDb` is OFI_DB.
function QuestLog.init(savedDb)
  db = savedDb
  if QuestLog.listening then return true end
  QuestLog.listening = true
  WFJ.State.on("questShown", function(questID, panelName) pcall(rememberSpeaker, questID, panelName) end)
  WFJ.State.on("voicePack", function() pcall(QuestLog.enable) end)
  WFJ.State.on("voice", function() pcall(QuestLog.refresh) end)
  QuestLog.enable() -- a pack that registered before this ran
  return true
end
