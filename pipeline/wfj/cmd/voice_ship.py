"""wfj voice pack: the voice addon OldpZ_ForeverITA_Voce, built from the audio store.

  pack --scope S --store DIR [--out build/voice-pack] [--version V] [--config F]
      Writes OUT/OldpZ_ForeverITA_Voce/ (TOC, Register.lua, LEGGIMI.txt, Sound/*.mp3) and, beside OUT, the zip
      OldpZ_ForeverITA_Voce-<version>.zip holding that one folder. Ships only the takes in step with the
      Italian the addon ships now (the recorded fingerprint is the take's current one) and whose file in the
      store is the recorded one; the others are left out and listed, with counts. Fails, writing nothing,
      when the audio comes to more than 420 MB. --version defaults to today's date.

The store is --store, else $VOICE_ROOT.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys
import zipfile
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from wfj.cmd import voice_make
from wfj.cmd.voice import read_rows, scope_path
from wfj.cmd.voice_cast import CONFIG, VOICES, in_scope, load_config
from wfj.core import voice
from wfj.emit import voice_pack
from wfj.emit.voice_pack import FOLDER, Entry
from wfj.paths import data_root

LIMIT = 420 * 1024 * 1024  # bytes of audio: the pack's ceiling
STEM = re.compile(r"^[A-Za-z0-9_-]+$")  # what the addon accepts of a file name (`^[%w%-_]+%.mp3$`)


def interface_of(root: Path) -> str:
    """The main addon's `## Interface:`: the pack is loaded by the same client."""
    toc = root.parent / "addon" / "OldpZ_ForeverITA" / "OldpZ_ForeverITA.toc"
    for line in toc.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Interface:"):
            return line.split(":", 1)[1].strip()
    raise ValueError(f"{toc}: no ## Interface line")


def select(
    root: Path, cfg: Mapping[str, Any], scope: str, store: Path
) -> tuple[list[voice_make.Take], list[tuple[str, str]], list[tuple[str, str, str]]]:
    """(takes to ship, [(stem, why left out)], the survey's silent lines). A take ships when the audio record
    holds its current fingerprint and the store holds exactly the recorded file."""
    sv = voice_make.survey(root, cfg, scope)
    audio, blocked = voice_make.audio_record(root), voice_make.read_blocked(store)
    ship: list[voice_make.Take] = []
    left: list[tuple[str, str]] = []
    for t in sv.takes:
        stem, rec = t.job.stem, audio.get(t.job.stem)
        path = voice_make.mp3_file(store, stem)
        if blocked.get(stem, {}).get("fingerprint") == t.fingerprint:
            left.append((stem, "blocked"))
        elif rec is None:
            left.append((stem, "missing"))
        elif rec.get("fingerprint") != t.fingerprint:
            left.append((stem, "stale"))
        elif (not path.is_file() or path.stat().st_size != int(rec["bytes"])
              or voice_make.file_sha(path) != rec["sha256"]):
            left.append((stem, "damaged"))
        else:
            ship.append(t)
    return ship, left, sv.silent


def entries(
    ship: Sequence[voice_make.Take], audio: Mapping[str, Mapping[str, Any]]
) -> tuple[dict[str, Entry], list[tuple[str, str]]]:
    """({pack key: Entry}, [(stem, why left out)]). A key ships when its main voice's male take does: a female
    take, or another voice's take, without the take it hangs on has no line to go in."""
    males = {t.job.stem: t for t in ship if t.job.sex == "m"}

    def secs(stem: str) -> float:
        return float(audio[stem]["seconds"])

    out = {
        t.job.key: Entry(f"{stem}.mp3", voice.it_hash(t.it), secs(stem))
        for stem, t in males.items() if stem == t.job.key
    }
    left: list[tuple[str, str]] = []
    for t in sorted(ship, key=lambda t: t.job.stem):
        j = t.job
        e = out.get(j.key)
        if j.sex == "f":
            base = j.stem.removesuffix("_f")
            if e is None or base not in males:
                left.append((j.stem, "no male take"))
            elif base == j.key:
                e.female = (f"{j.stem}.mp3", secs(j.stem))
            else:
                f, s, _ = e.voices[j.voice]
                e.voices[j.voice] = (f, s, (f"{j.stem}.mp3", secs(j.stem)))
        elif j.stem != j.key:
            if e is None:
                left.append((j.stem, "no take of the main voice"))
            else:
                e.voices[j.voice] = (f"{j.stem}.mp3", secs(j.stem), None)
    return out, left


def creature_voices(
    root: Path, scope: str, lines: Mapping[str, Entry]
) -> dict[int, str | tuple[str, str]]:
    """{creature id: voice id, or (male, female)} for every creature that says a line with other voices."""
    quests, books = voice.read_scope_file(scope_path(root, scope))
    cast = {int(r["creature"]): r for r in read_rows(root / "voice" / VOICES)}
    out: dict[int, str | tuple[str, str]] = {}
    for row in in_scope(read_rows(root / "voice" / "speakers.jsonl"), quests, books):
        entry = lines.get(row["key"])
        if entry is None or not entry.voices:
            continue
        for c in (row["speaker"], *row.get("others", ())):
            if isinstance(c, int) and c in cast:
                r = cast[c]
                out[c] = (r["voice"], r["female"]) if r.get("female") else r["voice"]
    return out


def files_of(lines: Mapping[str, Entry]) -> list[str]:
    """Every file name the lines point at, sorted."""
    out: list[str] = []
    for e in lines.values():
        out.append(e.file)
        if e.female:
            out.append(e.female[0])
        for f, _, fem in e.voices.values():
            out += [f, *([fem[0]] if fem else [])]
    return sorted(out)


def _place(src: Path, dest: Path) -> None:
    """A hard link where the store and the output share a disk, else a copy."""
    try:
        os.link(src, dest)
    except OSError:
        shutil.copyfile(src, dest)


def check_zip(path: Path, files: Sequence[str]) -> list[str]:
    """What is wrong with the zip: anything but the TOC, Register.lua, LEGGIMI.txt and the listed Sound files,
    or one of those missing."""
    want = {f"{FOLDER}/{n}" for n in (f"{FOLDER}.toc", "Register.lua", "LEGGIMI.txt")}
    want |= {f"{FOLDER}/Sound/{f}" for f in files}
    with zipfile.ZipFile(path) as z:
        have = {n for n in z.namelist() if not n.endswith("/")}
    return [f"{path.name}: contiene {n}, che Register.lua non elenca" for n in sorted(have - want)] + [
        f"{path.name}: manca {n}" for n in sorted(want - have)
    ]


def zip_folder(base: Path, dest: Path) -> None:
    """FOLDER under `base`, at the top of the zip. MP3s are stored as they are (already compressed)."""
    with zipfile.ZipFile(dest, "w") as z:
        for f in sorted((base / FOLDER).rglob("*")):
            if f.is_file():
                kind = zipfile.ZIP_STORED if f.suffix == ".mp3" else zipfile.ZIP_DEFLATED
                z.write(f, f.relative_to(base).as_posix(), compress_type=kind)


def build(root: Path, cfg: Mapping[str, Any], scope: str, store: Path, out: Path, version: str) -> int:
    ship, left, silent = select(root, cfg, scope, store)
    lines, orphans = entries(ship, voice_make.audio_record(root))
    left += orphans
    files = files_of(lines)
    for f in files:
        if not STEM.match(f.removesuffix(".mp3")):
            raise ValueError(f"file name the addon would refuse: {f}")
    total = sum(voice_make.mp3_file(store, f.removesuffix(".mp3")).stat().st_size for f in files)
    for kind, n in sorted(Counter(k for _, k in left).items()):
        print(f"voice pack: left out, {kind}: {n}")
    for stem, kind in sorted(left):
        print(f"voice pack: left out: {stem}: {kind}")
    for kind, n in sorted(Counter(k for _, k, _ in silent).items()):
        print(f"voice pack: silent, {kind}: {n}")
    print(f"voice pack: {len(lines)} lines, {len(files)} files, {total / 1024**2:.1f} MB")
    if total > LIMIT:
        print(f"voice pack: {total / 1024**2:.1f} MB is over the {LIMIT // 1024**2} MB limit: nothing"
              " written", file=sys.stderr)
        return 1
    dest = out / FOLDER
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "Sound").mkdir(parents=True)
    (dest / f"{FOLDER}.toc").write_text(voice_pack.toc_text(interface_of(root), version), encoding="utf-8")
    (dest / "Register.lua").write_text(
        voice_pack.register_text(lines, creature_voices(root, scope, lines)), encoding="utf-8"
    )
    (dest / "LEGGIMI.txt").write_text(voice_pack.readme_text(len(lines), version), encoding="utf-8")
    for f in files:
        _place(voice_make.mp3_file(store, f.removesuffix(".mp3")), dest / "Sound" / f)
    zip_path = out.parent / f"{FOLDER}-{version}.zip"
    zip_folder(out, zip_path)
    if problems := check_zip(zip_path, files):
        print("\n".join(f"voice pack: {p}" for p in problems), file=sys.stderr)
        return 1
    print(f"voice pack: {dest}\nvoice pack: {zip_path} ({zip_path.stat().st_size / 1024**2:.1f} MB)")
    return 0


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice pack")
    p.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
    p.add_argument("--store", help="the audio store (default: $VOICE_ROOT)")
    p.add_argument("--out", default="build/voice-pack", help="where the pack folder is written")
    p.add_argument("--version", default=datetime.date.today().isoformat())
    p.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
    a = p.parse_args(list(argv))
    store = voice_make.store_dir(a.store)
    if store is None:
        p.error("pack needs the audio store: --store DIR, or VOICE_ROOT in the environment")
    root = root or data_root()
    try:
        cfg = load_config(Path(a.config) if a.config else root.parent / CONFIG)
        return build(root, cfg, a.scope, store, Path(a.out), a.version)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"voice pack: {e}", file=sys.stderr)
        return 1
