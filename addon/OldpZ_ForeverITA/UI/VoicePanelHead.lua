-- UI/VoicePanelHead.lua: the voice panel's head: the speaking NPC's 3D model, loading it, and its talk animation; a
-- book icon (the client's own art) for a line nobody on screen says. UI/VoicePanel owns the panel and calls these
-- with the head it built.
--   Head.build(parent, x, y, size) → head · Head.load(head, item) · Head.setTalking(head, talking)
-- The model comes from the unit on screen while that unit is still the speaker (the client is drawing it), else from
-- the creature id (the client's creature cache: it loads after /reload and a restart; a new client build empties the
-- cache, so an NPC not seen since has no model and gets the icon). A book page, or a line with no NPC (a quest taken
-- from an object), gets the icon. The model frame is never hidden, only made transparent: a hidden PlayerModel does
-- not keep the model it loads.
-- Adapted from forever-vo's ForeverVO/UI/TalkingHead.lua (MIT License; see ATTRIBUTION.md).
local _, WFJ = ...
local Head = {}
WFJ.VoicePanelHead = Head

local Compat = WFJ.Compat

Head.TALK_ANIMATION = 60 -- [likely: forever-vo's talk loop on Forever; in-game check: the head's mouth moves]
Head.ICON = "Interface\\Icons\\INV_Misc_Book_09" -- a book, from the client's icon set
local MODEL_SETTLE = 0.6 -- seconds a model load gets before a speaker with no model gets the icon
local ZOOM, CAMERA = 1, 1 -- PlayerModel:SetPortraitZoom, SetCamDistanceScale: the face fills the portrait

local function hasModel(m)
  local ok, id = pcall(m.GetModelFileID, m)
  return ok and id ~= nil and id ~= 0
end

local function animate(h)
  pcall(h.model.SetAnimation, h.model, h.talking and Head.TALK_ANIMATION or 0)
end

-- → the head: { model, icon } in a size × size box at (x, y) from `parent`'s top left
function Head.build(parent, x, y, size)
  local h = {}
  local createFrame = Compat.resolve("CreateFrame")
  h.model = createFrame("PlayerModel", nil, parent)
  h.model:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
  h.model:SetSize(size, size)
  h.model:SetScript("OnModelLoaded", function(m)
    pcall(m.SetPortraitZoom, m, ZOOM)
    pcall(m.SetCamDistanceScale, m, CAMERA)
    pcall(m.SetFacing, m, 0)
    animate(h)
  end)
  h.model:SetScript("OnAnimFinished", function() animate(h) end)
  h.icon = parent:CreateTexture(nil, "ARTWORK")
  h.icon:SetPoint("TOPLEFT", parent, "TOPLEFT", x + 4, y - 4)
  h.icon:SetSize(size - 8, size - 8)
  h.icon:SetTexture(Head.ICON)
  h.icon:Hide()
  return h
end

local function showModel(h, on)
  h.model:SetAlpha(on and 1 or 0)
  h.icon:SetShown(not on)
end

-- Loads `item`'s speaker (VoicePlayer's queue item: item.speaker = { creature, unit, guid } or nil).
function Head.load(h, item)
  local who = item and item.speaker
  if h.settleTimer then h.settleTimer:Cancel(); h.settleTimer = nil end
  if not who or not who.creature then
    h.loaded = nil
    showModel(h, false)
    return
  end
  local unit = who.unit
  local guid = Compat.resolve("UnitGUID")
  if unit and (type(guid) ~= "function" or guid(unit) ~= who.guid) then unit = nil end
  local want = unit and who.guid or who.creature
  if h.loaded == want and hasModel(h.model) then
    showModel(h, true)
    return
  end
  h.loaded = want
  showModel(h, true)
  if unit then
    h.model:SetUnit(unit)
  else
    h.model:ClearModel()
    h.model:SetCreature(who.creature)
  end
  animate(h)
  local timer = Compat.resolve("C_Timer")
  if type(timer) == "table" and type(timer.NewTimer) == "function" then
    h.settleTimer = timer.NewTimer(MODEL_SETTLE, function()
      h.settleTimer = nil
      showModel(h, hasModel(h.model))
    end)
  end
end

function Head.setTalking(h, talking)
  talking = talking and true or false
  if h.talking == talking then return end
  h.talking = talking
  animate(h)
end
