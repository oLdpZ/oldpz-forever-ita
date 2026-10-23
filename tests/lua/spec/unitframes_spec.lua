-- UI/UnitFrames.lua (hud) over unit frames replayed from Forever blizzard_unitframe: the target-style
-- frames' static DeadText / UnconsciousText (mainline/targetframe.xml:182–187, 448–453), the compact frames' status
-- text (shared/compactunitframe.lua:1084–1114), group titles (shared/compactraidgroup.lua:42–51,
-- compactpartyframe.lua:1–32), the unit tooltip's instruction line (mainline/unitframe.lua:396–408) and the
-- "not present" icon tooltips (mainline/partyframetemplates.xml:356–360, compactunitframe.lua:2160–2166).
-- Unit names, health numbers and secret values are never touched.
local H = require("tests.lua.spec.helpers")
local Stub = require("tests.lua.spec.wow_stub")

local FILES = {}
for i, f in ipairs(H.UI_FILES) do FILES[i] = f end
FILES[#FILES + 1] = "Core/UnitNames.lua"
FILES[#FILES + 1] = "UI/UnitFrames.lua"

local UI = {
  DEAD = { "Dead", "死亡" },
  UNCONSCIOUS = { "Unconscious", "気絶" },
  PLAYER_OFFLINE = { "Offline", "オフライン" },
  GROUP_NUMBER = { "Group %d", "グループ%d" },
  PARTY = { "Party", "パーティ" },
  UNIT_POPUP_RIGHT_CLICK = { "<Right click for Frame Settings>", "<右クリックでフレーム設定>" },
  PARTY_IN_PUBLIC_GROUP_MESSAGE = { "This player is currently in an instance group.",
    "このプレイヤーは現在インスタンスグループにいます。" },
  INCOMING_SUMMON_TOOLTIP_SUMMON_PENDING = { "Summon Pending", "召喚待ち" },
  RAID = { "Raid", "レイド" }, -- a dictionary word a unit may be NAMED
}
local function en(key) return UI[key][1] end
local function ja(key) return UI[key][2] end
local function tip(i) return _G["GameTooltipTextLeft" .. i]:GetText() end

local SECRET = {} -- stands for a secret value: comparing or matching it would raise on the client

local function targetStyle(name)
  local f = CreateFrame("Button", name)
  local container = { DeadText = Stub.fontString(en("DEAD")), UnconsciousText = Stub.fontString(en("UNCONSCIOUS")) }
  f.TargetFrameContent = { TargetFrameContentMain = { HealthBarsContainer = container,
    Name = Stub.fontString("Raid") } }
  f.totFrame = { HealthBar = { DeadText = Stub.fontString(en("DEAD")),
    UnconsciousText = Stub.fontString(en("UNCONSCIOUS")) }, Name = Stub.fontString("Hogger") }
  return f
end

local function compactFrame()
  local f = CreateFrame("Button")
  f.statusText = Stub.fontString("")
  f.name = Stub.fontString("Raid")
  f.centerStatusIcon = CreateFrame("Button")
  f.centerStatusIcon:SetScript("OnEnter", function(self)
    _G.GameTooltip:SetOwner(self)
    _G.GameTooltip:SetText(self.tooltip)
    _G.GameTooltip:Show()
  end)
  return f
end

local function installUnitFrames()
  targetStyle("TargetFrame")
  targetStyle("FocusFrame")
  targetStyle("Boss1TargetFrame")
  local party = CreateFrame("Frame", "PartyFrame")
  local member = CreateFrame("Button")
  member.NotPresentIcon = CreateFrame("Frame")
  member.NotPresentIcon:SetScript("OnEnter", function(self)
    _G.GameTooltip:SetOwner(self)
    _G.GameTooltip:SetText(self.tooltip)
    _G.GameTooltip:Show()
  end)
  party.PartyMemberFramePool = { EnumerateActive = function()
    local done = false
    return function() if not done then done = true; return member end end
  end }
  party.member = member
  _G.CompactUnitFrame_UpdateStatusText = function(frame) frame.statusText.text = frame.nextStatus end
  _G.CompactUnitFrame_UpdateCenterStatusIcon = function(frame) frame.centerStatusIcon.tooltip = frame.nextTooltip end
  _G.CompactRaidGroup_InitializeForGroup = function(frame, index)
    frame.title:SetText(string.format("Group %d", index))
  end
  _G.CompactPartyFrame_Generate = function()
    local f = CreateFrame("Frame", "CompactPartyFrame")
    f.title = Stub.button(nil, en("PARTY"))
    return f
  end
  _G.UnitFrame_UpdateTooltip = function(self)
    local tt = _G.GameTooltip
    tt:SetOwner(self)
    tt:ClearLines()
    tt:AddLine(self.unitName)
    tt:AddLine("Level 12 Orc Warrior")
    tt:AddLine(" ")
    tt:AddLine(en("UNIT_POPUP_RIGHT_CLICK"))
    tt:Show()
  end
  _G.issecretvalue = function(v) return v == SECRET end
end

local GLOBALS = { "TargetFrame", "FocusFrame", "Boss1TargetFrame", "PartyFrame", "CompactPartyFrame",
  "CompactUnitFrame_UpdateStatusText", "CompactUnitFrame_UpdateCenterStatusIcon",
  "CompactRaidGroup_InitializeForGroup", "CompactPartyFrame_Generate", "UnitFrame_UpdateTooltip", "issecretvalue" }

describe("the unit frames' fixed words on Forever", function()
  local WFJ

  local function load()
    local ns = H.loadChunks(FILES)
    ns.Lookup = { get = function() return nil end }
    H.uiSetup(ns, UI)
    return ns
  end

  local function fresh()
    H.uiTeardown()
    for _, n in ipairs(GLOBALS) do _G[n] = nil end
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installTooltipAPI()
  end

  before_each(function()
    fresh()
    WFJ = load()
    installUnitFrames()
    WFJ.Labels.forbidNames(WFJ.UnitFrames.NEVER_TOUCH)
    assert.is_true(WFJ.UnitFrames.init())
  end)

  after_each(function()
    H.uiTeardown()
    Stub.keys.alt = false
    for _, n in ipairs(GLOBALS) do _G[n] = nil end
  end)

  it("Dead / Unconscious translate on the target-style frames and their target-of-target; names stay English",
    function()
      for _, name in ipairs({ "TargetFrame", "FocusFrame", "Boss1TargetFrame" }) do
        local main = _G[name].TargetFrameContent.TargetFrameContentMain
        assert.are.equal(ja("DEAD"), main.HealthBarsContainer.DeadText:GetText())
        assert.are.equal(ja("UNCONSCIOUS"), main.HealthBarsContainer.UnconsciousText:GetText())
        assert.are.equal(ja("DEAD"), _G[name].totFrame.HealthBar.DeadText:GetText())
        assert.are.equal("Raid", main.Name:GetText()) -- a unit named like a dictionary word
      end
      Stub.keys.alt = true
      WFJ.Modifier.refresh()
      assert.are.equal(en("DEAD"), _G.TargetFrame.TargetFrameContent.TargetFrameContentMain.HealthBarsContainer
        .DeadText:GetText())
    end)

  it("a compact frame's status text: the two words translate, numbers and secret values are never read", function()
    local f = compactFrame()
    f.nextStatus = en("DEAD")
    _G.CompactUnitFrame_UpdateStatusText(f)
    assert.are.equal(ja("DEAD"), f.statusText:GetText())
    f.nextStatus = "4521" -- alive again: the record is dropped, the number stays
    _G.CompactUnitFrame_UpdateStatusText(f)
    assert.are.equal("4521", f.statusText:GetText())
    Stub.keys.alt = true
    WFJ.Modifier.refresh()
    assert.are.equal("4521", f.statusText:GetText()) -- no stale word is restored over it
    Stub.keys.alt = false
    WFJ.Modifier.refresh()
    f.nextStatus = en("PLAYER_OFFLINE")
    _G.CompactUnitFrame_UpdateStatusText(f)
    assert.are.equal(ja("PLAYER_OFFLINE"), f.statusText:GetText())
    f.nextStatus = SECRET
    assert.has_no.errors(function() _G.CompactUnitFrame_UpdateStatusText(f) end)
    assert.are.equal(SECRET, f.statusText:GetText())
    assert.are.equal("Raid", f.name:GetText())
  end)

  it("group titles: Group %d and Party translate", function()
    local group = CreateFrame("Frame")
    group.title = Stub.button(nil, "")
    _G.CompactRaidGroup_InitializeForGroup(group, 3)
    assert.are.equal("グループ3", group.title:GetText())
    local party = _G.CompactPartyFrame_Generate() -- created after init
    assert.are.equal(ja("PARTY"), party.title:GetText())
  end)

  it("the unit tooltip: only the instruction line translates", function()
    _G.TargetFrame.unitName = "Raid"
    _G.UnitFrame_UpdateTooltip(_G.TargetFrame)
    assert.are.equal("Raid", tip(1))
    assert.are.equal("Level 12 Orc Warrior", tip(2))
    assert.are.equal(ja("UNIT_POPUP_RIGHT_CLICK"), tip(4))
    assert.is_false(WFJ.HelpTooltip.registered(_G.TargetFrame))
  end)

  it("the not-present icons own help tooltips restricted to their keys", function()
    local icon = _G.PartyFrame.member.NotPresentIcon
    icon.tooltip = en("PARTY_IN_PUBLIC_GROUP_MESSAGE")
    icon.scripts.OnEnter(icon)
    assert.are.equal(ja("PARTY_IN_PUBLIC_GROUP_MESSAGE"), tip(1))
    icon.tooltip = "Raid" -- a phased reason / any other text: not in the restricted set
    icon.scripts.OnEnter(icon)
    assert.are.equal("Raid", tip(1))
    local f = compactFrame()
    f.nextTooltip = en("INCOMING_SUMMON_TOOLTIP_SUMMON_PENDING")
    _G.CompactUnitFrame_UpdateCenterStatusIcon(f)
    f.centerStatusIcon.scripts.OnEnter(f.centerStatusIcon)
    assert.are.equal(ja("INCOMING_SUMMON_TOOLTIP_SUMMON_PENDING"), tip(1))
  end)

  it("client names bound to the wrong type degrade to untouched English with no error", function()
    fresh()
    local ns = load()
    installUnitFrames()
    _G.FocusFrame = "moved"
    _G.Boss1TargetFrame.TargetFrameContent = 5
    _G.TargetFrame.totFrame = true
    _G.PartyFrame.PartyMemberFramePool = 3
    _G.CompactUnitFrame_UpdateStatusText = "not a function"
    _G.UnitFrame_UpdateTooltip = false
    _G.issecretvalue = 12
    assert.has_no.errors(function() assert.is_true(ns.UnitFrames.init()) end)
    assert.are.equal(ja("DEAD"), _G.TargetFrame.TargetFrameContent.TargetFrameContentMain.HealthBarsContainer
      .DeadText:GetText())
    assert.has_no.errors(function()
      ns.UnitFrames.onStatusText({ statusText = 9 })
      ns.UnitFrames.onStatusText("x")
      ns.UnitFrames.onGroupInit({ title = false })
      ns.UnitFrames.onCenterIcon({ centerStatusIcon = "x" })
      ns.UnitFrames.onUnitTooltip(nil)
    end)
  end)

  it("hooks install once; a client without the mainline target frame is skipped without error", function()
    assert.is_false(WFJ.UnitFrames.init())
    assert.are.equal(1, #Stub.hooks["CompactUnitFrame_UpdateStatusText"])
    fresh()
    local bare = load()
    _G.TargetFrame = CreateFrame("Button", "TargetFrame") -- no TargetFrameContent
    assert.has_no.errors(function() assert.is_false(bare.UnitFrames.init()) end)
  end)
end)

-- ADR-103 / Task 9: an NPC's name on the target, focus, target-of-target and boss frames takes the Italian of its
-- `unit` row (Core/UnitNames), written after the client's own UnitFrame_Update (mainline/unitframe.lua:
-- self.name:SetText(GetUnitName(self.unit))) and the UNIT_NAME_UPDATE branch of UnitFrame_OnEvent. A player's name,
-- the player frame, a secret text and another English stay as written; Alt and /fita nomi en give the English
-- back; the dictionary surface still refuses those widgets.
describe("the NPC names on the target-style frames", function()
  local WFJ
  local SENANI = "Creature-0-1-2-3-12696-0000"
  local HOGGER = "Creature-0-1-2-3-448-0000"
  local GLOBALS2 = { "TargetFrame", "FocusFrame", "Boss1TargetFrame", "PlayerFrame", "UnitFrame_Update",
    "UnitFrame_OnEvent", "issecretvalue", "UnitFrame_UpdateTooltip" }
  local ROWS = { RAID = { "Raid", "Incursione" } }

  local function frame(name, unit)
    local f = CreateFrame("Button", name)
    f.unit = unit
    f.name = Stub.fontString("")
    f.TargetFrameContent = { TargetFrameContentMain = { Name = f.name, HealthBarsContainer = {} } }
    f.totFrame = CreateFrame("Button")
    f.totFrame.unit = unit .. "target"
    f.totFrame.name = Stub.fontString("")
    f.totFrame.Name = f.totFrame.name
    return f
  end

  local function update(f) _G.UnitFrame_Update(f) end
  local function nameOf(f) return f.name:GetText() end

  before_each(function()
    H.uiTeardown()
    for _, n in ipairs(GLOBALS2) do _G[n] = nil end
    Stub.install(H.ADDON_DIR .. "/OldpZ_ForeverITA.toc")
    Stub.installTooltipAPI()
    Stub.installKeyAPI()
    WFJ = H.loadChunks(FILES)
    local function h1(text) return (WFJ.Hash.h32x2(WFJ.Normalize.v1(text))) end
    local UNIT = { ["unit.name"] = {
      [12696] = { ja = "Senani Cuore Tonante", status = ".", h1 = h1("Senani Thunderheart") },
      [448] = { ja = "Hogger il Rosso", status = ".", h1 = h1("Hogger") },
    } }
    local function lookup(kind, id) return UNIT[kind] and UNIT[kind][id] or nil end
    WFJ.Lookup = { get = lookup }
    H.uiSetup(WFJ, ROWS, { lookup = lookup })
    -- the client's writers, as mainline/unitframe.lua writes the name
    _G.UnitFrame_Update = function(self) self.name:SetText(_G.UnitName(self.unit)) end
    _G.UnitFrame_OnEvent = function(self, event)
      if event == "UNIT_NAME_UPDATE" then self.name:SetText(_G.UnitName(self.unit)) end
    end
    frame("TargetFrame", "target")
    frame("FocusFrame", "focus")
    frame("Boss1TargetFrame", "boss1")
    local player = CreateFrame("Button", "PlayerFrame")
    player.unit = "vehicle"
    player.name = Stub.fontString("")
    Stub.units.target = { name = "Senani Thunderheart", guid = SENANI }
    Stub.units.focus = { name = "Hogger", guid = HOGGER }
    Stub.units.boss1 = { name = "Senani Thunderheart", guid = SENANI }
    Stub.units.targettarget = { name = "Hogger", guid = HOGGER }
    Stub.units.vehicle = { name = "Senani Thunderheart", guid = "Vehicle-0-1-2-3-12696-0000" }
    WFJ.Labels.forbidNames(WFJ.UnitFrames.NEVER_TOUCH)
    assert.is_true(WFJ.UnitFrames.init())
  end)

  after_each(function()
    H.uiTeardown()
    Stub.keys.alt = false
    Stub.combat = false
    Stub.units = {}
    WFJ.UnitFrames.NAMES_OUT_OF_COMBAT = false
    for _, n in ipairs(GLOBALS2) do _G[n] = nil end
  end)

  it("a creature on the target, focus, boss and target-of-target frames shows its Italian name", function()
    update(_G.TargetFrame)
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    update(_G.FocusFrame)
    assert.are.equal("Hogger il Rosso", nameOf(_G.FocusFrame))
    update(_G.Boss1TargetFrame)
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.Boss1TargetFrame))
    update(_G.TargetFrame.totFrame)
    assert.are.equal("Hogger il Rosso", nameOf(_G.TargetFrame.totFrame))
  end)

  it("a player, another English and the player frame stay as written", function()
    Stub.units.target = { name = "Senani Thunderheart", guid = "Player-1-0ABCDEF0" }
    update(_G.TargetFrame)
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    Stub.units.target = { name = "Senani Stormheart", guid = SENANI } -- a Forever rename
    update(_G.TargetFrame)
    assert.are.equal("Senani Stormheart", nameOf(_G.TargetFrame))
    update(_G.PlayerFrame) -- a vehicle's name in the player frame: never ours
    assert.are.equal("Senani Thunderheart", nameOf(_G.PlayerFrame))
  end)

  it("a new target replaces the Italian with its own name; UNIT_NAME_UPDATE gets the Italian again", function()
    update(_G.TargetFrame)
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    Stub.units.target = { name = "Kobold Vermin", guid = "Creature-0-1-2-3-6-0000" }
    update(_G.TargetFrame)
    assert.are.equal("Kobold Vermin", nameOf(_G.TargetFrame))
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    assert.are.equal("Kobold Vermin", nameOf(_G.TargetFrame)) -- no stale name written back
    Stub.units.target = { name = "Senani Thunderheart", guid = SENANI }
    _G.UnitFrame_OnEvent(_G.TargetFrame, "UNIT_NAME_UPDATE", "target")
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    _G.UnitFrame_OnEvent(_G.TargetFrame, "UNIT_HEALTH", "target") -- any other event: nothing read
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    update(_G.TargetFrame) -- the same unit again: still Italian
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
  end)

  it("Alt shows the English name; releasing it the Italian", function()
    update(_G.Boss1TargetFrame)
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    assert.are.equal("Senani Thunderheart", nameOf(_G.Boss1TargetFrame))
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.Boss1TargetFrame))
  end)

  it("names in English (/fita nomi en) give the English back at once, and the Italian on the way back", function()
    local style = "it"
    WFJ.Names = { style = function() return style end }
    update(_G.TargetFrame)
    update(_G.FocusFrame)
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    style = "en"; WFJ.State.fire("names")
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    assert.are.equal("Hogger", nameOf(_G.FocusFrame))
    update(_G.TargetFrame)
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    style = "it"; WFJ.State.fire("names")
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    assert.are.equal("Hogger il Rosso", nameOf(_G.FocusFrame))
  end)

  it("a secret name is never read; the dictionary surface still refuses the name widgets", function()
    _G.issecretvalue = function(v) return v == "Senani Thunderheart" end
    assert.has_no.errors(function() update(_G.TargetFrame) end)
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    _G.issecretvalue = nil
    _G.TargetFrame.name:SetText("Raid") -- a unit named like a dictionary word
    assert.are.equal(0, WFJ.Labels.show(WFJ.UnitFrames.SURFACE, "probe", _G.TargetFrame.name))
    assert.are.equal("Raid", nameOf(_G.TargetFrame))
  end)

  it("out-of-combat mode: in combat the English stays, the Italian comes back when combat ends", function()
    WFJ.UnitFrames.NAMES_OUT_OF_COMBAT = true
    Stub.combat = true
    update(_G.TargetFrame)
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    Stub.combat = false
    WFJ.UnitFrames.onCombatEnd()
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    WFJ.UnitFrames.NAMES_OUT_OF_COMBAT = false -- the default: written in combat too
    Stub.combat = true
    Stub.units.target = { name = "Hogger", guid = HOGGER }
    update(_G.TargetFrame)
    assert.are.equal("Hogger il Rosso", nameOf(_G.TargetFrame))
  end)

  -- the addon's writes to one name widget (the stub counts SetText / SetFont made from addon code)
  local function addonWrites(fs) return fs.calls.addonSetText + fs.calls.addonSetFont end

  it("out-of-combat mode: combat start gives the English back; Alt in combat writes nothing", function()
    WFJ.UnitFrames.NAMES_OUT_OF_COMBAT = true
    update(_G.TargetFrame)
    update(_G.Boss1TargetFrame)
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    WFJ.UnitFrames.onCombatStart() -- PLAYER_REGEN_DISABLED, before the lockdown
    Stub.combat = true
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    assert.are.equal("Senani Thunderheart", nameOf(_G.Boss1TargetFrame))
    local fs, boss = _G.TargetFrame.name, _G.Boss1TargetFrame.name
    local before, bossBefore = addonWrites(fs), addonWrites(boss)
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    update(_G.TargetFrame) -- the client's own update in combat
    _G.UnitFrame_OnEvent(_G.TargetFrame, "UNIT_NAME_UPDATE", "target")
    assert.are.equal(before, addonWrites(fs))
    assert.are.equal(bossBefore, addonWrites(boss))
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    Stub.combat = false
    WFJ.UnitFrames.onCombatEnd()
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.Boss1TargetFrame))
  end)

  it("out-of-combat mode: /fita nomi in combat writes nothing; the style applies when combat ends", function()
    local style = "en"
    WFJ.Names = { style = function() return style end }
    WFJ.UnitFrames.NAMES_OUT_OF_COMBAT = true
    update(_G.TargetFrame)
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    WFJ.UnitFrames.onCombatStart()
    Stub.combat = true
    local fs = _G.TargetFrame.name
    local before = addonWrites(fs)
    style = "it"; WFJ.State.fire("names")
    assert.are.equal(before, addonWrites(fs))
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    Stub.combat = false
    WFJ.UnitFrames.onCombatEnd()
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
  end)

  it("the Italian shown, then the client writes a secret name: no error, no write, the record dropped", function()
    update(_G.TargetFrame)
    assert.are.equal("Senani Cuore Tonante", nameOf(_G.TargetFrame))
    local SECRET_NAME = {} -- a secret value: never compared
    _G.issecretvalue = function(v) return v == SECRET_NAME end
    Stub.units.target = { name = SECRET_NAME, guid = SENANI }
    local fs = _G.TargetFrame.name
    local before = fs.calls.addonSetText
    assert.has_no.errors(function() update(_G.TargetFrame) end)
    assert.are.equal(SECRET_NAME, nameOf(_G.TargetFrame))
    assert.are.equal(before, fs.calls.addonSetText)
    assert.is_nil(WFJ.SurfaceState.get(WFJ.UnitFrames.SURFACE, "name.TargetFrame"))
  end)

  it("a target change while Alt is held shows the new English; releasing Alt gives its Italian", function()
    update(_G.TargetFrame)
    Stub.keys.alt = true; WFJ.Modifier.refresh()
    assert.are.equal("Senani Thunderheart", nameOf(_G.TargetFrame))
    Stub.units.target = { name = "Hogger", guid = HOGGER }
    update(_G.TargetFrame)
    assert.are.equal("Hogger", nameOf(_G.TargetFrame))
    Stub.keys.alt = false; WFJ.Modifier.refresh()
    assert.are.equal("Hogger il Rosso", nameOf(_G.TargetFrame))
  end)
end)
