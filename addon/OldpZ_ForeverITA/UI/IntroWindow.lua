-- UI/IntroWindow.lua: the window a first install shows once, at its first login (docs/systems/settings.md).
-- Core/Intro decides when; Main hands it IntroWindow.request, which opens it. It is the one addon window that shows
-- both languages at once, an Italian block above an English one: the player has not learned the reveal key yet, so
-- a one-language window could be unreadable to them. The reveal key and the translation switch change nothing here.
-- Lines: what the addon does, the reveal key (named as set) and the minimap button. Only the addon's own copy
-- (UI/OptionsText), never game text.
local _, WFJ = ...
local IntroWindow = {}
WFJ.IntroWindow = IntroWindow

local W, Text = WFJ.OptionsWidgets, WFJ.OptionsText
local WIDTH, LEFT = 520, 26
local TEXT_WIDTH = WIDTH - 2 * LEFT
-- the inset panel moved up under the title bar and down to the bottom edge, as in UI/CollectorReminder
local INSET_TOP, INSET_BOTTOM = 24, 4
local TOP, BOTTOM, PAD = INSET_TOP + 4, INSET_BOTTOM + 4, 12
local LINE, BLOCK = 7, 14 -- between lines in a block; above and below the rule between the two blocks
local HEAD = 10 -- under a block's opening line
local KEY = "|cffffd200%s|r" -- the reveal key's name, in the gold the client uses for key names
local BULLETS = { it = "• ", en = "• " }
local BUTTON = 22

IntroWindow.frame = nil
IntroWindow.closedByPlayer = false -- Close, Esc or any hide outside a cinematic: it stays closed
IntroWindow.waiting = false -- a cinematic is playing: open when it ends
local watcher -- the frame that hears the cinematic events, made by the first request

-- Two font strings per line, not W.label: a W.label re-shows one language whenever the reveal key flips.
local function line(p)
  local r = {}
  r.it = p:CreateFontString(nil, "ARTWORK", "GameFontHighlight")
  r.en = p:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
  for _, fs in ipairs({ r.it, r.en }) do
    fs:SetWidth(TEXT_WIDTH)
    fs:SetJustifyH("LEFT")
  end
  r.en:SetTextColor(W.IT_COLOR[1], W.IT_COLOR[2], W.IT_COLOR[3])
  return r
end

-- A point's two texts, each with its block's bullet; the opening line has none and is a size up.
local function fill(r, en, it, lead)
  if lead then
    W.put(r.it, it, 13)
    W.put(r.en, en, 12)
  else
    W.put(r.it, BULLETS.it .. it, 12)
    W.put(r.en, BULLETS.en .. en, 11)
  end
end

-- The wrapped height of a line [likely: FontString:GetStringHeight with a set width; in-game check: the intro window
-- checklist in docs/testing/strategy.md]; the specs' stub has none.
local function height(fs)
  return math.max(14, fs.GetStringHeight and math.ceil(fs:GetStringHeight()) or 0)
end

local function build()
  local f = W.toolWindow("OFI_Intro", WIDTH, 300)
  -- where the client opens its own popups, clear of the character [verified: forever-ui-1.60.1.70425
  -- blizzard_staticpopup_game/gamedialog.xml:350, TOP 0,-135]; it grows down
  f:ClearAllPoints()
  f:SetPoint("TOP", 0, -135)
  if f.Inset then
    f.Inset:ClearAllPoints()
    f.Inset:SetPoint("TOPLEFT", 4, -INSET_TOP)
    f.Inset:SetPoint("BOTTOMRIGHT", -6, INSET_BOTTOM)
  end
  local p = CreateFrame("Frame", nil, f)
  p:SetPoint("TOPLEFT", 0, -TOP)
  p:SetPoint("TOPRIGHT", 0, -TOP)
  p:SetHeight(1)
  f.page = p
  f.lead, f.hold, f.minimap = line(p), line(p), line(p)
  f.lines = { f.lead, f.hold, f.minimap }
  W.put(f.title, WFJ.Options.TITLE, 13)
  local en, it = Text.get("intro.lead")
  fill(f.lead, en, it, true)
  for _, fs in ipairs({ f.lead.it, f.lead.en }) do fs:SetTextColor(W.GOLD[1], W.GOLD[2], W.GOLD[3]) end
  fill(f.minimap, Text.get("intro.minimap"))
  -- the gold rule between the blocks, as under the settings pages' section titles
  f.rule = p:CreateTexture(nil, "ARTWORK")
  f.rule:SetColorTexture(W.GOLD[1], W.GOLD[2], W.GOLD[3], 0.45)
  f.rule:SetSize(TEXT_WIDTH, 1)
  en, it = Text.get("intro.close")
  -- one caption with both words, so W.pick has nothing to switch
  f.close = W.button(p, it .. " / " .. en, nil, 140, function() IntroWindow.close() end)
  f:HookScript("OnHide", function() IntroWindow.hidden() end)
  IntroWindow.frame = f
  return f
end

-- Runs fn after `seconds` (1 by default), or now where the client timer is missing (the specs).
local function later(fn, seconds)
  if type(C_Timer) == "table" and type(C_Timer.After) == "function" then C_Timer.After(seconds or 1, fn) else fn() end
end

-- The Japanese lines as one block, a gold rule, their English as another; then the button.
-- Each line hangs from the one above it, so the gaps never depend on a measured height; only the window's does.
local function layout(f)
  local rows = f.lines
  local prev, used
  local function chain(region, gap, x)
    region:ClearAllPoints()
    region:SetPoint("TOPLEFT", prev, "BOTTOMLEFT", x or 0, -gap)
    used = used + gap + (region.GetObjectType and region:GetObjectType() == "FontString" and height(region) or 0)
    prev = region
  end
  f.lead.it:ClearAllPoints()
  f.lead.it:SetPoint("TOPLEFT", f.page, "TOPLEFT", LEFT, -PAD)
  prev, used = f.lead.it, height(f.lead.it)
  for i = 2, #rows do chain(rows[i].it, i == 2 and HEAD or LINE) end
  chain(f.rule, BLOCK)
  chain(f.lead.en, BLOCK)
  for i = 2, #rows do chain(rows[i].en, i == 2 and HEAD or LINE) end
  f.close:ClearAllPoints()
  f.close:SetPoint("BOTTOM", f, "BOTTOM", 0, BOTTOM + PAD)
  f:SetHeight(TOP + PAD + used + BLOCK + BUTTON + PAD + BOTTOM)
end

local function refused(f)
  for _, r in ipairs(f.lines) do
    if WFJ.Font.isPending(r.it) or WFJ.Font.isPending(r.en) then return true end
  end
  return false
end

-- A first install's first login is a fresh launch, when the client refuses the bundled face until its file loads
-- (UI/Font, Main's font retry): the lines were measured in another face and wrap differently once it lands. Checks
-- once a second and lays the window out again when Font's retry has applied it, for as long as Main keeps retrying.
local function relayoutWhenFonts(f)
  if f.fontTicker or not refused(f) or type(C_Timer) ~= "table" then return end
  local tries = 0
  f.fontTicker = C_Timer.NewTicker(1, function(ticker)
    tries = tries + 1
    local waiting = refused(f)
    if not waiting and f:IsShown() then layout(f) end
    if not waiting or tries >= 600 then
      ticker:Cancel()
      f.fontTicker = nil
    end
  end)
end

-- Names the reveal key as it is set now and shows the window. → the frame
function IntroWindow.open()
  local f = IntroWindow.frame or build()
  fill(f.hold, Text.get("intro.hold", KEY:format(WFJ.Options.keyName())))
  layout(f)
  -- a FontString given new text may report its old height until the client has drawn it once [likely; in-game
  -- check: the intro window checklist in docs/testing/strategy.md]: the height is taken again on the next frame
  later(function() if f:IsShown() then layout(f) end end, 0)
  relayoutWhenFonts(f)
  f:Show()
  return f
end

function IntroWindow.close()
  if IntroWindow.frame then IntroWindow.frame:Hide() end
end

-- ── When it opens ───────────────────────────────────────────────────────────
-- The client closes every window in UISpecialFrames (which is how Esc reaches this one) on its own
-- PLAYER_ENTERING_WORLD [verified: forever-ui-1.60.1.70425 blizzard_game/shared/eventimplementation.lua:306], when a
-- cinematic starts, such as a new character's race intro (CinematicFrame is a full-area panel, so showing it closes
-- the other windows [verified: blizzard_framexml/shared/cinematicframe.lua:89,
-- blizzard_uiparentpanelmanager/shared/uiparentpanelmanager.lua:281]), and again when the interface comes back after
-- it [verified: blizzard_game/shared/game.lua:91]. So the window opens a moment after it is asked for, waits out a
-- cinematic, and comes back after one that hid it. A hide outside a cinematic is the player's.

local function inCinematic()
  local playing = WFJ.Compat.resolve("InCinematic")
  return type(playing) == "function" and playing() == true
end

local function openNow()
  if IntroWindow.closedByPlayer then return end
  if inCinematic() then
    IntroWindow.waiting = true
    return
  end
  -- cleared only now, not at CINEMATIC_STOP: a hide's check a second later must still see a cinematic the player
  -- skipped within that second
  IntroWindow.waiting = false
  -- later than the login step, so the load guard is called again here: a failure is recorded as `intro`
  if WFJ.step then WFJ.step("intro", IntroWindow.open) else IntroWindow.open() end
end

local function onEvent(_, event)
  if IntroWindow.closedByPlayer then return end
  if event == "CINEMATIC_START" then
    IntroWindow.waiting = true
  elseif IntroWindow.waiting then
    later(openNow)
  end
end

-- Core/Intro's show: opens it a moment later, through any cinematic.
function IntroWindow.request()
  if not watcher then
    watcher = CreateFrame("Frame")
    watcher:RegisterEvent("CINEMATIC_START")
    watcher:RegisterEvent("CINEMATIC_STOP")
    watcher:SetScript("OnEvent", onEvent)
  end
  later(openNow)
end

-- A hide during a cinematic is the client's sweep. The cinematic's start may reach this addon after the sweep in the
-- same event, so the call is made a moment later, once CINEMATIC_START has been heard.
function IntroWindow.hidden()
  later(function()
    if IntroWindow.waiting or inCinematic() then return end
    IntroWindow.closedByPlayer = true
    if watcher then
      watcher:UnregisterEvent("CINEMATIC_START")
      watcher:UnregisterEvent("CINEMATIC_STOP")
    end
  end)
end
