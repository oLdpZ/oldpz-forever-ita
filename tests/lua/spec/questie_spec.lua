-- UI/Questie: Questie's translation global (QUESTIE_LOCALES_OVERRIDE) filled from the shipped rows, and its gossip
-- title match retried in Italian. Questie side replayed from Questie Localization/l10n.lua
-- (PublishLocaleOverrideEntityNames) and Database/QuestieDB.lua (GetQuestIDFromName).
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

describe("UI/Questie", function()
  local WFJ, Q

  local function h1(en) return (WFJ.Hash.h32x2(WFJ.Normalize.v1(en))) end

  local function quest(id, title, en, objectives, status)
    WFJ.Data.add("quest", { [id] = { title, objectives, nil, nil, nil, h1(en), objectives and 1 or nil,
      nil, nil, nil, status or "..mmm" } })
  end

  before_each(function()
    _G.QUESTIE_LOCALES_OVERRIDE, _G.QuestieLoader = nil, nil
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    WFJ = Loader.load("OldpZ_ForeverITA", { data = H.FIXTURE_DATA })
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    Q = WFJ.Questie
    Q.reset()
  end)

  after_each(function()
    _G.QUESTIE_LOCALES_OVERRIDE, _G.QuestieLoader = nil, nil
  end)

  it("sets the global at load, in Questie's shape, with an Italian locale and no UI strings", function()
    local o = _G.QUESTIE_LOCALES_OVERRIDE
    assert.are.equal("itIT", o.locale)
    assert.are.equal("Italiano", o.localeName)
    assert.are.same({}, o.translations)
    assert.are.equal(Q.quests, o.questLookup)
    assert.are.equal(Q.npcs, o.npcNameLookup)
  end)

  it("never replaces another addon's global", function()
    local other = { locale = "ukUA", translations = {} }
    local env = { QUESTIE_LOCALES_OVERRIDE = other }
    assert.is_false(Q.install(env))
    assert.are.equal(other, env.QUESTIE_LOCALES_OVERRIDE)
    assert.is_true(Q.install({}))
  end)

  it("publishes a quest's title and its objectives one line each, marked names resolved", function()
    quest(99999901, "⟦Tomb Weed=Erba Tombale⟧", "Tomb Weed",
      "Porta 8 ⟦Tomb Weed=Erba Tombale⟧ a Sorella Gigi.\n\nPoi torna da lei.")
    local row = Q.quests()[99999901]
    assert.are.same({ "Erba Tombale", { "Porta 8 Erba Tombale a Sorella Gigi.", "Poi torna da lei." } }, row)
    WFJ.Settings.set("names.style", "en")
    assert.are.equal("Tomb Weed", Q.quests()[99999901][1])
  end)

  it("leaves out a text with a token and a kept-English slot: Questie falls back to its English", function()
    quest(99999902, "Il Ritorno", "The Return", "Uccidi $N1 lupi.")
    assert.are.same({ "Il Ritorno", {} }, Q.quests()[99999902])
    WFJ.Data.add("quest", { [99999903] = { nil, nil, nil, nil, nil, h1("Kept"), nil, nil, nil, nil, "emmmm" } })
    assert.is_nil(Q.quests()[99999903])
    quest(99999904, "Ciao {name}", "Hello")
    assert.is_nil(Q.quests()[99999904])
  end)

  it("publishes NPC names and subnames, none with names.style = en", function()
    WFJ.Data.add("unit", { [99999905] = { "Sorella Gigi", "Erborista", h1("Sister Gigi"), h1("Herbalist"), ".." } })
    assert.are.same({ "Sorella Gigi", "Erborista" }, Q.npcs()[99999905])
    WFJ.Settings.set("names.style", "en")
    assert.are.same({}, Q.npcs())
  end)

  it("finds the Italian titles of an English one by its fingerprint", function()
    quest(99999906, "⟦Tomb Weed=Erba Tombale⟧", "Tomb Weed")
    assert.are.same({ "Erba Tombale" }, Q.titlesFor("Tomb Weed"))
    assert.are.same({}, Q.titlesFor("Nothing Like It"))
    assert.are.same({}, Q.titlesFor(nil))
  end)

  describe("GetQuestIDFromName", function()
    -- Questie's match: the giver's quests whose database title (now Italian) equals the client's title
    local function questieDB(titles)
      return { GetQuestIDFromName = function(name)
        for id, t in pairs(titles) do if t == name then return id end end
        return 0
      end }
    end

    it("retries a failed match with the Italian title", function()
      quest(99999907, "⟦Tomb Weed=Erba Tombale⟧", "Tomb Weed")
      local db = questieDB({ [367] = "Erba Tombale" })
      assert.is_true(Q.wrap(db))
      assert.are.equal(367, db.GetQuestIDFromName("Tomb Weed", "Creature-0-1-2-3-1-0", true))
      assert.are.equal(0, db.GetQuestIDFromName("Unknown Quest", "Creature-0-1-2-3-1-0", true))
    end)

    it("keeps a direct match and wraps once", function()
      local db = questieDB({ [5] = "Tomb Weed" })
      assert.is_true(Q.wrap(db))
      assert.is_false(Q.wrap(db))
      assert.are.equal(5, db.GetQuestIDFromName("Tomb Weed"))
      assert.is_false(Q.wrap({}))
    end)

    it("is installed when Questie loads, with the tracker", function()
      local db = questieDB({})
      local fn = db.GetQuestIDFromName
      local tracker = { GetColoredQuestName = function(q) return q.name end, GetObjectiveText = function(o)
        return o.Description end }
      local name = tracker.GetColoredQuestName
      _G.QuestieLoader = { ImportModule = function(_, n)
        return (n == "QuestieDB" and db) or (n == "TrackerData" and tracker) or nil
      end }
      Stub.fireAll("ADDON_LOADED", "Questie")
      assert.are_not.equal(fn, db.GetQuestIDFromName)
      assert.are_not.equal(name, tracker.GetColoredQuestName)
    end)
  end)

  describe("the tracker", function()
    -- Questie's TrackerData: the title and the objective line come from the client's quest log (English); the two
    -- writers colour, level and tag what they are given
    local function trackerData()
      local seen = {}
      local data = {
        GetColoredQuestName = function(q, showLevel)
          seen.complete = q:IsComplete()
          return (showLevel and ("[" .. q.level .. "] ") or "") .. q.name
        end,
        GetObjectiveText = function(objective) return "|cffff0000" .. objective.Description end,
      }
      return data, seen
    end
    local function displayQuest(id, name)
      return { Id = id, name = name, level = 7, IsComplete = function(self) return self.Id == 99999910 and 1 or 0 end }
    end

    it("shows the Italian title of a quest whose English it translates, Questie's level and state kept", function()
      quest(99999910, "Il ⟦Cult of the Damned=Culto dei Dannati⟧", "The Cult of the Damned")
      local data, seen = trackerData()
      assert.is_true(Q.wrapTracker(data))
      assert.is_false(Q.wrapTracker(data))
      local q = displayQuest(99999910, "The Cult of the Damned")
      assert.are.equal("[7] Il Culto dei Dannati", data.GetColoredQuestName(q, true))
      assert.are.equal(1, seen.complete) -- Questie's own methods still read the record
      assert.are.equal("The Cult of the Damned", q.name) -- never written
      WFJ.Settings.set("names.style", "en")
      assert.are.equal("Il Cult of the Damned", data.GetColoredQuestName(q, false))
    end)

    it("leaves the English: another English on the id, no row, the translation off, the reveal key", function()
      quest(99999911, "Il Ritorno", "The Return")
      local data = trackerData()
      Q.wrapTracker(data)
      assert.are.equal("Forever Renamed", data.GetColoredQuestName(displayQuest(99999911, "Forever Renamed")))
      assert.are.equal("Unknown", data.GetColoredQuestName(displayQuest(99999912, "Unknown")))
      assert.are.equal("Il Ritorno", data.GetColoredQuestName(displayQuest(99999911, "The Return")))
      WFJ.State.enabled = false
      assert.are.equal("The Return", data.GetColoredQuestName(displayQuest(99999911, "The Return")))
      WFJ.State.enabled = true
      local isDown = WFJ.Modifier.isDown
      WFJ.Modifier.isDown = function() return true end
      assert.are.equal("The Return", data.GetColoredQuestName(displayQuest(99999911, "The Return")))
      WFJ.Modifier.isDown = isDown
    end)

    it("shows an objective line in Italian through the quest map's lookups, else the English", function()
      local data = trackerData()
      Q.wrapTracker(data)
      local real = WFJ.QuestMap.objectiveJapanese
      WFJ.QuestMap.objectiveJapanese = function(en) return en == "2/5 Wolf slain" and "2/5 Lupo ucciso" or nil end
      local line = { Description = "2/5 Wolf slain", Collected = 2 }
      assert.are.equal("|cffff00002/5 Lupo ucciso", data.GetObjectiveText(line))
      assert.are.equal("2/5 Wolf slain", line.Description)
      assert.are.equal("|cffff0000Gather herbs", data.GetObjectiveText({ Description = "Gather herbs" }))
      WFJ.QuestMap.objectiveJapanese = function(en) return en .. " [Non tradotto]" end -- English with a marker
      assert.are.equal("|cffff00002/5 Wolf slain", data.GetObjectiveText(line))
      WFJ.QuestMap.objectiveJapanese = real
    end)
  end)
end)
