-- UI/ZoneNames.lua: zone names on the screen (surface "zonenames", area "namezone"): the big text on entering a zone,
-- the minimap's line and the world map's hover label. Their writers run on the client's own passes, so they are
-- followed from UI/TextWatch, which runs after those passes have ended (ADR-058).
local _, WFJ = ...
local ZoneNames = {}
WFJ.ZoneNames = ZoneNames

local Compat = WFJ.Compat
local SURFACE = "zonenames"
local WIDGETS = { "ZoneTextString", "SubZoneTextString", "MinimapZoneText" }

local function watch(name, fs)
  if type(fs) ~= "table" then return false end
  local function show() WFJ.NameText.show(SURFACE, name, fs, "namezone") end
  WFJ.TextWatch.add(fs, show)
  show()
  return true
end

-- The map's AreaLabelDataProvider keeps its frame in `Label`, created on the map [verified:
-- blizzard_sharedmapdataproviders/arealabeldataprovider.lua:7–8, 211].
function ZoneNames.mapLabel()
  local map = Compat.resolve("WorldMapFrame")
  local providers = type(map) == "table" and map.dataProviders or nil
  if type(providers) ~= "table" then return nil end
  for provider in pairs(providers) do
    local label = type(provider) == "table" and provider.Label or nil
    if type(label) == "table" and type(label.Name) == "table" then return label.Name end
  end
  return nil
end

local hooked = false

-- Called by Main after Compat.init. → false when already hooked
function ZoneNames.init()
  if hooked then return false end
  hooked = true
  for _, name in ipairs(WIDGETS) do watch(name, Compat.resolve(name)) end
  watch("mapLabel", ZoneNames.mapLabel())
  return true
end
