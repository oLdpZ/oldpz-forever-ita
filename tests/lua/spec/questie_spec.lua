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

    it("is installed when Questie loads", function()
      local db = questieDB({})
      local fn = db.GetQuestIDFromName
      _G.QuestieLoader = { ImportModule = function(_, name) return name == "QuestieDB" and db or nil end }
      Stub.fireAll("ADDON_LOADED", "Questie")
      assert.are_not.equal(fn, db.GetQuestIDFromName)
    end)
  end)
end)
