-- The NPCs' greeting on a click and goodbye: the client's English sounds (the pack's `hellomute`) stay silenced
-- while the pack carries the greetings; opening an NPC's window plays a short Italian greeting in its voice (the
-- pack's `greeters`), closing it a goodbye, a click again and again an annoyed line. A window whose own text is
-- read aloud takes the greeting's place.
local Stub = require("tests.lua.spec.wow_stub")
local E = require("tests.lua.spec.voice_env")

local HELLO_FOLDER = "OldpZ_ForeverITA_Voce_Chat"
local function path(file) return ("Interface\\AddOns\\%s\\Sound\\%s.mp3"):format(HELLO_FOLDER, file) end

describe("greetings on a click", function()
  local WFJ, v, now
  local random = math.random

  local function registerHello(extra)
    local function add(key) return { key .. ".mp3", WFJ.Hash.key(key), 0.8 } end
    local tbl = { format = 3, folder = HELLO_FOLDER, lines = {
      ["n-vx-g1"] = add("n-vx-g1"), ["n-vx-g2"] = add("n-vx-g2"), ["n-vx-g3"] = add("n-vx-g3"),
      ["n-vx-b1"] = add("n-vx-b1"), ["n-vx-b2"] = add("n-vx-b2"),
      ["n-vx-p1"] = add("n-vx-p1"), ["n-vx-p2"] = add("n-vx-p2"),
    }, greeters = { [3233] = "vx" }, hellomute = { 900, 901 } }
    for k, x in pairs(extra or {}) do tbl[k] = x end
    local n = WFJ.Voice.register(tbl)
    WFJ.State.fire("voicePack")
    return n
  end

  before_each(function()
    WFJ = E.setup(true)
    v = Stub.voice
    now = 100
    _G.GetTime = function() return now end
    _G.math.random = function(n) return n and 1 or 0.5 end
    registerHello()
  end)
  after_each(function()
    _G.GetTime = function() return 0 end
    _G.math.random = random
    E.teardown()
  end)

  local function last() return v.sounds[#v.sounds] end

  it("keeps the English greeting files silenced from the pack's load on", function()
    assert.is_true(v.muted[900])
    assert.is_true(v.muted[901])
  end)

  it("greets in the NPC's voice when its window opens, says goodbye when it closes", function()
    Stub.fireAll("MERCHANT_SHOW")
    Stub.fireTimers(0.2)
    assert.are.same({ path = path("n-vx-g1"), channel = "Master" }, last())
    Stub.fireAll("MERCHANT_CLOSED")
    Stub.fireTimers(0.3)
    assert.are.equal(path("n-vx-b1"), last().path)
  end)

  it("says no goodbye when one window of the NPC closes into another (gossip → quest)", function()
    Stub.fireAll("GOSSIP_SHOW")
    Stub.fireTimers(0.2)
    Stub.fireAll("GOSSIP_CLOSED")
    Stub.fireAll("QUEST_DETAIL")
    Stub.fireTimers(0.3)
    Stub.fireTimers(0.2)
    assert.are.equal(1, #v.sounds) -- the greeting only
  end)

  local function visit()
    Stub.fireAll("MERCHANT_SHOW")
    Stub.fireTimers(0.2)
    Stub.fireAll("MERCHANT_CLOSED")
    Stub.fireTimers(0.3)
  end

  it("says an annoyed line on the third click within a few seconds", function()
    for _ = 1, 3 do
      visit()
      now = now + 2
    end
    assert.are.equal(path("n-vx-p1"), v.sounds[#v.sounds - 1].path) -- before the third goodbye
    now = now + 60
    visit()
    assert.are.equal(path("n-vx-g1"), v.sounds[#v.sounds - 1].path) -- calm again
  end)

  it("lets a window whose text is read aloud take the greeting's place", function()
    Stub.fireAll("GOSSIP_SHOW")
    WFJ.VoicePlayer.onShown("gossip", "greeting", "gossip", E.GOSSIP) -- the window's text, voiced
    local before = #v.sounds
    Stub.fireTimers(0.2)
    assert.are.equal(before, #v.sounds)
    assert.are.equal(E.path("g-" .. E.GOSSIP), last().path)
  end)

  it("says nothing for an NPC the pack gives no greeting voice", function()
    Stub.units.npc = { name = "Somebody", guid = "Creature-0-4372-0-1-77-0000ABCDEF" }
    Stub.fireAll("MERCHANT_SHOW")
    Stub.fireTimers(0.2)
    assert.are.equal(0, #v.sounds)
  end)

  it("gives the English back and says nothing when greetings are switched off", function()
    WFJ.Settings.set("voice.hello", false)
    WFJ.State.fire("voice")
    assert.is_nil(v.muted[900])
    Stub.fireAll("MERCHANT_SHOW")
    Stub.fireTimers(0.2)
    assert.are.equal(0, #v.sounds)
  end)
end)
