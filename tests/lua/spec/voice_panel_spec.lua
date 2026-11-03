-- UI/VoicePanel (the small panel beside the window that showed the line: the speaker's 3D head, its name, stop, next
-- and "+N"), UI/VoicePanelHead, and UI/VoiceQuestLog (the quest log's play button and the remembered speaker).
local Stub = require("tests.lua.spec.wow_stub")
local E = require("tests.lua.spec.voice_env")

local function child(frame, kind)
  for _, f in ipairs(Stub.frames) do
    if f.parent == frame and f.kind == kind then return f end
  end
end

describe("UI/VoicePanel", function()
  local WFJ, P, v

  before_each(function()
    WFJ = E.setup(true)
    P, v = WFJ.VoicePlayer, Stub.voice
  end)
  after_each(E.teardown)

  local function gossip() return P.onShown("gossip", "greeting", "gossip", E.GOSSIP) end

  it("is built by the first voiced line, beside the window that showed it, about 220 × 64", function()
    assert.is_nil(E.panel())
    Stub.showDetail()
    local f = E.panel()
    assert.is_table(f)
    assert.is_true(f:IsShown())
    assert.are.same({ 220, 64 }, f.size)
    assert.are.same({ "TOPLEFT", QuestFrame, "TOPRIGHT", 4, 0 }, f.point)
    assert.are.equal(E.NPC.name, WFJ.VoicePanel.nameText())
    assert.is_false(WFJ.VoicePanel.waitingShown())
  end)

  it("shows the speaker's 3D head from the unit on screen, else from the creature id, talking while it plays",
  function()
    Stub.showDetail()
    local model = child(E.panel(), "PlayerModel")
    assert.are.equal("questnpc", model.unit)
    assert.are.equal(WFJ.VoicePanelHead.TALK_ANIMATION, model.animation)
    P.stop()
    Stub.units.npc = { name = "Kerra", guid = "Creature-0-4372-0-1-3234-0000ABCDEF" }
    gossip()
    model = child(E.panel(), "PlayerModel")
    assert.are.equal("npc", model.unit)
    assert.are.equal("Kerra", WFJ.VoicePanel.nameText())
    -- another NPC now answers to "npc": the speaker is loaded by its creature id
    Stub.units.npc = { name = "Someone Else", guid = "Creature-0-4372-0-1-99-0000ABCDEF" }
    WFJ.VoicePanelHead.load(WFJ.VoicePanel.head(), WFJ.VoiceQueue.current())
    assert.are.equal(3234, model.creature)
  end)

  it("a book has no speaker: a book icon instead of a head, the book's name", function()
    P.onShown("itemtext", "page", "book", E.BOOK)
    local f = E.panel()
    assert.are.same({ "TOPLEFT", _G.ItemTextFrame, "TOPRIGHT", 4, 0 }, f.point)
    assert.are.equal("Diario di Jitters", WFJ.VoicePanel.nameText())
    local h = WFJ.VoicePanel.head()
    assert.is_true(h.icon.shown)
    assert.are.equal(0, h.model.alpha)
  end)

  it("shows +N for the lines waiting; next plays the following one, stop empties the queue and hides it", function()
    Stub.showDetail()
    gossip()
    P.onShown("itemtext", "page", "book", E.BOOK)
    assert.is_true(WFJ.VoicePanel.waitingShown())
    assert.are.equal("+2", WFJ.VoicePanel.waitingText())
    WFJ.VoicePanel.buttons().skip:click()
    assert.are.equal(E.path("g-" .. E.GOSSIP), v.sounds[2].path)
    assert.are.equal("+1", WFJ.VoicePanel.waitingText())
    assert.are.same({ "TOPLEFT", GossipFrame, "TOPRIGHT", 4, 0 }, E.panel().point)
    WFJ.VoicePanel.buttons().stop:click()
    assert.are.equal(0, WFJ.VoiceQueue.size())
    assert.is_false(E.panel():IsShown())
  end)

  it("stays where it was when the window closes, until the line ends, then goes 3 s later", function()
    Stub.showDetail()
    QuestFrame:Hide()
    assert.is_true(E.panel():IsShown())
    Stub.fireTimers(3.5) -- the line ends
    assert.is_true(E.panel():IsShown())
    Stub.fireTimers(3)
    assert.is_false(E.panel():IsShown())
  end)

  it("next on the last line stops it, and the panel goes after its linger", function()
    Stub.showDetail()
    WFJ.VoicePanel.buttons().skip:click()
    assert.are.same({ 1 }, v.stopped)
    assert.are.equal(0, WFJ.VoiceQueue.size())
    assert.is_true(E.panel():IsShown())
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    Stub.fireTimers(3)
    assert.is_false(E.panel():IsShown())
  end)

  it("a new line before the 3 s are up keeps it on screen", function()
    Stub.showDetail()
    Stub.fireTimers(3.5)
    gossip()
    Stub.fireTimers(3)
    assert.is_true(E.panel():IsShown())
  end)

  it("voice.panel = nohead: name and buttons, no head nor book icon, a narrower panel", function()
    WFJ.Settings.set("voice.panel", "nohead")
    Stub.showDetail()
    local f, h = E.panel(), WFJ.VoicePanel.head()
    assert.is_true(f:IsShown())
    assert.are.same({ 220 - 56 - 6, 64 }, f.size)
    assert.are.equal(0, h.model.alpha)
    assert.is_false(h.icon.shown)
    assert.are.equal(E.NPC.name, WFJ.VoicePanel.nameText())
    Stub.fireTimers(0.7) -- the model settles: still hidden
    assert.are.equal(0, h.model.alpha)
    P.onShown("itemtext", "page", "book", E.BOOK)
    WFJ.VoicePanel.buttons().skip:click()
    assert.is_false(h.icon.shown)
    -- back to the full panel while a line plays: the head comes back
    WFJ.Settings.set("voice.panel", "full")
    assert.are.same({ 220, 64 }, f.size)
    assert.is_true(h.icon.shown)
  end)

  it("voice.panel = none: the line plays, no panel; switching it off mid-line hides the panel", function()
    WFJ.Settings.set("voice.panel", "none")
    Stub.showDetail()
    assert.are.equal(1, #v.sounds)
    assert.is_true(E.panel() == nil or not E.panel():IsShown())
    WFJ.Settings.set("voice.panel", "full")
    gossip()
    assert.is_true(E.panel():IsShown())
    WFJ.Settings.set("voice.panel", "none")
    assert.is_false(E.panel():IsShown())
  end)
end)

describe("UI/VoiceQuestLog", function()
  local WFJ, db, v

  before_each(function()
    WFJ, db = E.setup(true)
    v = Stub.voice
  end)
  after_each(E.teardown)

  -- the quest log's details pane shows quest `id`'s description (UI/QuestMap's record on questmap.info)
  local function showLog(id)
    local fs = Stub.fontString("Kill Sharptalon at Silverwind Refuge.")
    WFJ.Render.show("questmap.info", "description", fs, "Kill Sharptalon at Silverwind Refuge.", "quests",
      "quest.description", id)
    _G.QuestMapFrame_ShowQuestDetails(id)
  end

  it("remembers who showed each quest line in the quest window", function()
    Stub.showDetail()
    assert.are.same({ c = 3233, s = 2, n = E.NPC.name }, db.voiceSpeakers["2-description"])
  end)

  it("shows the play button only for a quest whose description has audio, and plays it like an offer", function()
    showLog(4) -- no file for quest 4
    local b = WFJ.VoiceQuestLog.button()
    assert.is_table(b)
    assert.is_false(b:IsShown())
    assert.are.equal(0, #v.sounds) -- opening the log plays nothing by itself
    showLog(2)
    assert.is_true(b:IsShown())
    assert.are.equal(0, #v.sounds)
    b:click()
    assert.are.equal(E.path("2-description"), v.sounds[1].path)
    -- through the queue: a line playing makes it wait
    WFJ.VoicePlayer.stop()
    WFJ.VoicePlayer.onShown("gossip", "greeting", "gossip", E.GOSSIP)
    b:click()
    assert.are.equal(1, WFJ.VoicePlayer.state().waiting)
  end)

  it("the replay takes the remembered speaker's head and name", function()
    Stub.showDetail()
    WFJ.VoicePlayer.stop()
    QuestFrame:Hide()
    Stub.units.questnpc = nil
    showLog(2)
    WFJ.VoiceQuestLog.button():click()
    local item = WFJ.VoiceQueue.current()
    assert.are.equal(3233, item.speaker.creature)
    assert.are.equal(E.NPC.name, item.name)
  end)
end)

describe("the voice panel and the quest log without a pack", function()
  local WFJ, db
  before_each(function() WFJ, db = E.setup(false) end)
  after_each(E.teardown)

  it("build nothing, hook nothing and remember nothing", function()
    Stub.showDetail()
    _G.QuestMapFrame_ShowQuestDetails(2)
    assert.is_nil(E.panel())
    assert.is_nil(WFJ.VoiceQuestLog.button())
    assert.is_nil(Stub.hooks.QuestMapFrame_ShowQuestDetails)
    assert.is_nil(db.voiceSpeakers)
  end)
end)
