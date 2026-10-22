-- The addon's public identity: oLd_pZ Forever - Traduzione Italiana, /fita, globals prefixed OFI_ only.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

describe("identity", function()
  local toc

  setup(function()
    toc = Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI(); Stub.installItemTextAPI()
    Loader.load("OldpZ_ForeverITA")
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
  end)

  it("names the addon in its TOC", function()
    assert.equal("oLd_pZ Forever - Traduzione Italiana", toc.Title)
    assert.equal("oLd_pZ", toc.Author)
    assert.is_nil(toc["X-Curse-Project-ID"])
    assert.is_nil(toc["X-Website"])
  end)

  it("registers /fita", function()
    assert.equal("/fita", _G.SLASH_OFI1)
    assert.is_function(SlashCmdList["OFI"])
    assert.is_nil(SlashCmdList["WFJ"])
  end)

  it("leaves no upstream global behind", function()
    for k in pairs(_G) do
      if type(k) == "string" then
        assert.is_falsy(k:find("^WFJ_"), k)
        assert.is_falsy(k:find("WoWForeverJapanese", 1, true), k)
      end
    end
  end)
end)
