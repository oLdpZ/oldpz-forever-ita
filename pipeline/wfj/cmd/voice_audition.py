"""wfj voice audition: the first lines of every speaker of a scope, made and put on one page to listen to.

  audition --scope S [--per N] --store DIR [--env-file F] [--config F]
      Makes (through `voice_make.generate`, so with the same engine, store and record: a file already made
      is not made again) the first N lines of each speaker, ordered by key, with both sexes' files where a
      line has variants, and writes DIR/audition/index.html: a row per speaker with its name, audio profile
      (as sent to the engine), Gemini voice, director's notes and a player for each file; then the spoken
      versions (the written text beside the spoken one, with the reason) and the takes the filter blocked.

The page is Italian (the owner reads it), static, and holds no key: only what the store and the data hold.
"""

from __future__ import annotations

import argparse
import html
import string
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from wfj.cmd import voice_make
from wfj.cmd.voice import read_rows, scope_path, shipped_lines
from wfj.cmd.voice_cast import CONFIG, VOICES, in_scope, load_config
from wfj.core import voice
from wfj.io import gemini
from wfj.paths import data_root

PER = 2  # lines of each speaker
TEMPLATE = Path(__file__).resolve().parent.parent / "emit" / "voice_audition.html"
NARRATORS = {voice.NARRATOR: "Narratore", voice.BOOK_NARRATOR: "Narratore dei libri"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def speakers_of(root: Path, scope: str) -> dict[str, int | str]:
    """{line key: its main speaker} for the scope."""
    quests, books = voice.read_scope_file(scope_path(root, scope))
    rows = in_scope(read_rows(root / "voice" / "speakers.jsonl"), quests, books)
    return {r["key"]: r["speaker"] for r in rows}


def chosen_keys(
    takes: Sequence[voice_make.Take], speakers: Mapping[str, int | str], per: int
) -> dict[str, int | str]:
    """{key: speaker} of the first `per` lines (by key) of each speaker that have a take to make."""
    keys = sorted({t.job.key for t in takes if t.job.key in speakers})
    taken: dict[int | str, int] = defaultdict(int)
    out: dict[str, int | str] = {}
    for k in keys:
        who = speakers[k]
        if taken[who] < per:
            taken[who] += 1
            out[k] = who
    return out


def prompt_parts(prompt: str) -> tuple[str, str]:
    """(audio profile, director's notes) of a prompt, as sent."""
    head, _, _ = prompt.partition("\n\n#### TRANSCRIPT\n")
    profile, _, notes = head.partition("\n\n### DIRECTOR'S NOTES\n")
    return profile.removeprefix("# AUDIO PROFILE: "), notes


def speaker_name(who: int | str, names: Mapping[int, str]) -> str:
    if isinstance(who, int):
        return names.get(who) or f"Creatura {who}"
    return NARRATORS.get(who, who)


def player(store: Path, take: voice_make.Take) -> str:
    stem = take.job.stem
    sex = " (personaggio femminile)" if take.job.sex == "f" else ""
    if voice_make.mp3_file(store, stem).is_file():
        # the page is DIR/audition/index.html: the files are in DIR/mp3
        audio = f'<audio controls preload="none" src="../mp3/{esc(stem)}.mp3"></audio>'
    else:
        audio = '<p class="manca">file non generato</p>'
    return (
        f'<li><span class="file">{esc(stem)}{esc(sex)}</span>'
        f'<p class="testo">{esc(take.transcript)}</p>{audio}</li>'
    )


def creature_sections(
    store: Path, cfg: Mapping[str, Any], takes: Sequence[voice_make.Take], chosen: Mapping[str, int | str],
    names: Mapping[int, str],
) -> str:
    """A section per speaker: its voices (profile, Gemini voice, notes) and each one's files."""
    by_speaker: dict[int | str, dict[str, list[voice_make.Take]]] = defaultdict(lambda: defaultdict(list))
    for t in takes:
        if t.job.key in chosen:
            by_speaker[chosen[t.job.key]][t.job.voice].append(t)
    ordered = sorted(by_speaker, key=lambda w: (isinstance(w, str), str(w) if isinstance(w, str) else w))
    out = []
    for who in ordered:
        parts = [f'<section class="creatura"><h2>{esc(speaker_name(who, names))}</h2>']
        for vid, group in by_speaker[who].items():
            profile, notes = prompt_parts(group[0].prompt)
            parts.append(
                '<div class="voce"><dl>'
                f"<dt>Profilo</dt><dd>{esc(profile)}</dd>"
                f"<dt>Voce</dt><dd>{esc(cfg['roster'][vid]['gemini_voice'])} ({esc(vid)})</dd>"
                f"<dt>Regia</dt><dd>{esc(notes)}</dd></dl>"
                f'<ul class="battute">{"".join(player(store, t) for t in group)}</ul></div>'
            )
        parts.append("</section>")
        out.append("".join(parts))
    return "\n".join(out)


def table(head: Sequence[str], rows: Sequence[Sequence[str]], empty: str) -> str:
    if not rows:
        return f"<p>{esc(empty)}</p>"
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def spoken_table(root: Path, lines: Mapping[str, str]) -> str:
    """Each spoken version of a scoped line, whose written Italian it was made from, beside that text."""
    rows = []
    for (key, sex), r in sorted(voice_make.read_spoken(root).items()):
        it = lines.get(key)
        if it is not None and r.get("it_hash") == voice.it_hash(it):
            rows.append([key, sex, it, r["spoken"], r.get("reason", "")])
    return table(["Battuta", "Sesso", "Scritto", "Parlato", "Motivo"], rows, "Nessuna versione parlata.")


def blocked_table(store: Path, lines: Mapping[str, str]) -> str:
    rows = [
        [f, str(r.get("tries", "")), lines.get(str(r.get("key")), ""), str(r.get("reason", ""))]
        for f, r in sorted(voice_make.read_blocked(store).items())
    ]
    return table(["File", "Tentativi", "Scritto", "Motivo"], rows, "Nessuna battuta bloccata.")


def page(root: Path, cfg: Mapping[str, Any], scope: str, store: Path, per: int) -> str:
    """The audition page for what the store holds now."""
    sv = voice_make.survey(root, cfg, scope)
    chosen = chosen_keys(sv.takes, speakers_of(root, scope), per)
    cast = {int(r["creature"]) for r in read_rows(root / "voice" / VOICES)}
    names = voice_make.english_names(root, cast)
    quests, books = voice.read_scope_file(scope_path(root, scope))
    lines = shipped_lines(root, quests, books)
    shown = [t for t in sv.takes if t.job.key in chosen]
    template = string.Template(TEMPLATE.read_text(encoding="utf-8"))
    return template.substitute(
        scope=esc(scope), per=esc(per), files=len(shown),
        creatures=creature_sections(store, cfg, sv.takes, chosen, names),
        spoken=spoken_table(root, lines), blocked=blocked_table(store, lines),
    )


def audition(  # noqa: PLR0913 - the engine, encoder, log and sleep are injected for the tests
    root: Path,
    cfg: Mapping[str, Any],
    scope: str,
    store: Path,
    engine: Any,
    per: int = PER,
    encode: Callable[[Path, Path], None] | None = None,
    log: Callable[[str], None] = print,
    sleep: Callable[[float], None] | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Makes the first `per` lines of each speaker (what the store lacks) and writes the page.
    → (the page, the generation's numbers)."""
    sv = voice_make.survey(root, cfg, scope)
    keys = set(chosen_keys(sv.takes, speakers_of(root, scope), per))
    result = voice_make.generate(
        root, cfg, scope, store, engine, encode=encode, log=log, sleep=sleep, keys=keys
    )
    out = store / "audition" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(root, cfg, scope, store, per), encoding="utf-8")
    return out, result


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice audition")
    p.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
    p.add_argument("--per", type=int, default=PER, help="lines of each speaker (default: %(default)s)")
    p.add_argument("--store", help="the audio store (default: $VOICE_ROOT)")
    p.add_argument("--env-file", help="a .env file holding GEMINI_API_KEY")
    p.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
    a = p.parse_args(list(argv))
    if a.per < 1:
        p.error("--per must be at least 1")
    store = voice_make.store_dir(a.store)
    if store is None:
        p.error("audition needs the audio store: --store DIR, or VOICE_ROOT in the environment")
    root = root or data_root()
    try:
        cfg = load_config(Path(a.config) if a.config else root.parent / CONFIG)
        key = gemini.read_key(Path(a.env_file) if a.env_file else None)
        engine = voice_make.make_engine(key, cfg["model"])
        out, r = audition(root, cfg, a.scope, store, engine, a.per, encode=voice_make.to_mp3)
    except (ValueError, KeyError, FileNotFoundError, gemini.EngineError) as e:
        print(f"voice audition: {e}", file=sys.stderr)
        return 1
    print(f"voice audition: made {r['made']} file(s), page → {out}")
    if r["stopped"]:
        print(f"voice audition: stopped: {r['stopped']}; run it again to resume", file=sys.stderr)
        return 1
    return 0
