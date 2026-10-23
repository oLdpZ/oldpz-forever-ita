-- UI/NamePlates.lua (ADR-103, Task 10): an NPC's name on its nameplate takes the Italian of its `unit` row
-- (Core/UnitNames), written after the client's CompactUnitFrame_UpdateName (shared/compactunitframe.lua:
-- frame.name:SetText(GetUnitName(frame.unit, true))). Only a nameplate's own unit frame is ever written: a compact
-- raid / party frame (the same global writer), a player's or a pet's plate, a secret name or GUID and a forbidden
-- plate stay as the client wrote them. In combat nothing is written at all: PLAYER_REGEN_DISABLED puts the English
-- back, PLAYER_REGEN_ENABLED writes the Italian again on every plate shown. A pooled unit frame never keeps the
-- previous unit's Italian.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")

local FILES = {}
for i, f in ipairs(H.UI_FILES) do FILES[i] = f end
FILES[#FILES + 1] = "Core/UnitNames.lua"
FILES[#FILES + 1] = "UI/NamePlates.lua"

describe("the NPC names on the nameplates", function()
  local WFJ
  local SENANI = "Creature-0-1-2-3-12696-0000"
  local HOGGER = "Creature-0-1-2-3-448-0000"
  local GLOBALS = { "CompactUnitFrame_UpdateName", "C_NamePlate", "issecretvalue" }

  -- the client's writer, as shared/compactunitframe.lua writes the name (nameplates and compact raid frames alike)
  local function updateName(uf) _G.CompactUnitFrame_UpdateName(uf) end
  local function nameOf(uf) return uf.name:GetText() end
  -- the addon's writes to one name widget (the stub counts SetText / SetFont made from addon code)
  local function addonWrites(fs) return fs.calls.addonSetText + fs.calls.addonSetFont end

  -- NAME_PLATE_UNIT_ADDED as the client runs it: the plate (a pooled unit frame when given) gets its token, the
  -- driver's SetUnit writes the name, then the event reaches the addons' frames (Main's, routed to the module).
  local function add(token, uf)
    local _, frame = Stub.namePlate(token, uf)
    updateName(frame)
    WFJ.NamePlates.onAdded(token) -- Main routes the event
    return frame
  end
  local function remove(token)
    WFJ.NamePlates.onRemoved(token)
    Stub.removeNamePlate(token)
  end

  before_each(function()
    H.uiTeardown()
    for _, n in ipairs(GLOBALS) do _G[n] = nil end
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installTooltipAPI()
    Stub.installKeyAPI()
    Stub.installNamePlateAPI()
    WFJ = H.loadChunks(FILES)
    local function h1(text) return (WFJ.Hash.h32x2(WFJ.Normalize.v1(text))) end
    local UNIT = { ["unit.name"] = {
      [12696] = { ja = "Senani Cuore Tonante", status = ".", h1 = h1("Senani Thunderheart") },
      [448] = { ja = "Hogger il Rosso", status = ".", h1 = h1("Hogger") },
    } }
    local function lookup(kind, id) return UNIT[kind] and UNIT[kind][id] or nil end
    WFJ.Lookup = { get = lookup }
    H.uiSetup(WFJ, { RAID = { "Raid", "Incursione" } }, { lookup = lookup })
    _G.CompactUnitFrame_UpdateName = function(frame) frame.name:SetText(_G.UnitName(frame.unit)) end
    Stub.units.nameplate1 = { name = "Senani Thunderheart", guid = SENANI }
    Stub.units.nameplate2 = { name = "Hogger", guid = HOGGER }
    assert.is_true(WFJ.NamePlates.init())
  end)

  after_each(function()
    H.uiTeardown()
    Stub.keys.alt = false
    Stub.combat = false
    Stub.units = {}
    for _, n in ipairs(GLOBALS) do _G[n] = nil end
  end)

  it("a creature's plate shows its Italian name out of combat", function()
    local a, b = add("nameplate1"), add("nameplate2")
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    assert.are.equal("Hogger il Rosso", nameOf(b))
    updateName(a) -- the same unit again: still Italian, nothing rewritten
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
  end)

  it("the name's colour code is kept around the Italian", function()
    Stub.units.nameplate2 = { name = "|cffff0000Hogger|r", guid = HOGGER }
    local b = add("nameplate2")
    assert.are.equal("|cffff0000Hogger il Rosso|r", nameOf(b))
  end)

  it("in combat a new plate stays English; PLAYER_REGEN_ENABLED writes the Italian", function()
    Stub.combat = true
    local a = add("nameplate1")
    assert.are.equal("Senani Thunderheart", nameOf(a))
    assert.are.equal(0, addonWrites(a.name))
    Stub.combat = false
    WFJ.NamePlates.onCombatEnd()
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
  end)

  it("combat start holds every write even when putting the English back raises", function()
    local a = add("nameplate1")
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    local dropAll = WFJ.SurfaceState.dropAll
    WFJ.SurfaceState.dropAll = function() error("boom") end
    local ok = pcall(WFJ.NamePlates.onCombatStart) -- the error still reaches Main's step guard
    WFJ.SurfaceState.dropAll = dropAll
    assert.is_false(ok)
    -- InCombatLockdown() not yet true (the event comes first): only the hold keeps this plate unwritten
    local c = add("nameplate2")
    assert.are.equal("Hogger", nameOf(c))
    assert.are.equal(0, addonWrites(c.name))
    WFJ.NamePlates.onCombatEnd()
    assert.are.equal("Hogger il Rosso", nameOf(c))
  end)

  it("combat start gives every Italian plate its English back; nothing is written until combat ends", function()
    local a, b = add("nameplate1"), add("nameplate2")
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    WFJ.NamePlates.onCombatStart() -- PLAYER_REGEN_DISABLED, before the lockdown
    Stub.combat = true
    assert.are.equal("Senani Thunderheart", nameOf(a))
    assert.are.equal("Hogger", nameOf(b))
    assert.are.equal(0, WFJ.SurfaceState.count(WFJ.NamePlates.SURFACE))
    local before = { addonWrites(a.name), addonWrites(b.name) }
    Stub.units.nameplate3 = { name = "Hogger", guid = HOGGER }
    local c = add("nameplate3") -- a plate that appears in combat
    updateName(a)
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    WFJ.State.fire("names")
    remove("nameplate2")
    assert.are.same(before, { addonWrites(a.name), addonWrites(b.name) })
    assert.are.equal(0, addonWrites(c.name))
    assert.are.equal("Hogger", nameOf(c))
    Stub.combat = false
    WFJ.NamePlates.onCombatEnd() -- PLAYER_REGEN_ENABLED: every plate shown now
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    assert.are.equal("Hogger il Rosso", nameOf(c))
    assert.are.equal("Hogger", nameOf(b)) -- removed in combat: not a plate any more
  end)

  it("a player's or a pet's plate and the personal plate stay as written", function()
    Stub.units.nameplate4 = { name = "Senani Thunderheart", guid = "Player-1-0ABCDEF0" }
    Stub.units.nameplate5 = { name = "Hogger", guid = "Pet-0-1-2-3-448-0000" }
    local p, pet = add("nameplate4"), add("nameplate5")
    assert.are.equal("Senani Thunderheart", nameOf(p))
    assert.are.equal("Hogger", nameOf(pet))
    local _, own = Stub.namePlate("player") -- not a nameplate token
    updateName(own)
    assert.are.equal("Reyn", nameOf(own))
    assert.are.equal(0, addonWrites(p.name) + addonWrites(pet.name) + addonWrites(own.name))
  end)

  it("a secret name or GUID is never read or written", function()
    local SECRET_NAME = {}
    _G.issecretvalue = function(v) return v == SECRET_NAME or v == "Creature-secret" end
    WFJ.Compat.init(function(name) return _G[name] end)
    Stub.units.nameplate1 = { name = SECRET_NAME, guid = SENANI }
    local a
    assert.has_no.errors(function() a = add("nameplate1") end)
    assert.are.equal(SECRET_NAME, nameOf(a))
    Stub.units.nameplate2 = { name = "Hogger", guid = "Creature-secret" }
    local b = add("nameplate2")
    assert.are.equal("Hogger", nameOf(b))
    assert.are.equal(0, addonWrites(a.name) + addonWrites(b.name))
  end)

  it("the Italian shown, then the client writes a secret name: no error, no write, the record dropped", function()
    local a = add("nameplate1")
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    local SECRET_NAME = {}
    _G.issecretvalue = function(v) return v == SECRET_NAME end
    WFJ.Compat.init(function(name) return _G[name] end)
    WFJ.SurfaceState.secret = _G.issecretvalue
    Stub.units.nameplate1 = { name = SECRET_NAME, guid = SENANI }
    local before = a.name.calls.addonSetText
    assert.has_no.errors(function() updateName(a) end)
    assert.are.equal(SECRET_NAME, nameOf(a))
    assert.are.equal(before, a.name.calls.addonSetText)
    assert.are.equal(0, WFJ.SurfaceState.count(WFJ.NamePlates.SURFACE))
  end)

  it("a compact raid or party frame is never written, even for a creature", function()
    Stub.units.raid1 = { name = "Senani Thunderheart", guid = SENANI }
    local raid = CreateFrame("Button")
    raid.unit, raid.name = "raid1", Stub.fontString("")
    raid.IsForbidden = function() return false end
    updateName(raid)
    assert.are.equal("Senani Thunderheart", nameOf(raid))
    -- a frame claiming a nameplate token that is not that plate's own unit frame
    add("nameplate1")
    local stray = CreateFrame("Button")
    stray.unit, stray.name = "nameplate1", Stub.fontString("")
    stray.IsForbidden = function() return false end
    updateName(stray)
    assert.are.equal("Senani Thunderheart", nameOf(stray))
    assert.are.equal(0, addonWrites(raid.name) + addonWrites(stray.name))
  end)

  it("a forbidden plate is not looked into past IsForbidden", function()
    local reads = {}
    local inner = { name = Stub.fontString("Senani Thunderheart"), unit = "nameplate1" }
    local forbidden = setmetatable({ IsForbidden = function() return true end }, { __index = function(_, k)
      reads[#reads + 1] = k
      return inner[k]
    end })
    assert.has_no.errors(function() WFJ.NamePlates.onName(forbidden) end)
    assert.are.same({}, reads)
    assert.are.equal("Senani Thunderheart", inner.name:GetText())
  end)

  it("a pooled unit frame reused for another unit keeps no stale Italian", function()
    local a = add("nameplate1")
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    remove("nameplate1")
    assert.are.equal("Senani Thunderheart", nameOf(a)) -- released: the client's English is back
    assert.are.equal(0, WFJ.SurfaceState.count(WFJ.NamePlates.SURFACE))
    Stub.units.nameplate2 = { name = "Kobold Vermin", guid = "Creature-0-1-2-3-6-0000" }
    add("nameplate2", a) -- the same unit frame, another unit
    assert.are.equal("Kobold Vermin", nameOf(a))
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    WFJ.NamePlates.onCombatEnd()
    assert.are.equal("Kobold Vermin", nameOf(a))
    -- reused without a removal event: the new unit's own name, never the old Italian
    Stub.units.nameplate3 = { name = "Hogger", guid = HOGGER }
    local b = add("nameplate3")
    assert.are.equal("Hogger il Rosso", nameOf(b))
    Stub.removeNamePlate("nameplate3")
    Stub.units.nameplate6 = { name = "Kobold Vermin", guid = "Creature-0-1-2-3-6-0000" }
    add("nameplate6", b)
    assert.are.equal("Kobold Vermin", nameOf(b))
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    assert.are.equal("Kobold Vermin", nameOf(b))
  end)

  it("Alt shows the English name; releasing it the Italian", function()
    local a = add("nameplate1")
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    assert.are.equal("Senani Thunderheart", nameOf(a))
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
  end)

  it("names in English (/fita nomi en) give the English back at once, and the Italian on the way back", function()
    local style = "it"
    WFJ.Names = { style = function() return style end }
    local a, b = add("nameplate1"), add("nameplate2")
    style = "en"; WFJ.State.fire("names")
    assert.are.equal("Senani Thunderheart", nameOf(a))
    assert.are.equal("Hogger", nameOf(b))
    style = "it"; WFJ.State.fire("names")
    assert.are.equal("Senani Cuore Tonante", nameOf(a))
    assert.are.equal("Hogger il Rosso", nameOf(b))
  end)

  it("hooks install once; a client without nameplates is skipped without error", function()
    assert.is_false(WFJ.NamePlates.init())
    assert.are.equal(1, #Stub.hooks["CompactUnitFrame_UpdateName"])
    H.uiTeardown()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    local bare = H.loadChunks(FILES)
    H.uiSetup(bare, {})
    _G.C_NamePlate = nil
    _G.CompactUnitFrame_UpdateName = function() end
    assert.has_no.errors(function() assert.is_false(bare.NamePlates.init()) end)
    assert.has_no.errors(function()
      bare.NamePlates.onName(nil)
      bare.NamePlates.onName({ unit = 3 })
      bare.NamePlates.onCombatEnd()
    end)
  end)
end)

-- Main owns the frames (ADR-016): it registers the plate events and routes them, and the combat events, to the module.
describe("Main routes the nameplate events", function()
  local Loader = require("tests.lua.spec.loader")

  it("NAME_PLATE_UNIT_ADDED / _REMOVED and PLAYER_REGEN_DISABLED / _ENABLED reach UI/NamePlates", function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI(); Stub.installItemTextAPI()
    local WFJ = Loader.load("OldpZ_ForeverITA")
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    local seen = {}
    for _, fn in ipairs({ "onAdded", "onRemoved", "onCombatStart", "onCombatEnd" }) do
      WFJ.NamePlates[fn] = function(token) seen[#seen + 1] = fn .. ":" .. tostring(token) end
    end
    Stub.fireAll("NAME_PLATE_UNIT_ADDED", "nameplate1")
    Stub.fireAll("PLAYER_REGEN_DISABLED")
    Stub.fireAll("NAME_PLATE_UNIT_REMOVED", "nameplate1")
    Stub.fireAll("PLAYER_REGEN_ENABLED")
    assert.are.same({ "onAdded:nameplate1", "onCombatStart:nil", "onRemoved:nameplate1", "onCombatEnd:nil" }, seen)
  end)

  it("a plate handler that raises is caught and logged once, never raised per plate event", function()
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installQuestAPI(); Stub.installTooltipAPI(); Stub.installGossipAPI(); Stub.installItemTextAPI()
    local WFJ = Loader.load("OldpZ_ForeverITA")
    Stub.fireAll("ADDON_LOADED", "OldpZ_ForeverITA")
    local calls, logged = 0, {}
    WFJ.NamePlates.onAdded = function() calls = calls + 1; error("plate boom") end
    WFJ.NamePlates.onRemoved = function() calls = calls + 1; error("plate boom") end
    WFJ.ErrorLog.recordCaught = function(msg) logged[#logged + 1] = tostring(msg) end
    for i = 1, 3 do
      assert.has_no.errors(function() Stub.fireAll("NAME_PLATE_UNIT_ADDED", "nameplate" .. i) end)
      assert.has_no.errors(function() Stub.fireAll("NAME_PLATE_UNIT_REMOVED", "nameplate" .. i) end)
    end
    assert.are.equal(6, calls) -- every event still reaches the module
    assert.are.equal(1, #logged)
    assert.truthy(logged[1]:find("plate boom", 1, true))
  end)
end)
