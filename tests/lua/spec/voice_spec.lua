-- Core/Voice and Core/VoiceQueue: the voice pack's registry, the decision which file a shown line plays, the order
-- lines wait in. Pure: the player (UI) plays what `decide` returns.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

local FOLDER = "OldpZ_ForeverITA_Voce"
local PATH = "Interface\\AddOns\\%s\\Sound\\%s"

-- the shipped Italian, raw: markers and tokens as generated
local DATA = {
  ["quest.title"] = { [2] = { ja = "Gli artigli di Sharptalon", status = "." } },
  ["quest.description"] = {
    [2] = { ja = "Salve, viandante. Va' al ⟦Silverwind Refuge=Rifugio di Ventargento⟧.", status = "." },
    [4] = { ja = "Ben fatto, {name}. Sei stat<o/a> coraggios<o/a>.", status = "." },
    [5] = { ja = "Grazie, sei stat<o/a> di grande aiuto.", status = "." },
  },
  ["quest.objectives"] = { [2] = { ja = "Uccidi Sharptalon", status = "." } },
  ["quest.completion"] = { [2] = { ja = "Ottimo lavoro.", status = "." } },
  ["quest.progress"] = { [2] = { ja = "Allora?", status = "." } },
}

describe("Core/Voice: the pack registry and the decision", function()
  local WFJ, V
  local settings, revealed, enabled, db

  before_each(function()
    WFJ = {}
    H.loadPure("Core/Hash.lua", nil, WFJ)
    H.loadPure("Core/Voice.lua", nil, WFJ) -- pure: no frame, no sound API, no global
    V = WFJ.Voice
    settings = { ["voice.enabled"] = true, ["voice.offer"] = true, ["voice.progress"] = true,
      ["voice.turnin"] = true, ["voice.greeting"] = "always", ["voice.books"] = true }
    revealed, enabled, db = false, true, {}
    V.init({
      lookup = function(kind, id) return DATA[kind] and DATA[kind][id] end,
      hash = WFJ.Hash.key,
      setting = function(id) return settings[id] end,
      revealed = function() return revealed end,
      enabled = function() return enabled end,
      db = db,
    })
  end)

  local function pack(lines, creatures)
    return { format = 3, folder = FOLDER, lines = lines, creatures = creatures }
  end
  local function entry(file, it, seconds) return { file, WFJ.Hash.key(it), seconds } end
  local desc = DATA["quest.description"][2].ja
  local function offer(id, who, sex)
    return { V.decide("questframe.detail", "description", "quest.description", id or 2, who, sex) }
  end

  it("registers a valid table and drops malformed entries, counting them", function()
    local n, bad = V.register(pack({
      ["2-description"] = entry("2-description.mp3", desc, 4.2),
      ["2-progress"] = { "../../Other/evil.mp3", WFJ.Hash.key("x"), 1 }, -- outside the Sound folder
      ["2-completion"] = { "2-completion.mp3", "nothex", 1 },
      ["3-description"] = { "3-description.mp3", WFJ.Hash.key("x"), 1, f = { "..\\x.mp3", 1 } },
      ["4-description"] = { "4-description.mp3", WFJ.Hash.key("x"), 1, v = { deep = { "a/../b.mp3", 1 } } },
      ["g-0123456789abcdef"] = { "g-0123456789abcdef.mp3", "0123456789ABCDEF" }, -- no length is fine
    }, { [10] = "deep", [11] = { m = "deep", f = "soft" }, [12] = { "deep", "soft" }, ["x"] = "deep" }))
    assert.are.equal(2, n)
    assert.are.equal(6, bad)
    assert.is_true(V.hasPack())
    assert.are.same({ registered = 2, invalid = 6, matched = 0, missing = 0, stale = 0 }, V.counts)
  end)

  it("refuses a table of another format or folder as a whole", function()
    assert.are.same({ 0, 1 }, { V.register({ format = 1, folder = FOLDER, lines = {} }) })
    assert.are.same({ 0, 1 }, { V.register({ format = 2, folder = FOLDER, lines = {} }) })
    assert.are.same({ 0, 1 }, { V.register({ format = 3, folder = FOLDER .. "/../X", lines = {} }) })
    assert.are.same({ 0, 1 }, { V.register({ format = 3, folder = "..", lines = {} }) })
    assert.are.same({ 0, 1 }, { V.register({ format = 3, folder = "WoWForeverJapanese_Voice", lines = {} }) })
    assert.are.same({ 0, 1 }, { V.register({ format = 3, folder = "SomeOtherAddon", lines = {} }) })
    assert.are.same({ 0, 1 }, { V.register(pack(nil)) })
    assert.are.same({ 0, 1 }, { V.register("x") })
    assert.is_false(V.hasPack())
  end)

  it("a pack whose every line is malformed is no pack: nothing to voice, no settings to show", function()
    assert.are.same({ 0, 0 }, { V.register(pack({})) })
    assert.is_false(V.hasPack())
    assert.are.same({ 0, 1 }, { V.register(pack({ ["2-description"] = { "../x.mp3", WFJ.Hash.key(desc) } })) })
    assert.is_false(V.hasPack())
    assert.are.same({ nil, "nopack" }, offer())
    V.register({ format = 3, folder = FOLDER .. "_2", lines = { ["2-description"] = entry("a.mp3", desc) } })
    assert.is_true(V.hasPack())
    V.register({ format = 3, folder = FOLDER .. "_2", lines = {} }) -- that pack again, now empty
    assert.is_false(V.hasPack())
  end)

  it("keys a quest field by quest id, gossip and book pages by their key, nothing else", function()
    assert.are.equal("456-description", V.packKey("quest.description", 456))
    assert.are.equal("g-0a044ece3562b58d", V.packKey("gossip", "0a044ece3562b58d"))
    assert.are.equal("b-0a044ece3562b58d", V.packKey("book", "0a044ece3562b58d"))
    assert.is_nil(V.packKey("quest.description", "456"))
    assert.is_nil(V.packKey("item.description", 4))
    assert.is_nil(V.packKey("ui", "QUEST_LOG"))
  end)

  it("voices only the offer, progress, turn-in, greeting and book lines", function()
    V.register(pack({ ["2-description"] = entry("2-description.mp3", desc, 4.2) }))
    assert.are.same({ PATH:format(FOLDER, "2-description.mp3"), 4.2 }, offer())
    assert.are.same({ nil, "kind" }, { V.decide("questframe.detail", "objectives", "quest.objectives", 2) })
    assert.are.same({ nil, "kind" }, { V.decide("questframe.detail", "title", "quest.title", 2) })
    assert.are.same({ nil, "kind" }, { V.decide("gossip", "option1", "gossip", "0123456789abcdef") })
    assert.are.same({ nil, "kind" }, { V.decide("tooltip", "description", "quest.description", 2) })
  end)

  it("stays silent when switched off, when English is showing, and without a pack", function()
    assert.are.same({ nil, "nopack" }, offer())
    V.register(pack({ ["2-description"] = entry("2-description.mp3", desc, 4.2) }))
    settings["voice.offer"] = false
    assert.are.same({ nil, "off" }, offer())
    settings["voice.offer"], settings["voice.enabled"] = true, false
    assert.are.same({ nil, "off" }, offer())
    settings["voice.enabled"] = true
    revealed = true
    assert.are.same({ nil, "english" }, offer())
    revealed, enabled = false, false
    assert.are.same({ nil, "english" }, offer())
  end)

  it("a line with no file, or whose Italian changed since the file was made, plays nothing", function()
    V.register(pack({ ["2-description"] = entry("2-description.mp3", "un italiano più vecchio", 4.2) }))
    assert.are.same({ nil, "stale" }, offer())
    assert.are.same({ nil, "missing" }, { V.decide("questframe.progress", "progress", "quest.progress", 2) })
    assert.are.equal(1, V.counts.stale)
    assert.are.equal(1, V.counts.missing)
    assert.are.equal(0, V.counts.matched)
  end)

  it("hashes the shipped Italian raw: markers and tokens intact", function()
    V.register(pack({ ["2-description"] = entry("2-description.mp3", desc) }))
    assert.is_string(offer()[1])
    V.register(pack({ ["2-description"] = entry("2-description.mp3",
      "Salve, viandante. Va' al Rifugio di Ventargento.") })) -- the resolved form is not what shipped
    assert.are.same({ nil, "stale" }, offer())
  end)

  it("a sectioned, variant or missing Italian plays nothing", function()
    DATA["quest.description"][9] = { sections = { head = "x" }, status = "." }
    DATA["quest.description"][8] = { variants = { "a", "b" }, status = "." }
    V.register(pack({ ["9-description"] = { "9-description.mp3", WFJ.Hash.key("x") },
      ["8-description"] = { "8-description.mp3", WFJ.Hash.key("a") },
      ["7-description"] = { "7-description.mp3", WFJ.Hash.key("a") } }))
    assert.are.same({ nil, "notext" }, offer(9))
    assert.are.same({ nil, "notext" }, offer(8))
    assert.are.same({ nil, "notext" }, offer(7))
    DATA["quest.description"][9], DATA["quest.description"][8] = nil, nil
  end)

  describe("the character's sex", function()
    local named = DATA["quest.description"][4].ja -- {name} and <o/a>
    local paired = DATA["quest.description"][5].ja -- <o/a> only

    it("a female character hears the line's female take", function()
      V.register(pack({ ["4-description"] = { "4-description.mp3", WFJ.Hash.key(named), 3,
        f = { "4-description_f.mp3", 3.5 } } }))
      assert.are.same({ PATH:format(FOLDER, "4-description_f.mp3"), 3.5 }, offer(4, nil, 3))
      assert.are.same({ PATH:format(FOLDER, "4-description.mp3"), 3 }, offer(4, nil, 2))
      assert.are.same({ PATH:format(FOLDER, "4-description.mp3"), 3 }, offer(4))
    end)

    it("a line that needs a female take and has none is silent for a female character, never the male take", function()
      V.register(pack({ ["4-description"] = entry("4-description.mp3", named, 3),
        ["5-description"] = entry("5-description.mp3", paired, 3) }))
      assert.are.same({ nil, "nofemale" }, offer(4, nil, 3))
      assert.are.same({ nil, "nofemale" }, offer(5, nil, 3))
      assert.are.same({ PATH:format(FOLDER, "5-description.mp3"), 3 }, offer(5, nil, 2))
    end)

    it("a line the sex does not change plays its main take for a female character", function()
      V.register(pack({ ["2-description"] = entry("2-description.mp3", desc, 4) }))
      assert.are.same({ PATH:format(FOLDER, "2-description.mp3"), 4 }, offer(2, nil, 3))
    end)

    it("mirrors the pipeline's rule: {name} or an <a/b> pair, not a stage direction", function()
      assert.is_true(V.needsVariants("Ciao {name}."))
      assert.is_true(V.needsVariants("Sei <un/una> eroe."))
      assert.is_true(V.needsVariants("Sei stat<o/a>."))
      assert.is_false(V.needsVariants("<sbuffa> Vattene."))
      assert.is_false(V.needsVariants("Ciao {class}."))
      assert.is_false(V.needsVariants("<a / b>"))
      assert.is_false(V.needsVariants(nil))
    end)

    it("the speaker's own voice has its female take too; without it the female character hears nothing", function()
      V.register(pack({ ["4-description"] = { "4-description.mp3", WFJ.Hash.key(named), 3,
        f = { "4-description_f.mp3", 3 },
        v = { deep = { "4-description_deep.mp3", 2, f = { "4-description_deep_f.mp3", 2.5 } },
          soft = { "4-description_soft.mp3", 2 } } } }, { [10] = "deep", [11] = "soft" }))
      assert.are.same({ PATH:format(FOLDER, "4-description_deep_f.mp3"), 2.5 }, offer(4, { creature = 10 }, 3))
      assert.are.same({ PATH:format(FOLDER, "4-description_deep.mp3"), 2 }, offer(4, { creature = 10 }, 2))
      assert.are.same({ nil, "nofemale" }, offer(4, { creature = 11 }, 3))
    end)
  end)

  it("packs merge, and a pack registering again replaces only its own lines", function()
    V.register({ format = 3, folder = FOLDER .. "_1", lines = { ["2-description"] = entry("a.mp3", desc, 1) } })
    V.register({ format = 3, folder = FOLDER .. "_2",
      lines = { ["3-description"] = entry("b.mp3", "x", 1), ["2-progress"] = entry("c.mp3", "y", 1) } })
    assert.are.same({ [FOLDER .. "_1"] = 1, [FOLDER .. "_2"] = 2 }, V.packs())
    assert.are.equal(3, V.counts.registered)
    V.register({ format = 3, folder = FOLDER .. "_2", lines = { ["3-description"] = entry("b.mp3", "x", 1) } })
    assert.are.equal(2, V.counts.registered)
    assert.are.equal(PATH:format(FOLDER .. "_1", "a.mp3"), offer()[1])
  end)

  it("a line several creatures say plays the voice of the one on screen, else its main voice", function()
    V.register(pack({ ["2-description"] = { "2-description.mp3", WFJ.Hash.key(desc), 3,
        v = { deep = { "2-description_deep.mp3", 2.5 }, soft = { "2-description_soft.mp3", 2 } } } },
      { [10] = "deep", [11] = { m = "deep", f = "soft" } }))
    assert.are.same({ PATH:format(FOLDER, "2-description_deep.mp3"), 2.5 }, offer(2, { creature = 10 }))
    assert.are.same({ PATH:format(FOLDER, "2-description_soft.mp3"), 2 }, offer(2, { creature = 11, sex = 3 }))
    assert.are.same({ PATH:format(FOLDER, "2-description_deep.mp3"), 2.5 }, offer(2, { creature = 11, sex = 2 }))
    assert.are.same({ PATH:format(FOLDER, "2-description.mp3"), 3 }, offer(2, { creature = 99 }))
    assert.are.same({ PATH:format(FOLDER, "2-description.mp3"), 3 }, offer(2, nil))
  end)

  it("a pack registering again also drops the creatures it brought before", function()
    local line = { "2-description.mp3", WFJ.Hash.key(desc), 3, v = { deep = { "2-description_deep.mp3", 2 } } }
    V.register(pack({ ["2-description"] = line }, { [10] = "deep" }))
    assert.are.same({ PATH:format(FOLDER, "2-description_deep.mp3"), 2 }, offer(2, { creature = 10 }))
    V.register(pack({ ["2-description"] = line }))
    assert.are.same({ PATH:format(FOLDER, "2-description.mp3"), 3 }, offer(2, { creature = 10 }))
  end)

  it("a book page is voiced on the book window and switched off by its own setting", function()
    DATA.book = { ["0a044ece3562b58d"] = { ja = "Pagina", status = "." } }
    V.register(pack({ ["b-0a044ece3562b58d"] = entry("b-0a044ece3562b58d.mp3", "Pagina", 2) }))
    assert.is_string((V.decide("itemtext", "page", "book", "0a044ece3562b58d")))
    settings["voice.books"] = false
    assert.are.same({ nil, "off" }, { V.decide("itemtext", "page", "book", "0a044ece3562b58d") })
    DATA.book = nil
  end)

  describe("greetings", function()
    local KEY = "0a044ece3562b58d"
    before_each(function()
      DATA.gossip = { [KEY] = { ja = "Salve.", status = "." } }
      V.register(pack({ ["g-" .. KEY] = entry("g-" .. KEY .. ".mp3", "Salve.", 1) }))
    end)
    after_each(function() DATA.gossip = nil end)
    local function greet(who, peek)
      return { V.decide("gossip", "greeting", "gossip", KEY, who, nil, peek) }
    end
    local GREETING = PATH:format(FOLDER, "g-" .. KEY .. ".mp3")

    it("once: decide only reads; a creature is heard once the player marks it (saved table)", function()
      settings["voice.greeting"] = "once"
      assert.are.same({ GREETING, 1 }, greet({ creature = 10 }))
      assert.are.same({ GREETING, 1 }, greet({ creature = 10 })) -- never played yet: asked again, it plays
      assert.is_nil(db.voiceHeard)
      V.markHeard(10) -- the player, when the line starts playing
      assert.are.same({ [10] = true }, db.voiceHeard)
      assert.are.same({ nil, "off" }, greet({ creature = 10 }))
      assert.are.same({ GREETING, 1 }, greet({ creature = 11 })) -- another creature
      assert.are.same({ GREETING, 1 }, greet({ creature = 10 }, true)) -- the replay button asks anyway
      assert.are.same({ GREETING, 1 }, greet(nil)) -- no creature to remember: it plays
      assert.are.same({ GREETING, 1 }, greet(nil))
    end)

    it("markHeard ignores a missing creature id and a missing saved table", function()
      V.markHeard(nil)
      assert.is_nil(db.voiceHeard)
      V.init({}) -- no db
      V.markHeard(10)
    end)

    it("the quest window's greeting panel is a greeting too", function()
      settings["voice.greeting"] = "once"
      assert.are.same({ GREETING, 1 },
        { V.decide("questframe.greeting", "greeting", "gossip", KEY, { creature = 10 }) })
      V.markHeard(10)
      assert.are.same({ nil, "off" }, greet({ creature = 10 }))
    end)

    it("always plays every time; never plays nothing", function()
      settings["voice.greeting"] = "always"
      V.markHeard(10)
      assert.are.same({ GREETING, 1 }, greet({ creature = 10 }))
      assert.are.same({ GREETING, 1 }, greet({ creature = 10 }))
      settings["voice.greeting"] = "never"
      assert.are.same({ nil, "off" }, greet({ creature = 12 }))
    end)
  end)
end)

describe("Core/VoiceQueue: the order lines play in", function()
  local Q
  before_each(function()
    local ns = {}
    H.loadPure("Core/VoiceQueue.lua", nil, ns)
    Q = ns.VoiceQueue
  end)

  it("adds a line once, plays the head first, puts a replay at the head", function()
    assert.are.equal(0, Q.size())
    assert.is_true(Q.push({ key = "a" }))
    assert.is_true(Q.push({ key = "b" }))
    assert.is_false(Q.push({ key = "a" }))
    assert.are.equal(2, Q.size())
    assert.is_true(Q.has("b"))
    assert.are.equal("a", Q.current().key)
    assert.are.equal(1, Q.waiting())
    Q.front({ key = "b" })
    assert.are.same({ "b", "a" }, { Q.items[1].key, Q.items[2].key })
    assert.are.equal("b", Q.pop().key)
    assert.are.equal(1, Q.size())
    Q.clear()
    assert.are.equal(0, Q.size())
    assert.is_false(Q.has("a"))
    assert.is_nil(Q.pop())
  end)

  it("drops the lines of a closed window and says whether the head was one", function()
    Q.push({ key = "a", window = "QuestFrame" })
    Q.push({ key = "b", window = "GossipFrame" })
    Q.push({ key = "c", window = "QuestFrame" })
    assert.is_true(Q.dropWindow("QuestFrame"))
    assert.are.same({ "b" }, { Q.items[1].key })
    assert.is_false(Q.dropWindow("ItemTextFrame"))
  end)
end)

describe("voice in the loaded addon", function()
  local WFJ, S
  local KEY = "0123456789abcdee"
  local MARKED = "Benvenuto a ⟦Goldshire=Borgodoro⟧, {name}."

  before_each(function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI()
    _G.OFI_DB = nil
    WFJ = Loader.load("OldpZ_ForeverITA", { data = H.FIXTURE_DATA })
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    S = WFJ.Settings
    WFJ.Data.add("gossip", { [KEY] = { MARKED, "." } })
  end)

  local function voiceSettings()
    local all, hidden = {}, 0
    for _, d in ipairs(S.list()) do
      if d.id:find("^voice%.") then
        all[#all + 1] = d.id
        if S.isHidden(d) then hidden = hidden + 1 end
      end
    end
    return all, hidden
  end

  it("without a pack: the global exists, every voice setting is hidden, nothing is voiced or saved", function()
    assert.is_function(_G.OldpZ_ForeverITA_RegisterVoice)
    assert.is_false(WFJ.Voice.hasPack())
    local all, hidden = voiceSettings()
    assert.are.same({ "voice.enabled", "voice.offer", "voice.progress", "voice.turnin", "voice.greeting",
      "voice.books", "voice.muteDialog", "voice.panel" }, all)
    assert.are.equal(#all, hidden)
    assert.are.same({ nil, "nopack" }, { WFJ.Voice.decide("gossip", "greeting", "gossip", KEY, { creature = 1 }) })
    assert.is_nil(OFI_DB.voiceHeard)
    -- the defaults, and every label in Italian
    for _, id in ipairs(all) do
      local d
      for _, x in ipairs(S.list()) do if x.id == id then d = x end end
      assert.is_true(type(d.it) == "string" and #d.it > 0, id)
      if id ~= "voice.greeting" and id ~= "voice.panel" then assert.is_true(S.get(id), id) end
    end
    assert.are.equal("once", S.get("voice.greeting"))
    assert.are.same({ "once", "always", "never" }, (function()
      for _, x in ipairs(S.list()) do if x.id == "voice.greeting" then return x.choices end end
    end)())
  end)

  it("a pack registers through the global and shows the settings", function()
    local n, bad = OldpZ_ForeverITA_RegisterVoice({ format = 3, folder = FOLDER,
      lines = { ["g-" .. KEY] = { "g-" .. KEY .. ".mp3", WFJ.Hash.key(MARKED), 2 } } })
    assert.are.same({ 1, 0 }, { n, bad })
    local _, hidden = voiceSettings()
    assert.are.equal(0, hidden)
  end)

  it("Lookup.raw is the shipped text, names unresolved", function()
    assert.are.equal("Benvenuto a Borgodoro, {name}.", WFJ.Lookup.get("gossip", KEY).ja)
    assert.are.equal(MARKED, WFJ.Lookup.raw("gossip", KEY).ja)
    local q = WFJ.Lookup.get("quest.title", 7)
    assert.are.same(q, WFJ.Lookup.raw("quest.title", 7))
    assert.is_nil(WFJ.Lookup.raw("quest.title", 999999))
    assert.is_nil(WFJ.Lookup.raw("gossip", nil))
  end)

  it("the same decision with names.style it and en", function()
    OldpZ_ForeverITA_RegisterVoice({ format = 3, folder = FOLDER,
      lines = { ["g-" .. KEY] = { "g-" .. KEY .. ".mp3", WFJ.Hash.key(MARKED), 2,
        f = { "g-" .. KEY .. "_f.mp3", 2 } } } })
    S.set("voice.greeting", "always")
    local want = { PATH:format(FOLDER, "g-" .. KEY .. ".mp3"), 2 }
    assert.are.same(want, { WFJ.Voice.decide("gossip", "greeting", "gossip", KEY, nil, 2) })
    S.set("names.style", "en")
    assert.are.same(want, { WFJ.Voice.decide("gossip", "greeting", "gossip", KEY, nil, 2) })
    assert.are.same({ PATH:format(FOLDER, "g-" .. KEY .. "_f.mp3"), 2 },
      { WFJ.Voice.decide("gossip", "greeting", "gossip", KEY, nil, 3) })
  end)

  it("greeting once is remembered per creature in OFI_DB.voiceHeard", function()
    OldpZ_ForeverITA_RegisterVoice({ format = 3, folder = FOLDER,
      lines = { ["g-" .. KEY] = { "g-" .. KEY .. ".mp3", WFJ.Hash.key(MARKED), 2 } } })
    assert.is_string((WFJ.Voice.decide("gossip", "greeting", "gossip", KEY, { creature = 42 }, 2)))
    assert.is_nil(OFI_DB.voiceHeard)
    WFJ.Voice.markHeard(42)
    assert.are.same({ [42] = true }, OFI_DB.voiceHeard)
    assert.are.same({ nil, "off" }, { WFJ.Voice.decide("gossip", "greeting", "gossip", KEY, { creature = 42 }, 2) })
  end)
end)
