-- UI/UnitFrames.lua: the unit frames' fixed words on Forever (surface "unitframes", area "ui", ADR-016):
-- player / target / focus / boss / party frames and the compact (raid-style) unit frames of blizzard_unitframe, whose
-- camelot load set is the mainline one (blizzard_unitframe.toc). Almost everything on a unit frame is a NAME (unit,
-- aura) or a NUMBER (health, power, level) and is never touched; the fixed words are:
--   the target-style frames' "Dead" / "Unconscious": static XML FontStrings, text="DEAD" / text="UNCONSCIOUS"
--     (mainline/targetframe.xml:182, 187 in TargetFrameContent.TargetFrameContentMain.HealthBarsContainer; :448, :453
--     in the target-of-target HealthBar), shown and hidden by TargetFrameMixin:CheckDead (targetframe.lua:475–490).
--     Shown once at init for TargetFrame, FocusFrame, Boss1..5TargetFrame and their totFrame;
--   a compact unit frame's status text: CompactUnitFrame_UpdateStatusText (a global function, shared/
--     compactunitframe.lua:1084–1114) writes PLAYER_OFFLINE, DEAD, a health number, LOST_HEALTH or a percentage into
--     frame.statusText. Post-hooked; only the two words are ever shown. The health forms can be SECRET values on this
--     client (`issecretvalue`, blizzard_sharedxmlbase/securetypes.lua:6): the hook reads the text once, skips a
--     secret, and calls Labels.show only for one of the two words or to drop a record the client overwrote;
--   a compact raid group's title: CompactRaidGroup_InitializeForGroup: frame.title:SetFormattedText(GROUP_NUMBER,
--     groupIndex) (shared/compactraidgroup.lua:42–51), post-hooked; the compact party frame's title:
--     CompactPartyFrame_Generate → self.title:SetText(self.titleText), titleText = PARTY (shared/
--     compactpartyframe.lua:1–32, compactpartyframe.xml:11), post-hooked and shown at init when the frame exists;
--   the unit tooltip's instruction line: UnitFrame_UpdateTooltip (a global function, mainline/unitframe.lua:396–408):
--     GameTooltip_SetDefaultAnchor(GameTooltip, self) (owner = the unit frame, blizzard_sharedxml/
--     sharedtooltiptemplates.lua:87–88), GameTooltip:SetUnit, a blank line, UNIT_POPUP_RIGHT_CLICK, Show. Post-hooked:
--     when GameTooltip's owner is that frame, walked once with HelpTooltip.walkAs restricted to that one key; the
--     unit's name, level, class and guild lines never match it;
--   the "not present" icon tooltips: PartyMemberFrame's NotPresentIcon: SetText(self.tooltip) + Show
--     (mainline/partyframetemplates.xml:356–360), tooltip = PARTY_IN_PUBLIC_GROUP_MESSAGE | INCOMING_SUMMON_TOOLTIP_*
--     (mainline/partymemberframe.lua:595–614); the compact frame's centerStatusIcon: the same keys
--     (shared/compactunitframe.lua:1476–1499, 2160–2166). Owners registered with UI/HelpTooltip restricted to those
--     keys (a phased reason is client-built text and never matches): the party frames from PartyFrame's pool at init,
--     a compact frame's icon from the post-hook of CompactUnitFrame_UpdateCenterStatusIcon (registering is a table
--     write, repeated harmlessly).
-- One kind of NAME is written (ADR-103): an NPC's name on TargetFrame, FocusFrame, Boss1..5TargetFrame and their
--   target-of-target (`frame.name`, set by UnitFrame_Initialize). The client writes it in UnitFrame_Update
--   (self.name:SetText(GetUnitName(self.overrideName or self.unit)), mainline/unitframe.lua; TargetFrameMixin:Update
--   and the target-of-target's Update call it by its global name) and in UnitFrame_OnEvent's UNIT_NAME_UPDATE branch.
--   Both globals are post-hooked; the name is replaced only when Core/UnitNames answers for the English just read
--   (a creature's GUID, the row's English), through Render (Alt shows the English; /fita nomi en and back re-run
--   every frame: refreshNames). Player, pet, party and compact frames are never written (a vehicle's name in
--   PlayerFrame neither). In combat too by default; NAMES_OUT_OF_COMBAT (below) is the one switch to stop that.
--   ADR-058 check [from the mainline code as cited in this header and the retail family it shares, NOT re-read
--   against a Forever 1.60.1 extract: none is on this machine]: the name FontString has a fixed size in the XML;
--   no Blizzard code calls GetText / GetStringWidth / GetStringHeight on it or lays anything out from it, and no
--   protected call (the secure unit button's Show/Hide by its unit watch, SetPoint by edit mode) reads it. Not found
--   measured on a protected path, so it is written. UI/TaintWatch would name it on the first block; Task 12 checks it
--   in game, in combat, with the boss frames up.
-- Not here (stay English): a TextStatusBar's zero text (SetBarTextZeroText(DEAD), targetframe.lua:744,
--   partymemberframe.lua:359, 809), written inside the health text update on every health event, beside values that
--   can be secret; unit popup menu titles (RAID_TARGET_ICON, SET_FOCUS: the menu system's); HelpTips; edit-mode
--   system names.
local _, WFJ = ...
local UnitFrames = {}
WFJ.UnitFrames = UnitFrames

local SURFACE = "unitframes"
UnitFrames.SURFACE = SURFACE
local Compat = WFJ.Compat

-- Names: every unit name widget of the named frames (the compact frames' `name` is pooled and never addressed here).
-- NEVER_TOUCH is the DICTIONARY's refusal (Labels.show refuses these widgets on any surface, so a unit named like a UI
-- word, "Raid", is never translated as one). The NPC names below are written through Render, which does not consult
-- that list, so the target / focus / target-of-target / boss names stay listed here: the dictionary keeps away from
-- them while the name writer owns them. PlayerName and PetName are never written by anything.
UnitFrames.NEVER_TOUCH = {
  "PlayerFrame.PlayerFrameContent.PlayerFrameContentMain.PlayerName", "PlayerName",
  "TargetFrame.TargetFrameContent.TargetFrameContentMain.Name",
  "FocusFrame.TargetFrameContent.TargetFrameContentMain.Name",
  "TargetFrameToT.Name", "FocusFrameToT.Name", "PetName",
}
for i = 1, 5 do
  UnitFrames.NEVER_TOUCH[#UnitFrames.NEVER_TOUCH + 1] = "Boss" .. i .. "TargetFrame.TargetFrameContent"
    .. ".TargetFrameContentMain.Name"
end

-- The one switch for the NPC names on the target-style frames (ADR-103, Task 9): false (the default) writes them in
-- combat too; true leaves the client's English while InCombatLockdown() and puts the Italian back on
-- PLAYER_REGEN_ENABLED (Main → UnitFrames.onCombatEnd). Meant for the in-game check (Task 12): flip it here if the
-- taint watch ever traces a block to these FontStrings.
UnitFrames.NAMES_OUT_OF_COMBAT = false

local TARGET_STYLE = { "TargetFrame", "FocusFrame", "Boss1TargetFrame", "Boss2TargetFrame", "Boss3TargetFrame",
  "Boss4TargetFrame", "Boss5TargetFrame" }
local DEAD = { only = { DEAD = true, UNCONSCIOUS = true } }
local STATUS = { only = { PLAYER_OFFLINE = true, DEAD = true } }
local GROUP = { only = { GROUP_NUMBER = true } }
local PARTY = { only = { PARTY = true } }
local RIGHT_CLICK = { only = { "UNIT_POPUP_RIGHT_CLICK" } }
local NOT_PRESENT = { only = { "PARTY_IN_PUBLIC_GROUP_MESSAGE", "INCOMING_SUMMON_TOOLTIP_SUMMON_PENDING",
  "INCOMING_SUMMON_TOOLTIP_SUMMON_ACCEPTED", "INCOMING_SUMMON_TOOLTIP_SUMMON_DECLINED" } }

-- The client's global writers, post-hooked by name: { global function, this module's handler }.
local GLOBAL_HOOKS = {
  { "CompactUnitFrame_UpdateStatusText", "onStatusText" },
  { "CompactUnitFrame_UpdateCenterStatusIcon", "onCenterIcon" },
  { "CompactRaidGroup_InitializeForGroup", "onGroupInit" },
  { "CompactPartyFrame_Generate", "onPartyGenerate" },
  { "UnitFrame_UpdateTooltip", "onUnitTooltip" },
  { "UnitFrame_Update", "onName" },
  { "UnitFrame_OnEvent", "onUnitEvent" },
}

local function declareAll()
  for _, name in ipairs(TARGET_STYLE) do Compat.declare(SURFACE, name, { name }) end
  Compat.declare(SURFACE, "partyFrame", { "PartyFrame" })
  Compat.declare(SURFACE, "compactParty", { "CompactPartyFrame" })
  Compat.declare(SURFACE, "tooltip", { "GameTooltip" })
  Compat.declare(SURFACE, "isSecret", { "issecretvalue" })
  Compat.declare(SURFACE, "inCombat", { "InCombatLockdown" })
  Compat.declare(SURFACE, "unitGUID", { "UnitGUID" })
  for _, hook in ipairs(GLOBAL_HOOKS) do Compat.declare(SURFACE, hook[1], { hook[1] }) end
  Compat.declare(SURFACE, "enDead", { "DEAD" })
  Compat.declare(SURFACE, "enOffline", { "PLAYER_OFFLINE" })
end

local function get(key) return Compat.get(SURFACE, key) end

local statusKey = WFJ.Labels.keyer("status.") -- a compact frame's status text (pooled frames: keyed by widget)
local titleKey = WFJ.Labels.keyer("group.") -- a compact group's title

-- The two FontStrings of one health container (a target-style frame's, or its target-of-target's). → words found
local function showDead(prefix, container)
  if type(container) ~= "table" then return 0 end
  return WFJ.Labels.show(SURFACE, prefix .. ".dead", container.DeadText, nil, DEAD)
    + WFJ.Labels.show(SURFACE, prefix .. ".unconscious", container.UnconsciousText, nil, DEAD)
end

-- The static "Dead" / "Unconscious" labels of every target-style frame that exists. → words found
function UnitFrames.showStatic()
  local n = 0
  for _, name in ipairs(TARGET_STYLE) do
    local frame = get(name)
    if type(frame) == "table" then
      local content = frame.TargetFrameContent
      local main = type(content) == "table" and content.TargetFrameContentMain or nil
      n = n + showDead(name, type(main) == "table" and main.HealthBarsContainer or nil)
      local tot = frame.totFrame
      n = n + showDead(name .. ".tot", type(tot) == "table" and tot.HealthBar or nil)
    end
  end
  local party = get("compactParty")
  if type(party) == "table" then n = n + WFJ.Labels.show(SURFACE, "party.title", party.title, nil, PARTY) end
  WFJ.Render.updateBanner(SURFACE)
  return n
end

-- → true when `text` must not be read further (a secret value: comparing it from addon code can raise).
local function secret(text)
  local isSecret = get("isSecret")
  return type(isSecret) == "function" and isSecret(text) == true
end

-- hooksecurefunc target (CompactUnitFrame_UpdateStatusText). Runs on every health event of every compact frame, so it
-- does the least it can: one GetText, and Labels.show only for one of the two words or over an existing record.
function UnitFrames.onStatusText(frame)
  local fs = type(frame) == "table" and frame.statusText or nil
  if type(fs) ~= "table" or type(fs.GetText) ~= "function" then return 0 end
  local recKey = statusKey(fs)
  local text = fs:GetText()
  if secret(text) then
    WFJ.SurfaceState.drop(SURFACE, recKey)
    return 0
  end
  if text ~= get("enDead") and text ~= get("enOffline") and not WFJ.SurfaceState.get(SURFACE, recKey) then return 0 end
  return WFJ.Labels.show(SURFACE, recKey, fs, nil, STATUS)
end

-- hooksecurefunc target (CompactRaidGroup_InitializeForGroup): "Group %d" on the group's title button.
function UnitFrames.onGroupInit(frame)
  local title = type(frame) == "table" and frame.title or nil
  if type(title) ~= "table" then return 0 end
  return WFJ.Labels.show(SURFACE, titleKey(title), title, nil, GROUP)
end

-- hooksecurefunc target (CompactPartyFrame_Generate): the frame exists from here on.
function UnitFrames.onPartyGenerate()
  Compat.declare(SURFACE, "compactParty", { "CompactPartyFrame" }) -- re-resolve: it did not exist at init
  local party = get("compactParty")
  if type(party) ~= "table" then return 0 end
  return WFJ.Labels.show(SURFACE, "party.title", party.title, nil, PARTY)
end

-- hooksecurefunc target (CompactUnitFrame_UpdateCenterStatusIcon): the icon owns a help tooltip.
function UnitFrames.onCenterIcon(frame)
  local icon = type(frame) == "table" and frame.centerStatusIcon or nil
  if type(icon) == "table" and not WFJ.HelpTooltip.registered(icon) then WFJ.HelpTooltip.register(icon, NOT_PRESENT) end
end

-- hooksecurefunc target (UnitFrame_UpdateTooltip): the unit tooltip's "<Right click for Frame Settings>" line.
function UnitFrames.onUnitTooltip(frame)
  local tt = get("tooltip")
  if type(tt) ~= "table" or type(tt.GetOwner) ~= "function" or frame == nil or tt:GetOwner() ~= frame then return 0 end
  return WFJ.HelpTooltip.walkAs(tt, RIGHT_CLICK)
end

-- The frames whose `name` this surface may write: the target-style frames and their target-of-target, found at init.
-- Weak-keyed: { [frame] = record key }. UnitFrame_Update also runs for the player, pet and party frames (a vehicle's
-- name in the player frame has a Vehicle- GUID): none of them is here, so none is ever written.
local nameFrames = setmetatable({}, { __mode = "k" })

local function registerNameFrames()
  for _, name in ipairs(TARGET_STYLE) do
    local frame = get(name)
    if type(frame) == "table" then
      nameFrames[frame] = "name." .. name
      if type(frame.totFrame) == "table" then nameFrames[frame.totFrame] = "name." .. name .. ".tot" end
    end
  end
end

local function inCombat()
  local fn = get("inCombat")
  return type(fn) == "function" and fn() and true or false
end

-- hooksecurefunc target (UnitFrame_Update; also called for UNIT_NAME_UPDATE and the names / combat refreshes): an
-- NPC's name on one of the target-style frames takes its `unit` row's Italian (Core/UnitNames: a creature's GUID,
-- the English shown hashing to the row's). Written only over the English just read; our own text still showing (an
-- event for another unit) is left alone; anything else drops this frame's record without writing over the client.
-- → true when the name was written
function UnitFrames.onName(frame)
  local key = frame ~= nil and nameFrames[frame] or nil
  local fs = key and frame.name or nil
  if type(fs) ~= "table" or type(fs.GetText) ~= "function" then return false end
  local text = fs:GetText()
  if secret(text) then
    WFJ.SurfaceState.drop(SURFACE, key)
    return false
  end
  local rec = WFJ.SurfaceState.get(SURFACE, key)
  if rec and rec.fs == fs and rec.applied ~= nil and text == rec.applied then return false end
  local unit = frame.overrideName or frame.unit
  local U = WFJ.UnitNames
  local ja = not (UnitFrames.NAMES_OUT_OF_COMBAT and inCombat()) and U and type(text) == "string"
    and U.forUnit(unit, text) or nil
  local unitGUID = get("unitGUID")
  local id = ja and type(unitGUID) == "function" and WFJ.Collector.creatureId(unitGUID(unit)) or nil
  if not id then
    WFJ.SurfaceState.drop(SURFACE, key)
    return false
  end
  return WFJ.Render.show(SURFACE, key, fs, text, "ui", "unit.name", id)
end

-- hooksecurefunc target (UnitFrame_OnEvent, every unit event of every unit frame): only UNIT_NAME_UPDATE rewrites
-- the name (mainline/unitframe.lua), so only it is looked at.
function UnitFrames.onUnitEvent(frame, event)
  if event == "UNIT_NAME_UPDATE" then return UnitFrames.onName(frame) end
  return false
end

-- Every name frame again: the English back where our text still shows, then the Italian if the style asks for it.
-- → the number of names written
function UnitFrames.refreshNames()
  local n = 0
  for frame, key in pairs(nameFrames) do
    WFJ.SurfaceState.drop(SURFACE, key)
    if UnitFrames.onName(frame) then n = n + 1 end
  end
  return n
end
-- The State "names" event (/fita nomi): Render's refresh does not consult the names style, so this surface does.
WFJ.State.on("names", function() UnitFrames.refreshNames() end)

-- PLAYER_REGEN_ENABLED (Main): in out-of-combat mode, the names the client wrote during combat. → names written
function UnitFrames.onCombatEnd()
  if not UnitFrames.NAMES_OUT_OF_COMBAT then return 0 end
  return UnitFrames.refreshNames()
end

-- The party member frames PartyFrame's pool holds now. → the number of icons registered
local function registerPartyIcons()
  local party = get("partyFrame")
  local pool = type(party) == "table" and party.PartyMemberFramePool or nil
  if type(pool) ~= "table" or type(pool.EnumerateActive) ~= "function" then return 0 end
  local n = 0
  for member in pool:EnumerateActive() do
    local icon = type(member) == "table" and member.NotPresentIcon or nil
    if type(icon) == "table" then
      WFJ.HelpTooltip.register(icon, NOT_PRESENT)
      n = n + 1
    end
  end
  return n
end

local hooked = false

-- Called by Main after Compat.init, HelpTooltip.init and ButtonText.init. → false when the mainline unit frames are
-- absent (a TargetFrame without TargetFrameContent).
function UnitFrames.init()
  declareAll()
  local target = get("TargetFrame")
  if hooked or type(target) ~= "table" or type(target.TargetFrameContent) ~= "table" then return false end
  hooked = true
  registerNameFrames()
  for _, hook in ipairs(GLOBAL_HOOKS) do
    local name, handler = hook[1], hook[2]
    if type(get(name)) == "function" then
      hooksecurefunc(name, function(...) return UnitFrames[handler](...) end)
    end
  end
  registerPartyIcons()
  UnitFrames.showStatic()
  return true
end
