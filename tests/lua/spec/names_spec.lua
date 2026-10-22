-- Core/Names is the Lua twin of core/names.py (vectors/names_vectors.lua): a marked name `⟦english=italian⟧`
-- (spec §8) shows as the form `names.style` picks, wherever shipped text is read (Core/Lookup).
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

describe("Core/Names: shared vectors", function()
  local N
  setup(function()
    local ns = {}
    H.loadPure("Core/Names.lua", "OldpZ_ForeverITA", ns)
    N = ns.Names
  end)

  it("loads under a std-lib-only environment and resolves every vector in both styles", function()
    local V = dofile(H.ROOT .. "/vectors/names_vectors.lua")
    assert.is_true(#V.cases >= 6)
    for _, c in ipairs(V.cases) do
      assert.are.equal(c.it, N.resolve(c.text, "it"), c.id)
      assert.are.equal(c.en, N.resolve(c.text, "en"), c.id)
    end
  end)

  it("style en drops an English name's leading The after an Italian article or articulated preposition", function()
    assert.are.equal("la Bulwark", N.resolve("la ⟦The Bulwark=Il Baluardo⟧", "en"))
    assert.are.equal("Il Great Sea", N.resolve("Il ⟦The Great Sea=Mare Infinito⟧", "en"))
    assert.are.equal("verso The Barrens", N.resolve("verso ⟦The Barrens=Savane⟧", "en"))
    assert.are.equal("Nelle Barrens e dall'Den.",
      N.resolve("Nelle ⟦The Barrens=Savane⟧ e dall'⟦The Den=Antro del Tirocinio⟧.", "en"))
    assert.are.equal("dall’Den", N.resolve("dall’⟦The Den=Antro del Tirocinio⟧", "en"))
    assert.are.equal("Isola The Barrens", N.resolve("Isola ⟦The Barrens=Savane⟧", "en"))
    assert.are.equal("la Il Baluardo", N.resolve("la ⟦The Bulwark=Il Baluardo⟧", "it"))
  end)

  it("without a style or settings it is the official Italian; non-strings pass through", function()
    assert.are.equal("a Roccavento.", N.resolve("a ⟦Stormwind City=Roccavento⟧."))
    assert.is_nil(N.resolve(nil))
    assert.are.equal(5, N.resolve(5))
  end)
end)

describe("Core/Align counts a marked name once", function()
  it("matches the numbers vector of a marked name", function()
    local ns = {}
    H.loadPure("Core/Align.lua", "OldpZ_ForeverITA", ns)
    assert.are.same({ ["7"] = 1, ["3"] = 1 }, ns.Align.numbers("Al ⟦Sector 7=Settore 7⟧ con 3 casse"))
    assert.are.same({}, ns.Align.checkNumbers("Vai al ⟦Sector 7=Settore 7⟧.", "Go to Sector 7."))
  end)
end)

describe("names.style on the shipped data", function()
  local WFJ, S
  local MARKED = "Porta queste pelli a ⟦Stormwind City=Roccavento⟧."

  before_each(function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI()
    WFJ = Loader.load("OldpZ_ForeverITA", { data = H.FIXTURE_DATA })
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    S = WFJ.Settings
    Stub.prints = {}
  end)

  local function wfj(line) SlashCmdList.OFI(line) end

  it("defaults to the official Italian names; Lookup resolves every slot kind, data untouched", function()
    assert.are.equal("it", S.get("names.style"))
    WFJ.Data.quest[7][1] = MARKED
    assert.are.equal("Porta queste pelli a Roccavento.", WFJ.Lookup.get("quest.title", 7).ja)
    S.set("names.style", "en")
    assert.are.equal("Porta queste pelli a Stormwind City.", WFJ.Lookup.get("quest.title", 7).ja)
    assert.are.equal(MARKED, WFJ.Data.quest[7][1])
    -- a branch line's variants and a keyed (gossip) row
    local variants = { "$N1 a ⟦Goldshire=Borgodoro⟧.", "$N1.", shape = { "1/0", "1/0" } }
    WFJ.Data.add("spell", { [99999902] = { variants, nil, 0x12345678, nil, "um" } })
    local e = WFJ.Lookup.get("spell.description", 99999902)
    assert.are.same({ "$N1 a Goldshire.", "$N1." }, { e.variants[1], e.variants[2] })
    assert.are.same({ "1/0", "1/0" }, e.shapes)
    assert.are.equal("$N1 a ⟦Goldshire=Borgodoro⟧.", variants[1])
    WFJ.Data.add("gossip", { ["0123456789abcdee"] = { "Benvenuto a ⟦Goldshire=Borgodoro⟧.", "." } })
    assert.are.equal("Benvenuto a Goldshire.", WFJ.Lookup.gossip("0123456789abcdee").ja)
    S.set("names.style", "it")
    assert.are.equal("Benvenuto a Borgodoro.", WFJ.Lookup.gossip("0123456789abcdee").ja)
  end)

  it("/fita nomi switches the style, says so in Italian, and the open quest window shows the other form", function()
    WFJ.Data.quest[7][1] = MARKED
    Stub.quest = { id = 7, title = "Clearing the Kobold Field", description = "", objectives = "",
      progress = "", completion = "" }
    Stub.showDetail()
    assert.are.equal("Porta queste pelli a Roccavento.", QuestInfoTitleHeader:GetText())
    wfj("nomi")
    assert.are.equal("en", S.get("names.style"))
    assert.are.equal("OFI: Nomi: originali inglesi", Stub.prints[#Stub.prints])
    assert.are.equal("Porta queste pelli a Stormwind City.", QuestInfoTitleHeader:GetText())
    wfj("nomi")
    assert.are.equal("OFI: Nomi: italiani ufficiali", Stub.prints[#Stub.prints])
    assert.are.equal("Porta queste pelli a Roccavento.", QuestInfoTitleHeader:GetText())
    wfj("nomi en")
    assert.are.equal("en", S.get("names.style"))
    wfj("nomi xx")
    assert.are.equal("en", S.get("names.style"))
  end)

  it("holding the reveal key still shows the client's English, whatever the style", function()
    WFJ.Data.quest[7][1] = MARKED
    S.set("names.style", "en")
    Stub.quest = { id = 7, title = "Clearing the Kobold Field", description = "", objectives = "",
      progress = "", completion = "" }
    Stub.showDetail()
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    assert.are.equal("Clearing the Kobold Field", QuestInfoTitleHeader:GetText())
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    assert.are.equal("Porta queste pelli a Stormwind City.", QuestInfoTitleHeader:GetText())
  end)
end)
