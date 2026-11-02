-- UI/VoicePanel.lua: the small voice panel: the speaker's 3D head (UI/VoicePanelHead), its name, a stop button (■:
-- the line stops and the queue empties), a next button (⏭: the next waiting line now) and "+N" while N lines wait.
-- No text: the window beside it already shows the line.
--   * Built by the first line that plays (State "voiceQueue" from UI/VoicePlayer): without a voice pack it never
--     exists. Named WFJVoicePanel, about 220 × 64, on UIParent (never a child of a Blizzard frame).
--   * Placed beside the window that showed the line (its TOPLEFT on the window's TOPRIGHT, 4 px right): the quest,
--     gossip or book window. A window that closes leaves the panel where it was: the line plays on; a line the
--     quest log replays shows it where it last was (or under the top of the screen the first time).
--   * Once nothing plays it goes 3 s later; the stop button hides it at once.
-- Taint: only our own frames, anchored to a Blizzard frame; no Blizzard frame is written or hooked here.
local _, WFJ = ...
local Panel = {}
WFJ.VoicePanel = Panel

local Compat = WFJ.Compat
local Head = WFJ.VoicePanelHead

local WIDTH, HEIGHT = 220, 64
local HEAD_SIZE = 56
local BUTTON = 20
local LINGER = 3 -- seconds the panel stays once nothing plays
local WINDOWS = { QuestFrame = true, GossipFrame = true, ItemTextFrame = true }
-- the client's own art: the spellbook's next-page arrow for ⏭ [unverified on Forever; in-game check: the arrow
-- shows]; the stop square is drawn (a plain colour texture), so no image is shipped or guessed
local ICON_NEXT = "Interface\\Buttons\\UI-SpellbookIcon-NextPage-Up"
local ICON_HIGHLIGHT = "Interface\\Buttons\\UI-Common-MouseHilight"

local frame, head, nameText, waiting, buttons
local hideTimer
local placed = false

local function pick(key)
  local t = WFJ.OptionsText and WFJ.OptionsText.T[key]
  if not t then return "" end
  return WFJ.OptionsWidgets and WFJ.OptionsWidgets.pick(t.en, t.it) or t.it
end

-- A button's tooltip, in the addon's language (GameTooltip, owned by our button only while hovered).
local function tooltip(button, key)
  button:SetScript("OnEnter", function(self)
    local tip = Compat.resolve("GameTooltip")
    if type(tip) ~= "table" or type(tip.SetOwner) ~= "function" then return end
    tip:SetOwner(self, "ANCHOR_RIGHT")
    tip:SetText(pick(key))
    tip:Show()
  end)
  button:SetScript("OnLeave", function()
    local tip = Compat.resolve("GameTooltip")
    if type(tip) == "table" and type(tip.Hide) == "function" then tip:Hide() end
  end)
end

local function build()
  local createFrame = Compat.resolve("CreateFrame")
  if type(createFrame) ~= "function" then return nil end
  frame = createFrame("Frame", "WFJVoicePanel", Compat.resolve("UIParent"), "BackdropTemplate")
  frame:SetSize(WIDTH, HEIGHT)
  frame:SetFrameStrata("HIGH")
  frame:SetClampedToScreen(true)
  if type(frame.SetBackdrop) == "function" then
    frame:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
      edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", edgeSize = 14,
      insets = { left = 3, right = 3, top = 3, bottom = 3 } })
    frame:SetBackdropColor(0, 0, 0, 0.85)
  end
  head = Head.build(frame, 4, -4, HEAD_SIZE)
  nameText = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  nameText:SetPoint("TOPLEFT", frame, "TOPLEFT", HEAD_SIZE + 10, -10)
  nameText:SetWidth(WIDTH - HEAD_SIZE - 18)
  nameText:SetJustifyH("LEFT")
  nameText:SetWordWrap(false)
  buttons = {}
  buttons.stop = createFrame("Button", nil, frame)
  buttons.stop:SetSize(BUTTON, BUTTON)
  buttons.stop:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", HEAD_SIZE + 10, 8)
  local square = buttons.stop:CreateTexture(nil, "ARTWORK")
  square:SetPoint("CENTER", buttons.stop, "CENTER", 0, 0)
  square:SetSize(10, 10)
  square:SetColorTexture(0.9, 0.9, 0.9, 1)
  buttons.stop:SetHighlightTexture(ICON_HIGHLIGHT, "ADD")
  buttons.stop:SetScript("OnClick", function() WFJ.VoicePlayer.stop() end)
  tooltip(buttons.stop, "voice.stop")
  buttons.skip = createFrame("Button", nil, frame)
  buttons.skip:SetSize(BUTTON + 4, BUTTON + 4)
  buttons.skip:SetPoint("LEFT", buttons.stop, "RIGHT", 6, 0)
  buttons.skip:SetNormalTexture(ICON_NEXT)
  buttons.skip:SetHighlightTexture(ICON_HIGHLIGHT, "ADD")
  buttons.skip:SetScript("OnClick", function() WFJ.VoicePlayer.skip() end)
  tooltip(buttons.skip, "voice.skip")
  waiting = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  waiting:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -10, 12)
  waiting:Hide()
  frame:Hide()
  return frame
end

local function cancelHide()
  if hideTimer then hideTimer:Cancel(); hideTimer = nil end
end

local function place(item)
  local window = item and WINDOWS[item.window] and Compat.resolve(item.window)
  if type(window) == "table" then
    frame:ClearAllPoints()
    frame:SetPoint("TOPLEFT", window, "TOPRIGHT", 4, 0)
    placed = true
  elseif not placed then
    frame:ClearAllPoints()
    frame:SetPoint("TOP", Compat.resolve("UIParent"), "TOP", 0, -140)
    placed = true
  end
end

local function linger()
  if hideTimer or not frame:IsShown() then return end
  local timer = Compat.resolve("C_Timer")
  if type(timer) ~= "table" or type(timer.NewTimer) ~= "function" then return frame:Hide() end
  hideTimer = timer.NewTimer(LINGER, function()
    hideTimer = nil
    frame:Hide()
  end)
end

-- State "voiceQueue" listener: the panel as the player's state says. `reason`: "stop" hides it at once.
function Panel.update(reason)
  local s = WFJ.VoicePlayer.state()
  if not frame then
    if not s.item then return end -- nothing ever played: no frame
    if not build() then return end
  end
  if not s.item then
    Head.setTalking(head, false)
    waiting:Hide()
    if reason == "stop" then
      cancelHide()
      frame:Hide()
    else
      linger()
    end
    return
  end
  cancelHide()
  if s.item ~= Panel.shownItem then
    Panel.shownItem = s.item
    place(s.item)
    nameText:SetText(s.item.name or "")
    Head.load(head, s.item)
  end
  Head.setTalking(head, s.playing)
  if s.waiting > 0 then
    waiting:SetText("+" .. s.waiting)
    waiting:Show()
  else
    waiting:Hide()
  end
  frame:Show()
end

-- For the specs and /fita debug: the frame's parts, read only.
function Panel.frame() return frame end
function Panel.head() return head end
function Panel.buttons() return buttons end
function Panel.nameText() return nameText and nameText:GetText() end
function Panel.waitingText() return waiting and waiting:GetText() end
function Panel.waitingShown() return waiting ~= nil and waiting:IsShown() end
function Panel.visible() return frame ~= nil and frame:IsShown() end

-- Called by Main after VoicePlayer. Builds nothing: the first line that plays does.
function Panel.init()
  if Panel.listening then return true end
  Panel.listening = true
  WFJ.State.on("voiceQueue", function(reason) pcall(Panel.update, reason) end)
  return true
end
