-- ADR-101: an Italian line is aligned on its numbers only; every Italian word is Latin, so no name check.
local H = require("tests.lua.spec.helpers")

describe("Align.check on Italian (ADR-101)", function()
  local A
  setup(function()
    local ns = {}
    H.loadPure("Core/Align.lua", "OldpZ_ForeverITA", ns)
    A = ns.Align
  end)

  it("Italian words are not names the English must hold", function()
    local ok, text = A.check("Porta 8 Pelli di Lupo a Roccavento.", { "Bring 8 Wolf Pelts to Stormwind." })
    assert.is_true(ok)
    assert.are.equal("Porta 8 Pelli di Lupo a Roccavento.", text)
  end)

  it("a changed number is still refused", function()
    assert.is_false(A.check("Porta 9 Pelli di Lupo a Roccavento.", { "Bring 8 Wolf Pelts to Stormwind." }))
  end)
end)
