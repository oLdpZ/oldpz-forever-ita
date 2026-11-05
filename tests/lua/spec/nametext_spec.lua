-- UI/NameText.lua: a name the client shows, against a table of hashes. Render and SurfaceState are recorded fakes.
describe("NameText.show", function()
  local NameText, WFJ, shown, dropped, records, hidden

  local function fs(text)
    return { text = text, GetText = function(self) return self.text end }
  end

  before_each(function()
    shown, dropped, records, hidden = {}, {}, {}, nil
    WFJ = {
      Hash = { key = function(norm) return "k:" .. norm end },
      Normalize = { v1 = function(en) return en end },
      Compat = { resolve = function(name)
        if name == "issecretvalue" then return function(v) return v == hidden end end
      end },
      SurfaceState = {
        get = function(_, key) return records[key] end,
        drop = function(_, key) dropped[#dropped + 1] = key end,
      },
      Lookup = { keyed = function(kind, key)
        if kind == "namezone" and key == "k:Elwynn Forest" then return { ja = "Foresta di Elwynn" } end
        if kind == "nameitem" and key == "k:Linen Cloth" then return { ja = "Tela di Lino" } end
        if kind == "namespell" and key == "k:Linen Bandage" then return { ja = "Benda di Lino" } end
      end },
      Render = { show = function(surface, key, widget, en, area, kind, id, ctx)
        shown[#shown + 1] = { surface = surface, key = key, fs = widget, en = en, area = area, kind = kind, id = id,
          ctx = ctx }
      end },
    }
    assert(loadfile("addon/OldpZ_ForeverITA/UI/NameText.lua"))("OldpZ_ForeverITA", WFJ)
    NameText = WFJ.NameText
  end)

  it("shows a known name through Render, its kind being its area", function()
    assert.equals(1, NameText.show("s", "r", fs("Elwynn Forest"), "namezone"))
    local call = shown[1]
    assert.equals("namezone", call.area)
    assert.equals("namezone", call.kind)
    assert.equals("k:Elwynn Forest", call.id)
    assert.is_true(call.ctx.compact) -- never a "not translated" marker on a name
  end)

  it("leaves an unknown name alone and drops the old record", function()
    assert.equals(0, NameText.show("s", "r", fs("Nowhere"), "namezone"))
    assert.same({}, shown)
    assert.same({ "r" }, dropped)
  end)

  it("does not look a name up in another kind", function()
    assert.equals(0, NameText.show("s", "r", fs("Elwynn Forest"), "nameitem"))
  end)

  it("never reads a secret value", function()
    local secret = {}
    hidden = secret
    assert.equals(0, NameText.show("s", "r", fs(secret), "namezone"))
    assert.same({}, shown)
  end)

  it("keeps its own Italian without showing it again", function()
    local widget = fs("Foresta di Elwynn")
    records.r = { fs = widget, applied = "Foresta di Elwynn" }
    assert.equals(1, NameText.show("s", "r", widget, "namezone"))
    assert.same({}, shown)
  end)

  it("ignores what is no text", function()
    assert.equals(0, NameText.show("s", "r", nil, "namezone"))
    assert.equals(0, NameText.show("s", "r", fs(""), "namezone"))
    assert.equals(0, NameText.show("s", "r", fs(nil), "namezone"))
  end)
  it("keeps a colour code and a reagent count around the name", function()
    local text = "|cffffffff3/5 Linen Cloth|r"
    assert.equals(1, NameText.show("s", "r", fs(text), "nameitem"))
    local call = shown[1]
    assert.equals(text, call.en)
    assert.equals("k:Linen Cloth", call.id)
    assert.same({ "|cffffffff3/5 ", "|r" }, call.ctx.wrap)
  end)

  it("keeps a bare count before the name", function()
    assert.equals(1, NameText.show("s", "r", fs("5 Linen Cloth"), "nameitem"))
    assert.same({ "5 ", "" }, shown[1].ctx.wrap)
  end)

  it("shows a plain name without a wrap", function()
    NameText.show("s", "r", fs("Linen Cloth"), "nameitem")
    assert.is_nil(shown[1].ctx.wrap)
  end)

  it("tries several kinds in order, the one that knows the name being the area", function()
    assert.equals(1, NameText.show("s", "r", fs("Linen Bandage"), { "nameitem", "namespell" }))
    assert.equals("namespell", shown[1].area)
    assert.equals(1, NameText.show("s", "r2", fs("Linen Cloth"), { "nameitem", "namespell" }))
    assert.equals("nameitem", shown[2].area)
  end)

  it("keeps a rank count after the name (a profession's rank bar)", function()
    assert.equals(1, NameText.show("s", "r", fs("Linen Bandage 1/75"), "namespell"))
    assert.same({ "", " 1/75" }, shown[1].ctx.wrap)
    assert.equals(0, NameText.show("s", "r2", fs(" 1/75"), "namespell"))
  end)
end)

describe("NameText.inList", function()
  local NameText, WFJ

  before_each(function()
    WFJ = {
      Hash = { key = function(norm) return "k:" .. norm end },
      Normalize = { v1 = function(en) return en end },
      Compat = { resolve = function() return nil end },
      Lookup = { keyed = function(kind, key)
        if kind == "nameitem" and key == "k:Flint and Tinder" then return { ja = "Pietra Focaia ed Esca" } end
        if kind == "namezone" and key == "k:Elwynn Forest" then return { ja = "Foresta di Elwynn" } end
      end },
    }
    assert(loadfile("addon/OldpZ_ForeverITA/UI/NameText.lua"))("OldpZ_ForeverITA", WFJ)
    NameText = WFJ.NameText
  end)

  local KINDS = { "nameitem", "namespell", "namezone" }

  it("names each link's label, keeping the link and the colour around it", function()
    local text = "|cffff2020|HTotemRequirement|hFlint and Tinder|h|r, |HAreaRequirement|hElwynn Forest|h"
    assert.equals("|cffff2020|HTotemRequirement|hPietra Focaia ed Esca|h|r, |HAreaRequirement|hForesta di Elwynn|h",
      NameText.inList(text, KINDS))
  end)

  it("names the pieces of a plain list, colour codes kept", function()
    assert.equals("|cffff2020Pietra Focaia ed Esca|r, Anvil",
      NameText.inList("|cffff2020Flint and Tinder|r, Anvil", KINDS))
  end)

  it("is nil when no piece is a known name, or there is no text", function()
    assert.is_nil(NameText.inList("|HSpellFocusRequirement|hAnvil|h", KINDS))
    assert.is_nil(NameText.inList("Anvil, Forge", KINDS))
    assert.is_nil(NameText.inList("", KINDS))
    assert.is_nil(NameText.inList(nil, KINDS))
  end)

  it("is the `nameList` argument kind of Core/UIStrings", function()
    assert.equals("Pietra Focaia ed Esca", WFJ.UIStrings.nameList("Flint and Tinder"))
  end)
end)
