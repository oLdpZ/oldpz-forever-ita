-- The NPC lines in chat and the race intros: Core/Voice decides them like any line (`s-` keys read the gossip
-- Italian, `i-` keys the subtitle's UI row); UI/VoicePlayer plays a line in chat on its own, one at a time, never
-- over a window's line, and an intro under the zone's music with the game's English narration silenced.
local Stub = require("tests.lua.spec.wow_stub")
local E = require("tests.lua.spec.voice_env")

describe("voice in chat and intros", function()
  local WFJ, db, P, V, v

  before_each(function()
    WFJ, db = E.setup(true)
    E.registerChat(WFJ)
    P, V, v = WFJ.VoicePlayer, WFJ.Voice, Stub.voice
  end)
  after_each(function()
    _G.UnitLevel, _G.UnitXP = nil, nil
    E.teardown()
  end)

  local function say(key, chatType, lineID)
    return P.onSpeech(key, chatType or "MONSTER_SAY", 3233, lineID or key)
  end

  local function subtitle(id)
    return P.onShown("cinematic.subtitles", "line.1", "ui", id)
  end

  describe("Core/Voice", function()
    it("keys a line in chat by its gossip key and an intro line by its BroadcastText id", function()
      assert.are.equal("s-" .. E.GOSSIP, V.packKey("speech", E.GOSSIP))
      assert.are.equal("i-329309", V.packKey("ui", E.INTRO1))
      assert.is_nil(V.packKey("ui", "BroadcastText:abc"))
      assert.is_nil(V.packKey("ui", "QUEST_LOG"))
    end)

    it("reads a line in chat's Italian from the gossip rows and an intro's from the UI rows", function()
      assert.are.equal(E.chatPath("s-" .. E.GOSSIP), V.decide("speech", "line", "speech", E.GOSSIP))
      assert.are.equal(E.chatPath("i-329309"), V.decide("cinematic.subtitles", "line.3", "ui", E.INTRO1))
    end)

    it("hands back the English files a line silences", function()
      local _, _, mute = V.decide("speech", "line", "speech", E.SHOUT)
      assert.are.same({ E.ENGLISH_SHOUT }, mute)
    end)

    it("is off when its setting is", function()
      WFJ.Settings.set("voice.speech", false)
      WFJ.Settings.set("voice.intro", false)
      assert.are.same({ nil, "off" }, { V.decide("speech", "line", "speech", E.GOSSIP) })
      assert.are.same({ nil, "off" }, { V.decide("cinematic.subtitles", "line.1", "ui", E.INTRO1) })
    end)

    it("drops a pack entry whose silenced files are not ids", function()
      local _, bad = V.register({ format = 3, folder = "OldpZ_ForeverITA_Voce_X", lines = {
        ["s-aaaaaaaaaaaaaaaa"] = { "x.mp3", WFJ.Hash.key("x"), 1, m = { "file" } } } })
      assert.are.equal(1, bad)
    end)

    it("knows each race's intro by its subtitles' ids", function()
      local human = WFJ.VoiceIntro.of(329309)
      assert.are.equal(53492, human.music)
      assert.is_true(#human.files > 0)
      assert.is_nil(WFJ.VoiceIntro.of(1))
    end)
  end)

  describe("a line in chat", function()
    it("plays once on Master, without the panel's queue, however many chat tabs show it", function()
      assert.is_true(say(E.GOSSIP, "MONSTER_SAY", 7))
      assert.is_false(say(E.GOSSIP, "MONSTER_SAY", 7))
      assert.are.equal(1, #v.sounds)
      assert.are.same({ path = E.chatPath("s-" .. E.GOSSIP), channel = "Master" }, v.sounds[1])
      assert.are.equal(0, WFJ.VoiceQueue.size())
    end)

    it("leaves the dialog channel alone and silences only the line's own English file while it plays", function()
      say(E.SHOUT, "MONSTER_YELL")
      assert.are.equal("1", v.cvars.Sound_EnableDialog)
      assert.is_true(v.muted[E.ENGLISH_SHOUT])
      assert.is_true(db.voiceMutedFiles[E.ENGLISH_SHOUT])
      Stub.fireTimers(2.5)
      assert.is_nil(v.muted[E.ENGLISH_SHOUT])
      assert.is_nil(db.voiceMutedFiles) -- nothing left silenced: the saved list goes
    end)

    it("drops a new said line while one plays; a yell or a whisper takes over", function()
      say(E.GOSSIP, "MONSTER_SAY", 1)
      assert.is_false(say(E.SHOUT, "MONSTER_SAY", 2))
      assert.are.equal(1, #v.sounds)
      assert.is_true(say(E.SHOUT, "MONSTER_YELL", 3))
      assert.are.same({ 1 }, v.stopped)
      assert.is_true(say(E.GOSSIP, "RAID_BOSS_WHISPER", 4))
      assert.are.equal(3, #v.sounds)
    end)

    it("never plays over a window's line, and a window's line stops it", function()
      Stub.showDetail()
      assert.is_false(say(E.SHOUT, "MONSTER_YELL", 1))
      P.stop()
      v.sounds, v.stopped = {}, {}
      assert.is_true(say(E.SHOUT, "MONSTER_YELL", 2))
      Stub.showDetail()
      assert.are.equal(1, #v.stopped)
      assert.are.equal(E.path("2-description"), v.sounds[#v.sounds].path)
      assert.is_nil(v.muted[E.ENGLISH_SHOUT]) -- the stopped line's English file is back
    end)

    it("plays nothing with voice or chat lines switched off", function()
      WFJ.Settings.set("voice.speech", false)
      assert.is_false(say(E.GOSSIP))
      WFJ.Settings.set("voice.speech", true)
      WFJ.Settings.set("voice.enabled", false)
      assert.is_false(say(E.GOSSIP, "MONSTER_SAY", 99))
      assert.are.equal(0, #v.sounds)
    end)
  end)

  describe("an intro", function()
    it("silences the race's English narration and plays the zone's music under the Italian", function()
      Stub.fireAll("CINEMATIC_START")
      assert.is_true(subtitle(E.INTRO1))
      local human = WFJ.VoiceIntro.of(329309)
      for _, id in ipairs(human.files) do assert.is_true(v.muted[id]) end
      assert.are.equal(53492, v.playing)
      Stub.fireAll("CINEMATIC_STOP")
      for _, id in ipairs(human.files) do assert.is_nil(v.muted[id]) end
      assert.is_nil(v.playing)
      assert.is_nil(next(db.voiceMutedFiles or {}))
    end)

    it("plays each subtitle once per cinematic, though the scroll shows it again", function()
      Stub.fireAll("CINEMATIC_START")
      assert.is_true(subtitle(E.INTRO1))
      Stub.fireTimers(2.5)
      assert.is_false(subtitle(E.INTRO1))
      assert.is_true(subtitle(E.INTRO2))
      Stub.fireAll("CINEMATIC_STOP")
      Stub.fireAll("CINEMATIC_START")
      assert.is_true(subtitle(E.INTRO1)) -- a new showing of the intro
    end)

    it("stops our narrator too when the cinematic ends early (Esc)", function()
      Stub.fireAll("CINEMATIC_START")
      subtitle(E.INTRO1)
      subtitle(E.INTRO2) -- waits its turn
      Stub.fireAll("CINEMATIC_STOP")
      assert.are.same({ 1 }, v.stopped)
      assert.are.equal(0, WFJ.VoiceQueue.size())
    end)

    it("keeps the narration silenced between its lines, until the cinematic ends", function()
      Stub.fireAll("CINEMATIC_START")
      subtitle(E.INTRO1)
      Stub.fireTimers(2.5) -- the first line ended, the next subtitle has not come yet
      local human = WFJ.VoiceIntro.of(329309)
      assert.is_true(v.muted[human.files[1]])
      assert.are.equal(53492, v.playing)
    end)

    it("gives the English back on stop, on logout and after a crash", function()
      Stub.fireAll("CINEMATIC_START")
      subtitle(E.INTRO1)
      P.stop()
      assert.is_nil(next(v.muted))
      assert.is_nil(v.playing)
      subtitle(E.INTRO2)
      Stub.fireAll("PLAYER_LOGOUT")
      assert.is_nil(next(v.muted))
      -- a crash left a file silenced in the saved variables: the next load lifts it
      db.voiceMutedFiles = { [222761] = true }
      v.muted[222761] = true
      P.listening = nil
      P.init(db)
      assert.is_nil(v.muted[222761])
      assert.is_nil(db.voiceMutedFiles)
    end)

    -- a file already playing is not stopped by MuteSoundFile: the narration must be silenced before it starts
    it("silences the player's race narration as the cinematic starts, before its first subtitle", function()
      _G.UnitRace = function() return "Human", "Human", 1 end
      Stub.fireAll("CINEMATIC_START")
      local human = WFJ.VoiceIntro.of(329309)
      for _, id in ipairs(human.files) do assert.is_true(v.muted[id]) end
      assert.are.equal(53492, v.playing)
      assert.is_false(subtitle(E.INTRO1)) -- the cinematic's first instant: the line waits (next tests)
      Stub.fireAll("CINEMATIC_STOP")
      assert.is_nil(v.playing) -- the narration stays silenced, for a replay (next tests)
    end)

    -- the game cuts the sounds started in the cinematic's first instant, and the first subtitle can come before
    -- the addon hears the cinematic start, or not reach it at all: the player's race intro starts its first line
    -- once the cinematic has settled
    it("starts the first line of the player's race intro once the cinematic has settled, its subtitle or not",
      function()
        _G.UnitRace = function() return "Human", "Human", 1 end
        Stub.fireAll("CINEMATIC_START")
        assert.is_false(subtitle(E.INTRO1))
        assert.are.equal(0, #v.sounds)
        Stub.fireTimers(1)
        assert.are.equal(E.chatPath("i-329309"), v.sounds[#v.sounds].path)
        assert.is_false(subtitle(E.INTRO1))
        subtitle(E.INTRO2)
        Stub.fireTimers(2.5)
        assert.are.equal(E.chatPath("i-329310"), v.sounds[#v.sounds].path)
      end)

    it("starts the first line again once the cinematic has settled, when its subtitle came first", function()
      _G.UnitRace = function() return "Human", "Human", 1 end
      Stub.fireAll("PLAYER_LOGIN")
      assert.is_true(subtitle(E.INTRO1))
      Stub.fireAll("CINEMATIC_START")
      assert.are.same({ 1 }, v.stopped) -- cut: the cinematic would have cut it anyway
      Stub.fireTimers(1)
      assert.are.equal(E.chatPath("i-329309"), v.sounds[#v.sounds].path)
      assert.are.equal(2, #v.sounds)
      assert.are.equal(53492, v.playing)
    end)

    -- the cinematic of a new character starts before any event the addon could answer in time: the narration
    -- (a file only an intro plays) stays silenced from the login on, through a loading screen and a replay
    it("keeps the player's race narration silenced from the login on, the music only during the cinematic",
      function()
        _G.UnitRace = function() return "Human", "Human", 1 end
        local human = WFJ.VoiceIntro.of(329309)
        Stub.fireAll("PLAYER_LOGIN")
        for _, id in ipairs(human.files) do assert.is_true(v.muted[id]) end
        assert.is_nil(v.playing) -- the music waits for the cinematic
        Stub.fireAll("LOADING_SCREEN_ENABLED")
        assert.is_true(v.muted[human.files[1]])
        Stub.fireAll("CINEMATIC_START")
        assert.are.equal(53492, v.playing)
        Stub.fireAll("CINEMATIC_STOP")
        assert.is_nil(v.playing)
        assert.is_true(v.muted[human.files[1]]) -- ready for a replay
        Stub.fireAll("PLAYER_LOGOUT")
        assert.is_nil(next(v.muted))
        assert.is_nil(db.voiceMutedFiles)
      end)

    it("leaves an unvoiced race and a switched-off intro alone", function()
      _G.UnitRace = function() return "Orc", "Orc", 2 end -- the pack voices no orc subtitle
      Stub.fireAll("PLAYER_LOGIN")
      Stub.fireAll("CINEMATIC_START")
      assert.are.equal(0, v.mutes)
      Stub.fireAll("CINEMATIC_STOP")
      _G.UnitRace = function() return "Human", "Human", 1 end
      WFJ.Settings.set("voice.intro", false)
      Stub.fireAll("PLAYER_LOGIN")
      Stub.fireAll("CINEMATIC_START")
      assert.are.equal(0, v.mutes)
      assert.is_nil(v.playing)
    end)

    it("gives the narration back when intros are switched off", function()
      _G.UnitRace = function() return "Human", "Human", 1 end
      Stub.fireAll("PLAYER_LOGIN")
      assert.is_true(v.muted[222761])
      WFJ.Settings.set("voice.intro", false)
      WFJ.State.fire("voice")
      assert.is_nil(next(v.muted))
    end)

    it("stays English for a race whose narration file is unknown, or with intros switched off", function()
      WFJ.Settings.set("voice.intro", false)
      assert.is_false(subtitle(E.INTRO1))
      assert.are.equal(0, v.mutes)
      assert.is_nil(v.playing)
    end)
  end)
end)

describe("an intro the pack voices only in part", function()
  after_each(E.teardown)

  it("stays English when a subtitle of the race has Italian but no take that matches it", function()
    local WFJ = E.setup(true)
    local add = function(ja) return { "x.mp3", WFJ.Hash.key(ja), 2.0 } end
    WFJ.Voice.register({ format = 3, folder = E.CHAT_FOLDER, lines = {
      ["i-329309"] = add(E.DATA.ui[E.INTRO1].ja),
      ["i-329310"] = add("an older wording of the second subtitle"), -- stale: the Italian changed since
    } })
    local v = Stub.voice
    assert.is_false(WFJ.VoicePlayer.onShown("cinematic.subtitles", "line.1", "ui", E.INTRO1))
    assert.are.equal(0, v.mutes)
    assert.is_nil(v.playing)
    assert.are.equal(0, #v.sounds)
  end)
end)
