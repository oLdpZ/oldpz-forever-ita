-- Core/UnitNames: an NPC's Italian name from its GUID, only when the shown English is the one the row translates.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

describe("Core/UnitNames", function()
  local WFJ, U, S
  local SENANI = "Creature-0-1-2-3-12696-0000"

  before_each(function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    WFJ = Loader.load("OldpZ_ForeverITA", { data = H.FIXTURE_DATA })
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    WFJ.Compat.init(function(name) return _G[name] end)
    U, S = WFJ.UnitNames, WFJ.Settings
    _G.issecretvalue = nil
  end)

  after_each(function()
    _G.issecretvalue = nil
    _G.UnitGUID = nil
  end)

  it("gives the Italian name when the shown English hashes to the row's h1 (pipeline ↔ Lua contract)", function()
    assert.are.equal("Senani Cuore Tonante", U.name(SENANI, "Senani Thunderheart"))
    assert.are.equal(WFJ.Lookup.get("unit.name", 12696).h1,
      (WFJ.Hash.h32x2(WFJ.Normalize.v1("Senani Thunderheart"))))
  end)

  it("a Vehicle GUID is a creature too", function()
    assert.are.equal("Senani Cuore Tonante", U.name("Vehicle-0-1-2-3-12696-0000", "Senani Thunderheart"))
  end)

  it("another English for the same id leaves the name alone", function()
    assert.is_nil(U.name(SENANI, "Senani Stormheart"))
  end)

  it("never touches players or pets", function()
    assert.is_nil(U.name("Player-1-0ABCDEF0", "Senani Thunderheart"))
    assert.is_nil(U.name("Pet-0-1-2-3-12696-0000", "Senani Thunderheart"))
  end)

  it("names.style = en leaves the English, and a style change drops the cached answer", function()
    assert.are.equal("Senani Cuore Tonante", U.name(SENANI, "Senani Thunderheart"))
    S.set("names.style", "en")
    assert.is_nil(U.name(SENANI, "Senani Thunderheart"))
    S.set("names.style", "it")
    assert.are.equal("Senani Cuore Tonante", U.name(SENANI, "Senani Thunderheart"))
  end)

  it("a secret shown text or a secret guid is never compared", function()
    _G.issecretvalue = function() return true end
    assert.is_nil(U.name(SENANI, "Senani Thunderheart"))
    _G.issecretvalue = function(v) return v == SENANI end
    assert.is_nil(U.name(SENANI, "Senani Thunderheart"))
  end)

  it("an id without a row, a kept-English row, an empty subname slot and bad input give nil", function()
    assert.is_nil(U.name("Creature-0-1-2-3-999999-0000", "Nobody"))
    WFJ.Data.add("unit", { [99999903] = { nil, nil, 0x282b2a44, nil, "em" } })
    assert.is_nil(U.name("Creature-0-1-2-3-99999903-0000", "Senani Thunderheart"))
    assert.is_nil(U.subname(SENANI, "Senani Thunderheart"))
    assert.is_nil(U.name(nil, "Senani Thunderheart"))
    assert.is_nil(U.name(SENANI, nil))
    assert.is_nil(U.name(SENANI, ""))
  end)

  it("a creature with no row, or another English on its id, is recorded for translation; a kept row is not",
  function()
    local recorded = {}
    local record = WFJ.Collector.record
    WFJ.Collector.record = function(kind, id, field, en) recorded[#recorded + 1] = { kind, id, field, en } end
    assert.is_nil(U.name("Creature-0-1-2-3-999999-0000", "Rabid Forest Wolf")) -- a mob Forever added
    assert.is_nil(U.name(SENANI, "Senani Stormheart")) -- Forever renamed it
    WFJ.Data.add("unit", { [99999903] = { nil, nil, 0x282b2a44, nil, "em" } })
    assert.is_nil(U.name("Creature-0-1-2-3-99999903-0000", "Senani Thunderheart")) -- kept English on purpose
    assert.is_nil(U.subname("Creature-0-1-2-3-999998-0000", "Wolf Trainer")) -- subnames: not recorded
    assert.is_nil(U.name("Player-1-0ABCDEF0", "Someone")) -- never a player
    assert.are.same({ { "npc", 999999, "name", "Rabid Forest Wolf" }, { "npc", 12696, "name", "Senani Stormheart" } },
      recorded)
    WFJ.Collector.record = record
  end)

  it("subname reads the subname slot", function()
    WFJ.Data.add("unit", { [99999904] = { nil, "Maestro di prova", nil, 0x282b2a44, "m." } })
    assert.are.equal("Maestro di prova", U.subname("Creature-0-1-2-3-99999904-0000", "Senani Thunderheart"))
    assert.is_nil(U.name("Creature-0-1-2-3-99999904-0000", "Senani Thunderheart"))
  end)

  it("forUnit reads the unit's GUID", function()
    _G.UnitGUID = function(unit) return unit == "target" and SENANI or nil end
    assert.are.equal("Senani Cuore Tonante", U.forUnit("target", "Senani Thunderheart"))
    assert.is_nil(U.forUnit("focus", "Senani Thunderheart"))
  end)

  it("the cache stays bounded", function()
    for i = 1, U.CACHE_MAX + 5 do U.name("Creature-0-1-2-3-" .. (500000 + i) .. "-0000", "X") end
    assert.is_true(U.cacheSize() <= U.CACHE_MAX)
    assert.are.equal("Senani Cuore Tonante", U.name(SENANI, "Senani Thunderheart"))
  end)
  describe("byEnglish: the name an objective line or a system line carries (no GUID)", function()
    local function h1(text) return (WFJ.Hash.h32x2(WFJ.Normalize.v1(text))) end

    it("the shipped rows' Italian, found by the English's fingerprint (the index Main builds at load)", function()
      assert.are.equal("Senani Cuore Tonante", U.byEnglish("Senani Thunderheart"))
      U.buildIndex({})
      assert.is_nil(U.byEnglish("Senani Thunderheart"))
      U.buildIndex()
      assert.are.equal("Senani Cuore Tonante", U.byEnglish("Senani Thunderheart"))
      assert.is_nil(U.byEnglish("Senani Stormheart"))
      assert.is_nil(U.byEnglish(nil))
      assert.is_nil(U.byEnglish(""))
    end)

    it("names.style = en and a secret text leave the English", function()
      U.buildIndex()
      S.set("names.style", "en")
      assert.is_nil(U.byEnglish("Senani Thunderheart"))
      S.set("names.style", "it")
      _G.issecretvalue = function() return true end
      assert.is_nil(U.byEnglish("Senani Thunderheart"))
    end)

    it("a marked name is indexed in its Italian form, whatever the style when the index is built", function()
      local rows = { [213] = { "⟦Dire Wolf=Metalupo⟧ Affamato", nil, h1("Hungry Dire Wolf"), nil,
        ".m" } }
      S.set("names.style", "en")
      U.buildIndex(rows)
      S.set("names.style", "it")
      assert.are.equal("Metalupo Affamato", U.byEnglish("Hungry Dire Wolf"))
    end)

    it("two Italian names for one English: the most common; a tie leaves the English", function()
      U.buildIndex({
        [1] = { "Bruto Gnoll", nil, h1("Gnoll Brute"), nil, ".m" },
        [2] = { "Gnoll Bruto", nil, h1("Gnoll Brute"), nil, ".m" },
        [3] = { "Gnoll Bruto", nil, h1("Gnoll Brute"), nil, ".m" },
        [4] = { "Lupo A", nil, h1("Wolf"), nil, ".m" }, [5] = { "Lupo B", nil, h1("Wolf"), nil, ".m" },
        [6] = { nil, nil, h1("Kept"), nil, "em" }, -- kept English: no name
        [7] = { nil, "Solo sottotitolo", nil, h1("Sub"), "m." },
      })
      assert.are.equal("Gnoll Bruto", U.byEnglish("Gnoll Brute"))
      assert.is_nil(U.byEnglish("Wolf"))
      assert.is_nil(U.byEnglish("Kept"))
      assert.is_nil(U.byEnglish("Sub"))
      assert.are.same({ names = 1, ambiguous = 1 }, U.indexCounts())
    end)

    it("is the creatureName resolver of the UI strings", function()
      assert.are.equal(U.byEnglish, WFJ.UIStrings.creatureName)
    end)
  end)
end)
