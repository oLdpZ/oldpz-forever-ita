-- UI/GameMenu.lua: the Esc game menu's buttons (surface "gamemenu", area "ui").
-- GameMenuFrame:InitButtons() rebuilds the menu from a button pool on every show (Reset → AddButton per entry →
-- AddCloseButton) [verified: classic_era Blizzard_GameMenu/Shared/GameMenuFrame.lua:18–29, 62–161;
-- Blizzard_SharedXML/Shared/Frame/MainMenuFrameTemplates.lua:24–70]. It is post-hooked on the frame (hooksecurefunc
-- on the frame table: the method is looked up on self at call time), so our write follows the client's. Pool buttons
-- are reused, so the surface is forgotten first and every active button is read again; MainMenuFrameButtonTemplate
-- is a fixed 144×21 button and AddButton uses SetText, not SetTextToFit [verified: Classic/Frame/
-- MainMenuFrameTemplates.xml:11–16], so the Japanese never resizes it. AddButton re-sets OnEnter / OnLeave on each
-- reuse, which drops the font re-apply hooks for those two scripts; they are installed again (ButtonText.rehook).
-- The title plate (Header.Text, set once from MAINMENU_BUTTON at load and sized then) is shown too; its background is a
-- fixed 256×64 texture, so a shorter or slightly longer title stays on the plate [verified: Classic/Frame/
-- MainMenuFrameTemplates.xml:45–50, Classic/Dialog/DialogTemplates.xml:11–36, Shared/Dialog/DialogTemplates.lua:4–22].
-- Release on GameMenuFrame's OnHide.
-- Forever: the same frame, pool and InitButtons [verified: Forever blizzard_gamemenu/shared/
-- gamemenuframe.lua:153–158, 160–271; blizzard_sharedxml/shared/frame/mainmenuframetemplates.lua:14, 25–67], with
-- words of its own: GAMEMENU_EXTERNALEVENT (lua:178), GAME_MENU_SHOW_REWARDS (lua:222), and LOG_OUT from
-- the mainline GetLogoutText (lua:281–284) where the Classic override returned LOGOUT. The buttons are matched by their
-- English like every other entry, so only the dictionary had to learn them. The mainline button template is a
-- 200×36 three-slice button (blizzard_sharedxml/mainline/frame/mainmenuframetemplates.xml:11–16).
-- When the words are written: after the frame's Layout, not after InitButtons. Other addons find the menu's
-- buttons by their English in a post-hook of GameMenuFrame.Layout (ACP: `button:GetText() == ADDONS`, then its own
-- OnClick), and every InitButtons is followed by a Layout: OnShow calls it right after InitButtons, and AddButton's
-- MarkDirty runs it on the next OnUpdate after an event rebuild [verified: Forever blizzard_gamemenu/shared/
-- gamemenuframe.lua:61–77, 96–102; blizzard_sharedxml/shared/frame/mainmenuframetemplates.lua:24–65;
-- blizzard_sharedxml/layoutframe.lua:12–16, 79–89]. Our Layout hook is installed at the first show, after those
-- addons hooked at login (ACP: PLAYER_ENTERING_WORLD), so it runs after theirs and they still read the English.
-- The OnShow hook covers that first show (its Layout has run already) and a frame with no Layout.
local _, WFJ = ...
local GameMenu = {}
WFJ.GameMenu = GameMenu

local SURFACE = "gamemenu"
local Compat = WFJ.Compat
GameMenu.SURFACE = SURFACE

-- hooksecurefunc target: runs after InitButtons wrote the buttons. → the number of dictionary words found.
function GameMenu.onInit(frame)
  frame = frame or Compat.get(SURFACE, "frame")
  WFJ.Render.forget(SURFACE)
  local pool = type(frame) == "table" and frame.buttonPool or nil
  if type(pool) ~= "table" or type(pool.EnumerateActive) ~= "function" then return 0 end
  local list = {}
  for button in pool:EnumerateActive() do list[#list + 1] = button end
  table.sort(list, function(a, b) return (a.layoutIndex or 0) < (b.layoutIndex or 0) end)
  local items = {}
  if type(frame.Header) == "table" and type(frame.Header.Text) == "table" then
    items[1] = { "ui.header", frame.Header.Text }
  end
  for i, button in ipairs(list) do
    if WFJ.ButtonText.known(button) then
      WFJ.ButtonText.rehook(button) -- a reused button: AddButton replaced OnEnter / OnLeave
    else
      WFJ.ButtonText.of(button) -- first sight: every state script hooked once
    end
    items[#items + 1] = { "ui." .. (button.layoutIndex or i), button }
  end
  return WFJ.Labels.showAll(SURFACE, items)
end

function GameMenu.release()
  return WFJ.Render.release(SURFACE)
end

local hooked = false
GameMenu.layoutHooked = false

-- OnShow post-hook: the client's OnShow ran InitButtons and Layout (and the hooks other addons put on Layout).
-- Installs the Layout hook once, then writes this show's words. → the number of dictionary words found.
function GameMenu.onShow(frame)
  if not GameMenu.layoutHooked and type(frame) == "table" and type(frame.Layout) == "function" then
    GameMenu.layoutHooked = true
    hooksecurefunc(frame, "Layout", GameMenu.onInit)
  end
  return GameMenu.onInit(frame)
end

-- Called by Main after Compat.init.
function GameMenu.init()
  Compat.declare(SURFACE, "frame", { "GameMenuFrame" })
  if hooked then return false end
  local frame = Compat.get(SURFACE, "frame")
  if type(frame) ~= "table" or type(frame.InitButtons) ~= "function" or type(frame.HookScript) ~= "function" then
    return false
  end
  hooked = true
  frame:HookScript("OnShow", GameMenu.onShow)
  frame:HookScript("OnHide", GameMenu.release)
  return true
end
