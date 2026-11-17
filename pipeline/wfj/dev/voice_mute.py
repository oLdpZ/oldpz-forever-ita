"""pipeline/voice_mute.tsv: the game's own English voice of NPC lines in chat, silenced while ours plays.

python -m wfj.dev.voice_mute --vmangos FILE --soundkit SoundKitEntry.csv [--out pipeline/voice_mute.tsv]

The server sends a few lines in chat (mostly boss yells) with a sound (`broadcast_text.sound_id`, VMaNGOS);
that id is a client SoundKit, whose files are the SoundKitEntry rows (`SoundKitID` → `FileDataID`). Each row
of the table: the line's gossip key (the hash of its English, as UI/Speech finds it) and its file ids. A
sound kit the client table lacks gives no row. The voice packs read the table (`wfj voice pack`).
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from wfj.core import voice
from wfj.io import vmangos


def rows(sounds: Mapping[str, int], kits: Mapping[int, Sequence[int]]) -> dict[str, list[int]]:
    """{gossip key: file ids} for the English lines whose sound kit the client knows."""
    out: dict[str, list[int]] = {}
    for text, kit in sounds.items():
        files = kits.get(kit)
        if files:
            out[voice.gossip_id(text)] = sorted(set(files))
    return out


def read_kits(path: Path) -> dict[int, list[int]]:
    """SoundKitEntry.csv → {sound kit id: file data ids}."""
    out: dict[int, list[int]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(int(r["SoundKitID"]), []).append(int(r["FileDataID"]))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m wfj.dev.voice_mute")
    p.add_argument("--vmangos", required=True, type=Path)
    p.add_argument("--soundkit", required=True, type=Path, help="the client's SoundKitEntry.csv")
    p.add_argument("--out", type=Path, default=Path("voice_mute.tsv"))
    a = p.parse_args(argv)
    table = rows(vmangos.read_speech_sounds(a.vmangos), read_kits(a.soundkit))
    text = "key\tfiles\n" + "".join(f"{k}\t{','.join(map(str, v))}\n" for k, v in sorted(table.items()))
    a.out.write_text(text, encoding="utf-8")
    print(f"voice mute: {len(table)} lines in chat with an English voice → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
