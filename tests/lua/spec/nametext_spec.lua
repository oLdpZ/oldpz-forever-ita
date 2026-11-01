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
end)
