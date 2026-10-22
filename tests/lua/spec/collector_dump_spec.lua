-- the scripted session's SavedVariables text is the committed round-trip fixture the pipeline imports
-- (tests/python/test_import_collector.py). Regenerate after a deliberate change: WFJ_WRITE_FIXTURES=1 make test-lua
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")
local Loader = require("tests.lua.spec.loader")

local FIXTURE = "tests/fixtures/collector/OldpZ_ForeverITA.lua"

describe("collector dump fixture", function()
  it("the stub session serializes byte-identically to the committed fixture", function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI()
    -- on the Italian fixture store: quest 2's title and objectives and two gossip lines ship, so they are known
    Loader.load("OldpZ_ForeverITA", { data = H.FIXTURE_DATA })
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    Stub.fireAll("PLAYER_ENTERING_WORLD")
    require("tests.lua.spec.collector_session").run()
    local text = Stub.serializeSavedVariables({ "OFI_DB", "OFI_Collector" })

    if os.getenv("WFJ_WRITE_FIXTURES") == "1" then
      local f = assert(io.open(H.ROOT .. "/" .. FIXTURE, "w"))
      f:write(text)
      f:close()
    end
    assert.are.equal(H.readFile(FIXTURE), text)
    assert.are.same({ "1.15.9.69722" }, OFI_Collector.builds)
    -- the file loads back as Lua and keeps its shape
    local chunk = assert(loadstring(text))
    local env = {}
    setfenv(chunk, env)
    chunk()
    assert.are.same(OFI_Collector, env.OFI_Collector)
  end)
end)
