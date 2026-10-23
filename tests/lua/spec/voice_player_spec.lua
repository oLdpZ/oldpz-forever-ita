-- UI/VoicePlayer: the pack's line plays when the quest, gossip or book window shows its Italian (State "lineShown",
-- fired by UI/Render after a write the client asked for); a line shown while one plays waits its turn.
local Stub = require("tests.lua.spec.wow_stub")
local E = require("tests.lua.spec.voice_env")

describe("UI/VoicePlayer", function()
  local WFJ, db, P, Q, v

  before_each(function()
    WFJ, db = E.setup(true)
    P, Q, v = WFJ.VoicePlayer, WFJ.VoiceQueue, Stub.voice
  end)
  after_each(E.teardown)

  local function hasTimer(delay)
    for _, t in ipairs(v.timers) do if t.delay == delay and not t.cancelled then return true end end
    return false
  end

  local function gossip()
    return P.onShown("gossip", "greeting", "gossip", E.GOSSIP)
  end

  it("plays the offer on the Master channel when the quest window shows its Italian, until its length + 0.5 s",
  function()
    Stub.showDetail()
    assert.are.equal(1, #v.sounds)
    assert.are.same({ path = E.path("2-description"), channel = "Master" }, v.sounds[1])
    assert.are.equal("2-description", P.current())
    assert.is_true(hasTimer(3.5)) -- the pack's length plus the margin
    Stub.fireTimers(3.5)
    assert.is_nil(P.current())
    assert.is_false(P.state().playing)
  end)

  it("fires lineShown only for a write the client asked for: a redraw of the same text plays nothing again",
  function()
    local fired = {}
    WFJ.State.on("lineShown", function(surface, recKey, kind, id) fired[#fired + 1] = { surface, recKey, kind, id } end)
    Stub.showDetail()
    local seen = false
    for _, f in ipairs(fired) do
      if f[2] == "description" then
        assert.are.same({ "questframe.detail", "description", "quest.description", 2 }, f)
        seen = true
      end
    end
    assert.is_true(seen)
    P.stop()
    local n = #fired
    -- the reveal key down and up: the refresh writes the English, then the Italian again, with no client write
    Stub.keys.alt = true
    WFJ.Modifier.refresh()
    Stub.keys.alt = false
    WFJ.Modifier.refresh()
    assert.are.equal("Uccidi Sharptalon al Rifugio di Ventargento.", QuestInfoDescriptionText:GetText())
    assert.are.equal(n, #fired)
    assert.are.equal(1, #v.sounds)
  end)

  it("silences the game's English voice while a line plays and puts it back at the end", function()
    Stub.showDetail()
    assert.are.equal("0", v.cvars.Sound_EnableDialog)
    assert.is_true(db.voiceDialogMuted)
    Stub.fireTimers(3.5)
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    assert.is_nil(db.voiceDialogMuted)
  end)

  it("leaves the English voice alone when the player had it off, or when the setting says so", function()
    v.cvars.Sound_EnableDialog = "0"
    Stub.showDetail()
    assert.is_nil(db.voiceDialogMuted)
    Stub.fireTimers(3.5)
    assert.are.equal("0", v.cvars.Sound_EnableDialog)
    v.cvars.Sound_EnableDialog = "1"
    WFJ.Settings.set("voice.muteDialog", false)
    gossip()
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
  end)

  it("a line shown while one plays waits its turn, once, and plays when that one ends", function()
    Stub.showDetail()
    gossip()
    gossip() -- the gossip window lays its first window out twice
    assert.are.equal(1, #v.sounds)
    assert.are.same({ 2, true, 1 }, { Q.size(), P.state().playing, P.state().waiting })
    Stub.fireTimers(3.5)
    assert.are.equal(2, #v.sounds)
    assert.are.equal(E.path("g-" .. E.GOSSIP), v.sounds[2].path)
    assert.are.equal("0", v.cvars.Sound_EnableDialog) -- still muted: the next line follows straight on
    Stub.fireTimers(3.5)
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    assert.are.equal(0, Q.size())
  end)

  it("skip stops the line and plays the next one; stop empties the queue and puts the English voice back", function()
    Stub.showDetail()
    gossip()
    P.onShown("itemtext", "page", "book", E.BOOK)
    assert.are.equal(2, P.state().waiting)
    assert.is_true(P.skip())
    assert.are.same({ 1 }, v.stopped)
    assert.are.equal(E.path("g-" .. E.GOSSIP), v.sounds[2].path)
    assert.are.equal(1, P.state().waiting)
    table.remove(v.timers, 1).fn() -- the first line's timer is stale: it ends nothing
    assert.are.equal(2, #v.sounds)
    assert.are.equal("g-" .. E.GOSSIP, P.current())
    P.stop()
    assert.are.same({ 1, 2 }, v.stopped)
    assert.are.equal(0, Q.size())
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    Stub.fireTimers()
    assert.are.equal(2, #v.sounds)
  end)

  it("keeps playing when the window closes", function()
    Stub.showDetail()
    QuestFrame:Hide()
    assert.are.equal("2-description", P.current())
    assert.are.equal(0, #v.stopped)
  end)

  it("puts the English voice back at logout, and on the next load after a reload in the middle of a line", function()
    Stub.showDetail()
    Stub.fireAll("PLAYER_LOGOUT")
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    assert.is_nil(db.voiceDialogMuted)
    assert.are.equal(0, Q.size())
    -- a crash: the flag was saved, the CVar left off
    v.cvars.Sound_EnableDialog = "0"
    local saved = { voiceDialogMuted = true }
    WFJ.VoicePlayer.init(saved)
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    assert.is_nil(saved.voiceDialogMuted)
  end)

  local function alt(down)
    Stub.keys.alt = down
    WFJ.Modifier.refresh()
  end

  it("the reveal key going down never stops the line playing", function()
    Stub.showDetail()
    alt(true)
    assert.are.equal("2-description", P.current())
    assert.are.same({}, v.stopped)
    assert.are.equal(1, Q.size())
    alt(false)
    assert.are.equal(1, #v.sounds) -- not started again
  end)

  it("a line the window shows while the reveal key is held waits, and starts when the key is let go", function()
    alt(true)
    Stub.showDetail() -- the window shows the English: the line is still offered to the player
    assert.are.equal("Kill Sharptalon at Silverwind Refuge.", QuestInfoDescriptionText:GetText())
    assert.are.equal(0, #v.sounds)
    assert.are.equal(1, Q.size())
    assert.is_false(P.state().playing)
    gossip() -- a second line held back too
    assert.are.equal(2, Q.size())
    alt(false)
    assert.are.equal("Uccidi Sharptalon al Rifugio di Ventargento.", QuestInfoDescriptionText:GetText())
    assert.are.equal(1, #v.sounds)
    assert.are.equal(E.path("2-description"), v.sounds[1].path)
    assert.are.equal(1, P.state().waiting)
  end)

  it("a line ending while the reveal key is held: the next one waits for the key, then starts", function()
    Stub.showDetail()
    gossip()
    alt(true)
    Stub.fireTimers(3.5)
    assert.are.equal(1, #v.sounds)
    assert.are.equal(1, Q.size())
    assert.are.equal("1", v.cvars.Sound_EnableDialog) -- nothing plays while it waits
    alt(false)
    assert.are.equal(2, #v.sounds)
    assert.are.equal(E.path("g-" .. E.GOSSIP), v.sounds[2].path)
    assert.are.equal("0", v.cvars.Sound_EnableDialog)
  end)

  it("translation switched off stops the line and voices nothing", function()
    WFJ.Settings.set("voice.greeting", "always") -- the same greeting again and again
    gossip()
    WFJ.State.setEnabled(false)
    assert.are.same({ 1 }, v.stopped)
    assert.are.equal(0, Q.size())
    gossip()
    assert.are.equal(1, #v.sounds)
    assert.are.equal(0, Q.size())
  end)

  it("a loading screen ends the line and empties the queue", function()
    Stub.showDetail()
    gossip()
    Stub.fireAll("LOADING_SCREEN_ENABLED")
    assert.are.same({ 1 }, v.stopped)
    assert.are.equal(0, Q.size())
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
  end)

  it("a dialog channel the player switched by hand during the line is left as they chose", function()
    Stub.showDetail()
    v.cvars.Sound_EnableDialog = "1" -- turned back on in the sound options mid-line
    P.stop()
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    assert.is_nil(db.voiceDialogMuted)
  end)

  it("voice switched off stops the line; a kind switched off is not voiced", function()
    gossip()
    WFJ.Settings.set("voice.enabled", false)
    assert.are.same({ 1 }, v.stopped)
    WFJ.Settings.set("voice.enabled", true)
    WFJ.Settings.set("voice.offer", false)
    Stub.showDetail()
    assert.are.equal(1, #v.sounds)
  end)

  it("a greeting heard once is remembered when it starts playing, not when it is queued", function()
    Stub.showDetail()
    gossip()
    P.stop() -- dropped from the queue before it played
    assert.is_nil(db.voiceHeard)
    gossip()
    assert.are.same({ [3233] = true }, db.voiceHeard)
    P.stop()
    gossip() -- once per NPC (the default)
    assert.are.equal(2, #v.sounds)
  end)

  it("a female character's line plays only a female take", function()
    _G.UnitSex = function(unit) return unit == "player" and 3 or 2 end
    WFJ.Voice.register({ format = 3, folder = E.FOLDER .. "_F", lines = {
      ["3-description"] = { "3-description.mp3", WFJ.Hash.key(E.DATA["quest.description"][3].ja), 2.0,
        f = { "3-description_f.mp3", 2.5 } } } })
    P.onShown("questframe.detail", "description", "quest.description", 3)
    assert.are.equal("Interface\\AddOns\\" .. E.FOLDER .. "_F\\Sound\\3-description_f.mp3", v.sounds[1].path)
    assert.is_true(hasTimer(3.0))
  end)

  it("a file the client refuses is dropped and the next line plays", function()
    Stub.showDetail()
    gossip()
    v.willPlay = false
    Stub.fireTimers(3.5)
    assert.are.equal(0, Q.size())
    assert.are.equal("1", v.cvars.Sound_EnableDialog)
    assert.are.equal(1, P.counts.refused)
  end)
end)

describe("UI/VoicePlayer without a voice pack", function()
  local WFJ
  before_each(function() WFJ = E.setup(false) end)
  after_each(E.teardown)

  it("plays nothing and builds no frame", function()
    local before = #Stub.frames
    Stub.showDetail()
    WFJ.VoicePlayer.onShown("gossip", "greeting", "gossip", E.GOSSIP)
    assert.are.equal(0, #Stub.voice.sounds)
    assert.is_nil(E.panel())
    for i = before + 1, #Stub.frames do
      assert.is_not.equal("PlayerModel", Stub.frames[i].kind)
    end
    assert.are.equal(0, WFJ.VoiceQueue.size())
  end)
end)
