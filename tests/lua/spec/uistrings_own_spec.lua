-- Core/UIStrings OWN: one English with its own Japanese on one screen, asked for by key.
local H = require("tests.lua.spec.helpers")

local function ns()
  H.coreStub()
  local t = {}
  H.loadChunk("Core/Const.lua", "OldpZ_ForeverITA", t)
  H.loadPure("Core/Normalize.lua", "OldpZ_ForeverITA", t)
  H.loadPure("Core/Hash.lua", "OldpZ_ForeverITA", t)
  H.loadPure("Core/UIStringKeys.lua", "OldpZ_ForeverITA", t)
  H.loadPure("Core/UIStrings.lua", "OldpZ_ForeverITA", t)
  return t
end

local function build(t, own)
  local function h1(text) return (t.Hash.h32x2(t.Normalize.v1(text))) end
  local EN = { INVTYPE_CLOAK = "Back", AUCTION_HOUSE_BACK_BUTTON = "Back", SCORE_X = "Damage %d" }
  local rows = {
    INVTYPE_CLOAK = { "背中", h1("Back"), "." },
    AUCTION_HOUSE_BACK_BUTTON = { "Indietro", h1("Back"), "." },
  }
  local saved = t.UIStrings.OWN
  t.UIStrings.OWN = own or {}
  local index = t.UIStrings.build({ rows = rows, english = function(k) return EN[k] end, hash = h1 })
  t.UIStrings.OWN = saved
  return index
end

describe("Core/UIStrings OWN", function()
  it("an owned key answers only where a widget names it; the other key keeps the English", function()
    local t = ns()
    local index = build(t, { AUCTION_HOUSE_BACK_BUTTON = true })
    assert.are.equal("INVTYPE_CLOAK", (index:match("Back")))
    assert.are.equal("AUCTION_HOUSE_BACK_BUTTON", (index:matchOnly("Back", { "AUCTION_HOUSE_BACK_BUTTON" })))
    assert.are.equal("INVTYPE_CLOAK", (index:matchOnly("Back", { "INVTYPE_CLOAK" })))
    assert.are.equal(0, index.counts.ambiguous)
    assert.are.equal(1, index.counts.owned)
    assert.are.equal(1, index.counts.indexed)
  end)

  it("without OWN the two keys are still ambiguous (the default behaviour)", function()
    local t = ns()
    local index = build(t, {})
    assert.are.equal(2, index.counts.ambiguous)
    assert.is_nil(index:match("Back"))
    assert.is_nil(index:matchOnly("Back", { "AUCTION_HOUSE_BACK_BUTTON" }))
  end)

  it("an owned key is never matched by an unrestricted match, even with no other key", function()
    local t = ns()
    local index = build(t, { AUCTION_HOUSE_BACK_BUTTON = true, INVTYPE_CLOAK = true })
    assert.is_nil(index:match("Back"))
    assert.are.equal("INVTYPE_CLOAK", (index:matchOnly("Back", { INVTYPE_CLOAK = true })))
    assert.are.equal(2, index.counts.owned)
  end)

  describe("a female character's standing", function()
    local function standings(t, female)
      local function h1(text) return (t.Hash.h32x2(t.Normalize.v1(text))) end
      local EN = { FACTION_STANDING_LABEL6 = "Honored", FACTION_STANDING_LABEL6_FEMALE = "Honored",
        QUEST_FACTION_NEEDED_NOPROGRESS = "%s: %s" }
      local rows = {
        FACTION_STANDING_LABEL6 = { "Onorato", h1("Honored"), "." },
        FACTION_STANDING_LABEL6_FEMALE = { "Onorata", h1("Honored"), "." },
        QUEST_FACTION_NEEDED_NOPROGRESS = { "%s: %s", h1("%s: %s"), "." },
      }
      return t.UIStrings.build({ rows = rows, english = function(k) return EN[k] end, hash = h1,
        female = female })
    end
    local BOTH = { "FACTION_STANDING_LABEL6", "FACTION_STANDING_LABEL6_FEMALE" }

    it("a female player's panel shows the female form, a male player's the male one", function()
      local t = ns()
      local her = standings(t, function() return true end)
      local him = standings(t, function() return false end)
      assert.are.equal("FACTION_STANDING_LABEL6_FEMALE", (her:matchOnly("Honored", BOTH)))
      assert.are.equal("FACTION_STANDING_LABEL6", (him:matchOnly("Honored", BOTH)))
      assert.are.equal(0, her.counts.ambiguous)
    end)

    it("without a sex the male form answers, and the open match never gives the female form", function()
      local t = ns()
      local index = standings(t, nil)
      assert.are.equal("FACTION_STANDING_LABEL6", (index:matchOnly("Honored", BOTH)))
      assert.are.equal("FACTION_STANDING_LABEL6", (standings(t, function() return true end):match("Honored")))
    end)

    it("a standing argument takes the female form for a female player", function()
      local t = ns()
      local her = standings(t, function() return true end)
      local him = standings(t, function() return false end)
      local key = "QUEST_FACTION_NEEDED_NOPROGRESS"
      assert.are.equal("Darnassus: Onorata", her:fill("%s: %s", { key = key, "Darnassus", "Honored" }))
      assert.are.equal("Darnassus: Onorato", him:fill("%s: %s", { key = key, "Darnassus", "Honored" }))
    end)
  end)

  it("the shipped OWN table holds plain keys only", function()
    local t = ns()
    for key in pairs(t.UIStrings.OWN) do
      assert.is_truthy(key:find("^[A-Z][A-Z0-9_]+$"), key)
    end
  end)
end)
