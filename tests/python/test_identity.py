"""The shipped addon carries no identity of the upstream project (WoW Forever Japanese)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "addon"
FORBIDDEN = ("WoWForeverJapanese", "WFJ_", "zyaga/wow-forever-japanese", "1717928")


def test_no_upstream_identity_in_addon():
    hits = []
    for path in sorted(ADDON.rglob("*")):
        if not path.is_file() or path.suffix not in (".lua", ".toc", ".xml"):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for word in FORBIDDEN:
                if word in line:
                    hits.append(f"{path.relative_to(ROOT)}:{n}: {word}")
    assert hits == []


def test_addon_folder_and_toc():
    assert (ADDON / "OldpZ_ForeverITA" / "OldpZ_ForeverITA.toc").is_file()
    assert not (ADDON / "WoWForeverJapanese").exists()
