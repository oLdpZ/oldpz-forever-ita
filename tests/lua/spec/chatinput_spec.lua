-- The chat input box is the client's own: the addon ships no chat-input font module (the Japanese predecessor's
-- UI/ChatInput existed only because the client's chat font had no kana), so a shown edit box keeps its font.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

local function widget(name)
  local w = { font = { "Fonts/ARIALN.TTF", 14, "" }, scripts = {} }
  function w:GetFont() return self.font[1], self.font[2], self.font[3] end
  function w:SetFont(p, s, f) self.font = { p, s, f }; return true end
  function w.GetName() return name end
  function w:HookScript(n, fn) self.scripts[n] = fn end
  return w
end

describe("chat input font", function()
  local WFJ, box, header, suffix
  setup(function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI(); Stub.installItemTextAPI()
    box, header, suffix = widget("ChatFrame1EditBox"), widget(), widget()
    _G.CHAT_FRAMES = { "ChatFrame1" }
    _G.ChatFrame1 = { editBox = box }
    _G.ChatFrame1EditBoxHeader, _G.ChatFrame1EditBoxHeaderSuffix = header, suffix
    WFJ = Loader.load("OldpZ_ForeverITA", { data = H.FIXTURE_DATA })
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
  end)
  teardown(function()
    _G.CHAT_FRAMES, _G.ChatFrame1, _G.ChatFrame1EditBoxHeader, _G.ChatFrame1EditBoxHeaderSuffix = nil, nil, nil, nil
  end)

  it("registers no ChatInput module", function()
    assert.is_nil(WFJ.ChatInput)
  end)

  it("leaves a shown chat edit box, its header and suffix in the client's font", function()
    if box.scripts.OnShow then box.scripts.OnShow(box) end
    for _, w in ipairs({ box, header, suffix }) do
      assert.are.same({ "Fonts/ARIALN.TTF", 14, "" }, w.font)
    end
  end)
end)
