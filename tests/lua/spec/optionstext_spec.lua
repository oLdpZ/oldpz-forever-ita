local H = require("tests.lua.spec.helpers")

describe("UI/OptionsText: every page string in both languages", function()
  local Text
  setup(function() Text = H.loadChunks({ "UI/OptionsText.lua" }).OptionsText end)

  local function placeholders(s)
    local _, n = s:gsub("%%s", "")
    return n
  end

  it("has non-empty English and Italian with the same number of %s for every key", function()
    local n = 0
    for key, t in pairs(Text.T) do
      n = n + 1
      assert.is_true(type(t.en) == "string" and #t.en > 0, key .. " en")
      assert.is_true(type(t.it) == "string" and #t.it > 0, key .. " it")
      assert.are.equal(placeholders(t.en), placeholders(t.it), key)
      -- Italian as the pipeline's `language.is_italian` reads it: a Latin letter, and not the English itself;
      -- page.main is the addon's name, written the same in both languages
      assert.is_truthy(t.it:find("%a"), key .. ": the Italian has no letter in it")
      if key ~= "page.main" then assert.are_not.equal(t.en, t.it, key .. ": the Italian is the English") end
      assert.is_nil(t.it:find("[\227-\233\239]"), key .. ": CJK in the Italian")
    end
    assert.is_true(n > 30)
  end)

  it("no English line carries CJK (it would switch the English to the bundled face and wrap)", function()
    -- the About page's marker line once held a CJK marker in its English and ran into the next row
    -- page.main is the addon's name, written the same in both languages (and so in the same face) on a wide header
    for key, t in pairs(Text.T) do
      if key ~= "page.main" then assert.is_nil(t.en:find("[\227-\233\239]"), key) end
    end
  end)

  it("formats both languages and refuses a missing key", function()
    local en, tr = Text.get("warn.takeover", "Q", "Action Button 5", "Q")
    assert.are.equal('Q is used for "Action Button 5". While this addon is loaded, Q shows English instead.', en)
    assert.is_truthy(tr:find('"Action Button 5"', 1, true))
    assert.has_error(function() Text.get("no.such.key") end)
  end)
end)

describe("UI/OptionsText.SLASH names every command", function()
  it("lists every top-level verb and every debug sub-verb", function()
    local Text = H.loadChunks({ "UI/OptionsText.lua" }).OptionsText
    local all = table.concat(Text.SLASH, "\n")
    for _, verb in ipairs({ "on", "off", "toggle", "config", "debug", "togglekey", "collector",
        "version", "modifier", "area", "marker", "fix", "voce" }) do
      assert.is_truthy(all:find("/fita " .. verb, 1, true) or all:find("| " .. verb, 1, true), verb)
    end
    local debug = {}
    for list in all:gmatch("/fita debug %[(.-)%]\n") do debug[#debug + 1] = list end
    for list in all:gmatch("/fita debug %[(.-)%]$") do debug[#debug + 1] = list end
    local subs = table.concat(debug, " | ")
    for _, sub in ipairs({ "hash", "quest", "item", "spell", "gossip", "book", "objective", "fonts", "ui", "scan" }) do
      assert.is_truthy(subs:find(sub, 1, true), sub)
    end
  end)

  it("says the voice command needs a voice pack: without one it has nothing to stop", function()
    local Text = H.loadChunks({ "UI/OptionsText.lua" }).OptionsText
    for _, line in ipairs(Text.SLASH) do
      if line:find("/fita voce", 1, true) then assert.is_truthy(line:find("with a voice pack", 1, true), line) end
    end
  end)
end)
