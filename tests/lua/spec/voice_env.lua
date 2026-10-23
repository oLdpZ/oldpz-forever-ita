-- The voice player, panel and quest-log button specs' shared setup: the quest window through UI/QuestFrame (so a line
-- reaches the player the way the client shows it: Render.show → State "lineShown"), the gossip and book windows as
-- bare frames (their lines are fired straight at the player), the quest log's details pane, and a fake voice pack.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")

local E = {}

E.FILES = { "Core/Const.lua", "Core/Compat.lua", "Core/State.lua", "Core/Voice.lua", "Core/VoiceQueue.lua",
  "Core/Settings.lua", "Core/Modifier.lua", "Core/Translator.lua", "Core/SurfaceState.lua", "Core/Normalize.lua",
  "Core/Hash.lua", "Core/Collector.lua", "Core/UIStringKeys.lua", "Core/UIStrings.lua",
  "UI/Font.lua", "UI/Frames.lua", "UI/Render.lua", "UI/ButtonText.lua", "UI/Labels.lua", "UI/QuestFrame.lua",
  "UI/OptionsText.lua", "UI/VoicePlayer.lua", "UI/VoicePanelHead.lua", "UI/VoicePanel.lua", "UI/VoiceQuestLog.lua" }

E.FOLDER = "OldpZ_ForeverITA_Voce"
E.GOSSIP = "0123456789abcdef"
E.BOOK = "fedcba9876543210"

-- the shipped Italian, raw
E.DATA = {
  ["quest.title"] = { [2] = { ja = "Gli artigli di Sharptalon", status = "." },
    [3] = { ja = "Un'altra missione", status = "." } },
  ["quest.description"] = { [2] = { ja = "Uccidi Sharptalon al Rifugio di Ventargento.", status = "." },
    [3] = { ja = "Una seconda missione.", status = "." }, [4] = { ja = "Una missione senza voce.", status = "." } },
  ["quest.objectives"] = { [2] = { ja = "Porta l'artiglio di Sharptalon.", status = "." } },
  ["quest.completion"] = { [2] = { ja = "Ben fatto.", status = "." } },
  ["quest.progress"] = { [2] = { ja = "Allora?", status = "." } },
  gossip = { [E.GOSSIP] = { ja = "Salute, viandante.", status = "." } },
  book = { [E.BOOK] = { ja = "La prima pagina del diario.", status = "." } },
}

E.NPC = { name = "Senani Thunderheart", guid = "Creature-0-4372-0-1-3233-0000ABCDEF" } -- creature 3233

function E.path(key) return ("Interface\\AddOns\\%s\\Sound\\%s.mp3"):format(E.FOLDER, key) end

local function lines(WFJ)
  local out = {}
  local function add(key, ja) out[key] = { key .. ".mp3", WFJ.Hash.key(ja), 3.0 } end
  add("2-description", E.DATA["quest.description"][2].ja)
  add("2-progress", E.DATA["quest.progress"][2].ja)
  add("2-completion", E.DATA["quest.completion"][2].ja)
  add("3-description", E.DATA["quest.description"][3].ja)
  add("g-" .. E.GOSSIP, E.DATA.gossip[E.GOSSIP].ja)
  add("b-" .. E.BOOK, E.DATA.book[E.BOOK].ja)
  return out
end

-- The pack's Register.lua, as Main's global does it: register, then tell the UI a pack arrived.
function E.register(WFJ)
  local n = WFJ.Voice.register({ format = 3, folder = E.FOLDER, lines = lines(WFJ) })
  if n > 0 then WFJ.State.fire("voicePack") end
  return n
end

function E.setQuest(id)
  Stub.quest = { id = id, title = "Sharptalon's Claw", description = "Kill Sharptalon at Silverwind Refuge.",
    objectives = "Bring Sharptalon's Claw.", progress = "Did you get it?", completion = "Well done." }
end

-- → WFJ, db
function E.setup(withPack)
  Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
  Stub.installQuestAPI(); Stub.installTooltipAPI()
  Stub.installVoiceAPI()
  CreateFrame("Frame", "UIParent")
  CreateFrame("Frame", "GossipFrame")
  CreateFrame("Frame", "ItemTextFrame")
  _G.ItemTextGetItem = function() return "Diario di Jitters" end
  Stub.units.questnpc = { name = E.NPC.name, guid = E.NPC.guid }
  Stub.units.npc = { name = E.NPC.name, guid = E.NPC.guid }
  -- the quest log's details pane (questmapframe.xml: QuestsFrame.DetailsFrame.BackFrame)
  local map = CreateFrame("Frame", "QuestMapFrame")
  map.QuestsFrame = CreateFrame("Frame", nil, map)
  local details = CreateFrame("Frame", nil, map.QuestsFrame)
  map.QuestsFrame.DetailsFrame = details
  details.BackFrame = CreateFrame("Frame", nil, details)
  _G.QuestMapFrame_ShowQuestDetails = function(id) details.questID = id end
  local WFJ = H.loadChunks(E.FILES)
  local S = WFJ.Settings
  WFJ.Compat.init(function(name) return _G[name] end)
  local db = S.load(nil, 1, {})
  local function lookup(kind, id) return E.DATA[kind] and E.DATA[kind][id] end
  WFJ.Render.init(WFJ.Translator.new({
    enabled = function() return WFJ.State.enabled end,
    areaEnabled = WFJ.State.areaEnabled,
    modifierHeld = WFJ.Modifier.isDown,
    lookup = lookup,
    marker = function(n) return S.get("marker." .. n) end,
  }))
  WFJ.Voice.init({ lookup = lookup, hash = WFJ.Hash.key, setting = S.get, revealed = WFJ.Modifier.isDown,
    enabled = function() return WFJ.State.enabled end, db = db })
  assert(WFJ.QuestFrame.init())
  assert(WFJ.VoicePlayer.init(db))
  assert(WFJ.VoicePanel.init())
  assert(WFJ.VoiceQuestLog.init(db))
  if withPack then E.register(WFJ) end
  E.setQuest(2)
  return WFJ, db
end

function E.teardown()
  Stub.removeVoiceAPI()
  _G.UIParent, _G.GossipFrame, _G.ItemTextFrame, _G.ItemTextGetItem, _G.WFJVoicePanel = nil, nil, nil, nil, nil
  _G.QuestMapFrame, _G.QuestMapFrame_ShowQuestDetails = nil, nil
  Stub.units.questnpc, Stub.units.npc = nil, nil
end

-- the panel's frame (nil until the first voiced line builds it)
function E.panel() return _G.WFJVoicePanel end

return E
