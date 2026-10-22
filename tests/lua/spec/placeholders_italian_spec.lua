-- Italian class / race words by the player's sex (UnitSex: 2 male, 3 female; Main's player() reads it) and
-- gender pairs <a/b> whose words carry accents. The m/f table is Data/Placeholders.lua (WFJ.PlaceholderNames).
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

describe("Core/Placeholders in Italian", function()
  local P
  local function priest(sex)
    return { name = "Reyn", className = "Priest", classFile = "PRIEST", raceName = "Night Elf",
      raceFile = "NightElf", sex = sex }
  end

  before_each(function()
    local ns = {}
    H.loadPure("Data/Placeholders.lua", "OldpZ_ForeverITA", ns)
    H.loadPure("Core/Placeholders.lua", "OldpZ_ForeverITA", ns)
    P = ns.Placeholders
  end)

  it("a female player reads the female class and race words", function()
    assert.are.equal("Salve, Sacerdotessa.", (P.expand("Salve, {class}.", priest(3))))
    assert.are.equal("Sei una Elfa della Notte coraggiosa.",
      (P.expand("Sei un<o/a> {race} coraggios<o/a>.", priest(3))))
  end)

  it("a gender pair with Italian words takes one branch", function()
    assert.are.equal("la più cara", (P.expand("<il/la> più <caro/cara>", priest(3))))
    assert.are.equal("il più caro", (P.expand("<il/la> più <caro/cara>", priest(2))))
    assert.are.equal("è", (P.expand("<è/é>", { sex = 2 })))
    assert.are.equal("é", (P.expand("<è/é>", { sex = 3 })))
  end)

  it("a male player reads the male words", function()
    assert.are.equal("Salve, Sacerdote.", (P.expand("Salve, {class}.", priest(2))))
    assert.are.equal("Sei un Elfo della Notte coraggioso.",
      (P.expand("Sei <un/una> {race} coraggios<o/a>.", priest(2))))
  end)

  it("every playable class and race has both forms", function()
    for _, t in ipairs({ "WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "SHAMAN", "MAGE", "WARLOCK", "DRUID" }) do
      assert.is_string(P.CLASS[t].m, t); assert.is_string(P.CLASS[t].f, t)
    end
    for _, t in ipairs({ "Human", "Orc", "Dwarf", "NightElf", "Scourge", "Tauren", "Gnome", "Troll" }) do
      assert.is_string(P.RACE[t].m, t); assert.is_string(P.RACE[t].f, t)
    end
  end)
end)

describe("Data/Placeholders.lua in the addon's load order", function()
  it("is loaded before Core/Placeholders, which reads its table", function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI(); Stub.installItemTextAPI()
    local WFJ = Loader.load("OldpZ_ForeverITA")
    assert.are.same({ m = "Sacerdote", f = "Sacerdotessa" }, WFJ.Placeholders.CLASS.PRIEST)
    assert.are.same({ m = "Elfo della Notte", f = "Elfa della Notte" }, WFJ.Placeholders.RACE.NightElf)
  end)
end)
