-- The addon as it ships: Blizzard's official Italian (UI strings, item flavour text, spell tooltips) plus the quest
-- text translated so far, which grows with every imported batch, so no type's count is fixed here. It loads, Meta
-- counts what each Data shard holds, and the Translator finds no entry for a quest id with no Italian, so that
-- quest's text stays the game's English.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

describe("the addon with the generated data", function()
  local WFJ

  setup(function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI(); Stub.installItemTextAPI()
    WFJ = Loader.load("OldpZ_ForeverITA")
  end)

  it("loads with Meta counting each type's rows, the official import's types never empty", function()
    for _, t in ipairs({ "quest", "objective", "area" }) do
      assert.are.equal(WFJ.Data.meta.counts[t], WFJ.Data.count(t), t)
    end
    -- keyed types: Meta counts translated lines; a repeated quest's text and gender aliases are extra keys
    for _, t in ipairs({ "gossip", "book" }) do
      assert.is_true(WFJ.Data.count(t) >= WFJ.Data.meta.counts[t], t)
    end
    for _, t in ipairs({ "item", "spell", "ui" }) do
      assert.is_true(WFJ.Data.count(t) > 0, t)
      assert.are.equal(WFJ.Data.meta.counts[t], WFJ.Data.count(t), t)
    end
  end)

  it("Translator returns no entry for a quest id with no Italian, without an error", function()
    local T = WFJ.Translator.new({
      enabled = function() return true end,
      areaEnabled = function() return true end,
      modifierHeld = function() return false end,
      lookup = function(kind, id) return WFJ.Lookup.get(kind, id) end,
      marker = function() return false end,
    })
    for _, id in ipairs({ 0, 99999, 999999 }) do  -- ids no quest has
      for _, field in ipairs({ "title", "objectives", "description", "progress", "completion" }) do
        assert.is_nil(WFJ.Lookup.get("quest." .. field, id))
        local action, payload = T.resolve("quests", "quest." .. field, id)
        assert.are.equal("none", action)
        assert.is_nil(payload.it); assert.is_nil(payload.ja)
      end
    end
    -- the client's own Italian for a UI key (GlobalStrings itIT)
    assert.are.equal("Accetta", WFJ.Lookup.get("ui", "ACCEPT").ja)
  end)
end)
