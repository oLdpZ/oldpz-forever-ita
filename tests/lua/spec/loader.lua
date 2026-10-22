-- Loads the addon exactly as the client does: TOC order, one chunk per file, vararg = (ADDON, WFJ).
local H = require("tests.lua.spec.helpers")
local Loader = {}

function Loader.tocFiles(tocPath)
  local files = {}
  local f = assert(io.open(tocPath))
  for line in f:lines() do
    local l = line:gsub("^\239\187\191", ""):gsub("^%s+", ""):gsub("%s+$", "")
    if l ~= "" and not l:match("^##") and not l:match("^#") then
      files[#files + 1] = (l:gsub("\\", "/"))
    end
  end
  f:close()
  return files
end

-- `opts.data`: a folder holding generated shards and their `files.txt` (tests/fixtures/it-store/addon, H.FIXTURE_DATA).
-- Its files are loaded in place of the TOC's generated block (every `Data/` line), so a spec can run on shipped
-- lines while the committed store holds none.
function Loader.load(addonName, opts)
  addonName = addonName or "OldpZ_ForeverITA"
  local WFJ = {}
  local toc = H.ADDON_DIR .. "/" .. addonName .. ".toc"
  local data = opts and opts.data
  local done = false
  for _, rel in ipairs(Loader.tocFiles(toc)) do
    if data and rel:find("^Data/") then
      if not done then
        done = true
        for line in io.lines(data .. "/files.txt") do
          if line ~= "" then
            local chunk = assert(loadfile(data .. "/" .. line))
            chunk(addonName, WFJ)
          end
        end
      end
    else
      H.loadChunk(rel, addonName, WFJ)
    end
  end
  return WFJ, toc
end

return Loader
