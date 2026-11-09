-- UI/MenuAttach.lua: how our show / reset reach a Menu element without tainting its click (ADR-031 amendment,
-- the raid-marker block). UI/Menus (every tagged and untagged menu) and UI/SpellBook (its settings menu)
-- attach through here.
-- An initializer of ours must never sit in an element's initializer array when the client front-inserts its own
-- template initializer there at layout (InitializeElementDescription: AddInitializer(initializer, 1) →
-- securecallfunction(tinsert, tbl, 1, value), blizzard_menu/menu.lua:1106–1114; securetypes.lua:117–126 "Element
-- move will taint execution"). The move reads our value, so the template initializer lands in the array tainted,
-- runs tainted, and its button:SetScript("OnClick", OnButtonClick) (menutemplates.lua:196) leaves the element's
-- click tainted: picking a raid marker then calls SetRaidTarget from tainted code and the client blocks it, naming
-- this addon [seen in game: ADDON_ACTION_FORBIDDEN SetRaidTarget(); gone with the menus off, still there
-- with our initializer's body emptied].
-- So an element that does something when clicked (a responder) or opens a submenu gets no initializer of ours: it is
-- shown from a post-hook of MenuTemplates.RecurseSetupFontString, which the client's button final initializer calls
-- on the element after every initializer and before the menu is measured (menutemplates.lua:109–110;
-- menu.lua:1016–1066, PerformLayout :1302). A post-hook's taint never reaches the client's call. An inert element (a
-- title, a label: no responder, no submenu) keeps the initializer: its click runs nothing, and a title has no final
-- initializer to hook (menutemplates.lua:289–296). Resetters are only ever appended (menu.lua:455), never moved.
local _, WFJ = ...
local MenuAttach = {}
WFJ.MenuAttach = MenuAttach

local hooked = false
local viaHook = setmetatable({}, { __mode = "k" }) -- element description → show(frame), for the post-hook

-- → true when clicking `desc` can never run anything (no responder, no submenu).
local function inert(desc)
  if type(desc.HasResponder) ~= "function" or type(desc.HasElements) ~= "function" then return false end
  local ok, responds = pcall(desc.HasResponder, desc)
  if not ok or responds then return false end
  local okE, hasElements = pcall(desc.HasElements, desc)
  return okE and not hasElements
end
MenuAttach.inert = inert

local function stringWidth(fs)
  local f = type(fs) == "table" and (fs.GetUnboundedStringWidth or fs.GetStringWidth) or nil
  if type(f) ~= "function" then return nil end
  local ok, w = pcall(f, fs)
  return ok and type(w) == "number" and w or nil
end

-- The post-hook: one element frame (or one of its children, which carry no description). → show's count | 0
function MenuAttach.onFinalInit(frame)
  if type(frame) ~= "table" or type(frame.GetElementDescription) ~= "function" then return 0 end
  local ok, desc = pcall(frame.GetElementDescription, frame)
  local show = ok and desc ~= nil and viaHook[desc] or nil
  if not show then return 0 end
  local fs = frame.fontString
  local before = stringWidth(fs)
  local n = show(frame) or 0
  -- the frame was sized to the English before this hook; the menu takes its widest element (MeasureFrameExtents)
  local after = stringWidth(fs)
  if before and after and after > before and type(frame.GetWidth) == "function"
      and type(frame.SetWidth) == "function" then
    pcall(function() frame:SetWidth(frame:GetWidth() + (after - before)) end)
  end
  return n
end

-- Post-hooks MenuTemplates.RecurseSetupFontString once. → true when hooked
function MenuAttach.hook()
  if hooked then return true end
  local templates = WFJ.Compat.resolve("MenuTemplates")
  if type(templates) ~= "table" or type(templates.RecurseSetupFontString) ~= "function" then return false end
  hooked = true
  hooksecurefunc(templates, "RecurseSetupFontString", MenuAttach.onFinalInit)
  return true
end

-- Gives one element description our `show(frame)` and `reset(frame)` without ever tainting its click.
-- → true when the element will be shown (false: no hook point; it stays English and its click stays clean)
function MenuAttach.attach(desc, show, reset)
  if type(desc) ~= "table" then return false end
  if reset and type(desc.AddResetter) == "function" then desc:AddResetter(reset) end
  if inert(desc) and type(desc.AddInitializer) == "function" then
    desc:AddInitializer(show)
    return true
  end
  if not MenuAttach.hook() then return false end
  viaHook[desc] = show
  return true
end
