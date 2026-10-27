"""wfj voice plan|generate|status: the audio files of a scope, made by Gemini TTS.

  plan --scope S [--store DIR] [--config F] [--list]
      What generate would make now, without making anything: the files missing and those whose Italian,
      spoken version, voice or notes changed, by voice, with their characters, the hours of audio and the cost
      they come to; and the lines that stay silent, by reason (no voice cast, no spoken version, a line the
      voice cannot read). --list names each silent line.
  generate --scope S --store DIR [--env-file F] [--limit N] [--config F]
      Makes them through Gemini (the key is GEMINI_API_KEY, from the environment or --env-file; a designed
      voice made in project N goes through GEMINI_API_KEY_N, see `gemini.Projects`) into DIR, the
      audio store: mp3/ holds what the pack ships (mono, 22.05 kHz, 32 kbps, no Xing / Info frame), wav/ the
      original take with the fingerprint it was made for (a take paid for but never encoded is encoded from
      it on the next run, not asked again). Each file is recorded in data/voice/audio.jsonl as soon as it is
      made, so a stopped run resumes where it stopped. A take the filter blocks four times goes to
      DIR/blocked.jsonl and is not asked again until its line, spoken version, voice or profile changes; a
      busy or failing engine, a missing encoder or an unreadable take stops the run.
      --limit N stops after N files made (a trial at a known cost).
  status --store DIR
      The running or last generation: done / total, rate, time left, and whether its process is alive.

The store is --store, else $VOICE_ROOT. A line said for a player of either sex (`{name}`, a `<a/b>` pair,
in the written Italian or in its spoken version) is made twice: `<key>` for a male character, `<key>_f`
for a female one; a voice other than the main speaker's adds `_<voice>` before it.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from wfj.cmd.voice import read_rows as _rows
from wfj.cmd.voice import scope_path, shipped_lines
from wfj.cmd.voice_cast import CONFIG, PROFILES, VOICES, in_scope, load_config
from wfj.core import casting, voice
from wfj.io import gemini
from wfj.io.jsonl_store import Store, dumps
from wfj.paths import data_root

LAME = ("lame", "-m", "m", "--resample", "22.05", "-b", "32", "--cbr", "-t", "--quiet")
AUDIO, SPOKEN, BLOCKED = "audio.jsonl", "spoken.jsonl", "blocked.jsonl"
ANY = "any"  # a spoken version both sexes hear
TRIES = 4  # takes the filter may block before the line goes to the blocked list
# What plan estimates from: Gemini says about 11 characters of Italian a second, and bills 25 audio tokens a
# second of speech at 20 dollars a million.
CHARS_PER_SECOND = 11
TOKENS_PER_SECOND = 25
DOLLARS_PER_MILLION_TOKENS = 20.0


# ---- the takes a scope needs -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Take:
    """One file to make, and the prompt that makes it. `project` is the one whose key reaches its voice."""

    job: voice.Job
    it: str
    transcript: str
    prompt: str
    gemini_voice: str
    fingerprint: str
    project: int = 1


@dataclass
class Survey:
    """Every take a scope needs, and the lines that stay silent: (file or key, kind, why)."""

    takes: list[Take]
    silent: list[tuple[str, str, str]]


def read_spoken(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """data/voice/spoken.jsonl by (key, sex): the spoken version of a line, for `m`, `f` or `any`."""
    return {(r["key"], r["sex"]): r for r in _rows(root / "voice" / SPOKEN)}


def spoken_for(
    spoken: Mapping[tuple[str, str], Mapping[str, Any]], key: str, sex: str, it: str
) -> tuple[str | None, bool]:
    """(the spoken version a player of `sex` hears, or None; whether one was left out as stale). A version
    for that sex wins over one for both; a version made from other Italian is stale and never read."""
    stale = False
    for s in (sex, ANY):
        row = spoken.get((key, s))
        if row is None:
            continue
        if row.get("it_hash") == voice.it_hash(it):
            return str(row["spoken"]), False
        stale = True
    return None, stale


def line_values(
    root: Path, lines: Mapping[str, str], spoken: Iterable[Mapping[str, Any]] = ()
) -> dict[str, list[str]]:
    """{pack key: the numbers its `$N<k>` take} for the lines (or spoken versions) that have any, from their
    English, as the addon fills them from the live text."""
    want = {k for k, it in lines.items() if "$N" in it}
    want |= {r["key"] for r in spoken if "$N" in str(r.get("spoken", "")) and r.get("key") in lines}
    if not want:
        return {}
    english = Store(root, english=True)
    en: dict[str, str] = {}
    for ln in english.load("quest"):
        en[voice.quest_key(ln["id"], ln["field"])] = ln["en"]
    for ln in english.load("gossip"):
        en[voice.gossip_key(ln["id"])] = ln["en"]
    for ln in english.load("book"):
        if ln.get("hash"):
            en[voice.book_key(str(ln["hash"]))] = ln["en"]
    return {k: voice.live_values(en[k]) for k in want if k in en}


def profile_text(name: str, profile: Mapping[str, Any], gender: str | None = None) -> str:
    """A creature's audio profile line: its English name, then who it is (profile fields, English values).
    `gender` overrides a mixed creature's, for the voice of one of its two genders."""
    facts = {f: profile.get(f) for f in casting.FIELDS}
    if gender:
        facts["gender"] = gender
    if facts.get("archetype") == "none":
        facts["archetype"] = None
    return "; ".join([name, *(f"{f}: {v}" for f, v in facts.items() if v)])


def line_voices(
    row: Mapping[str, Any],
    cast: Mapping[int, Mapping[str, Any]],
    cfg: Mapping[str, Any],
    names: Mapping[int, str],
    profiles: Mapping[int, Mapping[str, Any]],
) -> list[tuple[str, str]]:
    """[(voice id, audio profile)] of a line: its main speaker's voice first, then every other voice a
    speaker of it is cast to (a mixed creature's female voice too), each once. A speaker with no voice yet
    adds none."""
    out: dict[str, str] = {}
    for c in (row["speaker"], *row.get("others", ())):
        if c == voice.NARRATOR:
            pairs = [(cfg["narrator"], cfg["narrator_profile"])]
        elif c == voice.BOOK_NARRATOR:
            pairs = [(cfg["book_narrator"], cfg["book_narrator_profile"])]
        elif c in cast:
            v, p, name = cast[c], profiles.get(c, {}), names.get(c) or f"Creature {c}"
            mixed = bool(v.get("female"))
            pairs = [(v["voice"], profile_text(name, p, "male" if mixed else None))]
            if mixed:
                pairs.append((v["female"], profile_text(name, p, "female")))
        else:
            continue
        for vid, prof in pairs:
            out.setdefault(vid, prof)
    return list(out.items())


def build_prompt(key: str, profile: str, notes: str, transcript: str, name: str = "") -> str:
    """The prompt for one take. The profile and the notes are direction, so English only (Gemini reads
    anything else aloud); the transcript is Italian with English tags only (`voice.SPEECH_TAGS`). Raises
    VoiceError with the key otherwise: such a line is reported, never sent. `name`, the creature's English
    name the profile starts with, is left out of the check: "Drusilla La Salle" and "Una" are names."""
    direction = profile.removeprefix(name) if name else profile
    why = casting.not_english(f"{direction}\n{notes}")
    if why:
        raise voice.VoiceError(
            f"{key}: the audio profile and the director's notes must be English only, Gemini would read them"
            f" aloud ({why})"
        )
    bad = voice.tag_problem(transcript)
    if bad:
        raise voice.VoiceError(f"{key}: {bad}")
    return gemini.prompt_text(profile, notes, transcript)


def english_names(root: Path, creatures: set[int]) -> dict[int, str]:
    return {
        int(r["id"]): r["en"]
        for r in Store(root, english=True).load("unit")
        if r.get("field") == "name" and r["id"] in creatures
    }


def survey(root: Path, cfg: Mapping[str, Any], scope: str) -> Survey:
    """Every take the scope needs now, from its speakers, the shipped Italian, the cast, the profiles and the
    spoken versions."""
    quests, books = voice.read_scope_file(scope_path(root, scope))
    rows = in_scope(_rows(root / "voice" / "speakers.jsonl"), quests, books)
    lines = shipped_lines(root, quests, books)
    cast = {int(r["creature"]): r for r in _rows(root / "voice" / VOICES)}
    profiles = {int(r["creature"]): r for r in _rows(root / "voice" / PROFILES)}
    names = english_names(root, set(cast))
    spoken = read_spoken(root)
    values = line_values(root, lines, spoken.values())
    takes: list[Take] = []
    silent: list[tuple[str, str, str]] = []
    for row in rows:
        key = row["key"]
        it = lines.get(key)
        if it is None:
            continue
        sp = row["speaker"]
        if isinstance(sp, int) and sp not in cast:
            silent.append((key, "no voice", f"creature {sp} has no voice (wfj voice cast)"))
            continue
        voices = line_voices(row, cast, cfg, names, profiles)
        vals = values.get(key, ())
        # a spoken version that names the player, or picks a word by sex, is said for each sex too
        said_by_sex = [spoken_for(spoken, key, s, it)[0] for s in voice.SEXES]
        both = voice.needs_variants(it) or any(s is not None and voice.needs_variants(s) for s in said_by_sex)
        for sex in voice.SEXES if both else ("m",):
            said, stale = spoken_for(spoken, key, sex, it)
            tail = "_f" if sex == "f" else ""
            if said is None and voice.needs_spoken(it):
                kind = "stale spoken version" if stale else "no spoken version"
                silent.append((key + tail, kind, f"{key}: names the player's class or race"))
                continue
            for n, (vid, profile) in enumerate(voices):
                stem = (key if n == 0 else f"{key}_{vid}") + tail
                r = cfg["roster"][vid]
                try:
                    plain = voice.speech_text(it, key, sex, vals, said)
                    text = voice.respell(plain, cfg.get("pronounce", {}))
                    named = profile.split("; ", 1)[0] if isinstance(sp, int) else ""
                    prompt = build_prompt(stem, profile, r["notes"], text, named)
                except voice.VoiceError as e:
                    silent.append((stem, "refused", str(e)))
                    continue
                respelled = text if text != plain else None
                words = voice.text_hash(it, vals, said, respelled)
                fp = voice.fingerprint(words, vid, r["gemini_voice"], r["model"], r["notes"], sex, profile)
                takes.append(Take(voice.Job(stem, key, vid, sex), it, text, prompt, r["gemini_voice"], fp,
                                  r.get("project", 1)))
    return Survey(takes, silent)


# ---- the record and the store ----------------------------------------------------------------------------


def audio_record(root: Path) -> dict[str, dict[str, Any]]:
    return {r["file"]: r for r in _rows(root / "voice" / AUDIO)}


def read_blocked(store: Path | None) -> dict[str, dict[str, Any]]:
    """<store>/blocked.jsonl by file: the takes the filter blocked TRIES times."""
    return {r["file"]: r for r in _rows(store / BLOCKED)} if store is not None else {}


def mp3_file(store: Path, stem: str) -> Path:
    return store / "mp3" / f"{stem}.mp3"


def wav_file(store: Path, stem: str) -> Path:
    return store / "wav" / f"{stem}.wav"


def take_file(store: Path, stem: str) -> Path:
    """Beside a kept WAV: the fingerprint it was made for. A paid take whose MP3 or record was never written
    (the encoder failed, the run died) is encoded again from it, not asked of the engine again."""
    return store / "wav" / f"{stem}.json"


def kept_take(store: Path, t: Take) -> bytes | None:
    """The WAV the store already holds for this take, when it was made for the same fingerprint."""
    wav, side = wav_file(store, t.job.stem), take_file(store, t.job.stem)
    if not (wav.is_file() and side.is_file()):
        return None
    try:
        made_for = json.loads(side.read_text(encoding="utf-8")).get("fingerprint")
    except (ValueError, AttributeError):
        return None
    return wav.read_bytes() if made_for == t.fingerprint else None


def keep_take(store: Path, t: Take, wav: bytes) -> None:
    """The paid take first, then what it was made for: a resume encodes it again from here."""
    keep_wav(store, t.job.stem, t.fingerprint, wav)


def keep_wav(store: Path, stem: str, fingerprint: str, wav: bytes) -> None:
    """`keep_take` by stem and fingerprint (a batch's results carry no Take, only what the job was sent
    for)."""
    (store / "wav").mkdir(parents=True, exist_ok=True)
    _write_bytes(wav_file(store, stem), wav)
    _write_bytes(take_file(store, stem), (json.dumps({"fingerprint": fingerprint}) + "\n").encode())


def record_row(t: Take, mp3: Path, seconds: float, provenance: Mapping[str, str]) -> dict[str, Any]:
    """The audio record's row for a made file."""
    return {
        "file": t.job.stem,
        "key": t.job.key,
        "voice": t.job.voice,
        "sex": t.job.sex,
        "it_hash": voice.it_hash(t.it),
        "fingerprint": t.fingerprint,
        "seconds": round(seconds, 2),
        "bytes": mp3.stat().st_size,
        "chars": len(t.transcript),
        "sha256": file_sha(mp3),
        "provenance": dict(provenance),
    }


def store_dir(arg: str | None) -> Path | None:
    """The audio store: --store, else $VOICE_ROOT, else none."""
    if arg:
        return Path(arg)
    env = os.environ.get("VOICE_ROOT", "").strip()
    return Path(env) if env else None


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Rows as JSONL, through a temporary file: a run stopped mid-write keeps the old file whole."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text("".join(dumps(dict(r)) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(path)


def _write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def file_sha(path: Path) -> str:
    """The SHA-256 of a made file: what proves the store holds the recorded take, not another of the same
    length (the encoder's constant bitrate makes equal lengths equal sizes)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---- plan ------------------------------------------------------------------------------------------------


def plan(
    root: Path, cfg: Mapping[str, Any], scope: str, store: Path | None = None,
    keys: Collection[str] | None = None,
) -> dict[str, Any]:
    """The files generate would make now (`work`), and why; the estimate; the silent lines. `keys` narrows
    the scope to those lines (a trial of a few)."""
    sv = survey(root, cfg, scope)
    if keys is not None:
        sv = Survey([t for t in sv.takes if t.job.key in keys], sv.silent)
    audio = audio_record(root)
    blocked = read_blocked(store)
    # a recorded file gone from the store is made again only where the store is
    held = store if store is not None and store.is_dir() else None
    count: Counter[str] = Counter()
    work: list[Take] = []
    for t in sv.takes:
        stem = t.job.stem
        rec = audio.get(stem)
        if blocked.get(stem, {}).get("fingerprint") == t.fingerprint:
            count["blocked"] += 1
            continue
        if rec is None:
            count["missing"] += 1
        elif rec.get("fingerprint") != t.fingerprint:
            count["stale"] += 1
        elif held is not None and not mp3_file(held, stem).is_file():
            count["gone"] += 1
        else:
            continue
        work.append(t)
    chars = sum(len(t.transcript) for t in work)
    seconds = chars / CHARS_PER_SECOND
    return {
        "files": len(sv.takes),
        "to_make": len(work),
        "missing": count["missing"],
        "stale": count["stale"],
        "gone": count["gone"],
        "blocked": count["blocked"],
        "chars": chars,
        "hours": seconds / 3600,
        "dollars": seconds * TOKENS_PER_SECOND * DOLLARS_PER_MILLION_TOKENS / 1_000_000,
        "by_voice": Counter(t.job.voice for t in work),
        "silent": sv.silent,
        "work": work,
    }


def run_plan(cfg: Mapping[str, Any], root: Path, scope: str, store: Path | None, listing: bool) -> int:
    p = plan(root, cfg, scope, store)
    gone = f", {p['gone']} gone from the store" if p["gone"] else ""
    print(
        f"voice plan ({scope}): {p['files']} files; to make {p['to_make']} ({p['missing']} new, {p['stale']}"
        f" changed{gone}), {p['chars']:,} characters, about {p['hours']:.2f} h of audio, about"
        f" ${p['dollars']:.2f}"
    )
    if p["blocked"]:
        print(f"voice plan: blocked by the filter, not asked again until their line changes: {p['blocked']}")
    for vid, n in sorted(p["by_voice"].items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"voice plan: voice {vid}: {n}")
    for kind, n in sorted(Counter(k for _, k, _ in p["silent"]).items()):
        print(f"voice plan: silent: {kind}: {n}")
    if listing:
        for stem, kind, why in p["silent"]:
            print(f"voice plan: silent: {stem}: {kind}: {why}")
    return 0


# ---- generate --------------------------------------------------------------------------------------------


def wav_seconds(wav: bytes) -> float:
    with wave.open(BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()


def to_mp3(wav: Path, out: Path) -> None:
    # encoded beside the file and renamed, so a run stopped mid-encode leaves no cut-off mp3 at its name
    part = out.with_name(out.name + ".part")
    try:
        subprocess.run([*LAME, str(wav), str(part)], check=True)
        part.replace(out)
    finally:
        part.unlink(missing_ok=True)


def make_engine(key: str, model: str) -> gemini.Engine:
    return gemini.Engine(key, model)


def projects(cfg: Mapping[str, Any], env_file: Path | None) -> gemini.Projects:
    """The engines of the roster's projects (each made by `make_engine` when first needed): a take in a
    designed voice goes through the key of the project that made it, every other take through project 1."""
    voices = {
        r["gemini_voice"]: r.get("project", 1)
        for r in cfg["roster"].values()
        if gemini.voice_kind(r["gemini_voice"]) == "designed"
    }
    return gemini.Projects(cfg["model"], env_file, voices, make=make_engine)


def _status(path: Path, **fields: Any) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(fields, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def generate(  # noqa: PLR0913, PLR0915 - the engine, encoder, log and sleep are injected for the tests
    root: Path,
    cfg: Mapping[str, Any],
    scope: str,
    store: Path,
    engine: Any,
    encode: Callable[[Path, Path], None] | None = None,
    log: Callable[[str], None] = print,
    limit: int | None = None,
    sleep: Callable[[float], None] | None = None,
    keys: Collection[str] | None = None,
    kept_only: bool = False,
) -> dict[str, Any]:
    """Makes every file plan lists (for `keys` only, when given), up to `limit`; resumable. The record and the
    blocked list are written after every file, and on the way out whatever stops the run. A busy or failing
    engine (or encoder) stops it: → `stopped`, the reason. A blocked take is listed and the run goes on.
    `kept_only`: only the takes the store already holds (a batch's results), so the engine is never asked.
    → the run's numbers."""
    p = plan(root, cfg, scope, store, keys)
    work: list[Take] = p["work"]
    if kept_only:
        work = [t for t in work if kept_take(store, t) is not None]
    out: dict[str, Any] = {"made": 0, "files": p["files"], "blocked": 0, "chars_made": 0, "seconds_made": 0.0,
                           "elapsed": 0.0, "stopped": None, "left": len(work), "silent": p["silent"]}
    if not work:
        return out
    encode = encode or to_mp3
    if encode is to_mp3 and shutil.which(LAME[0]) is None:
        # checked before the first paid take: a take that cannot be encoded is a take paid for nothing
        out["stopped"] = f"{LAME[0]} is not installed: it encodes the MP3s"
        return out
    audio = audio_record(root)
    blocked = read_blocked(store)
    for d in ("mp3", "wav"):
        (store / d).mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    source = f"gemini@{cfg['model']}"
    started = time.time()
    done = 0  # takes asked: made or blocked

    def save(finished: bool = False) -> None:
        write_jsonl(root / "voice" / AUDIO, (audio[k] for k in sorted(audio)))
        write_jsonl(store / BLOCKED, (blocked[k] for k in sorted(blocked)))
        elapsed = time.time() - started
        rate = out["chars_made"] / elapsed if elapsed > 0 else 0.0
        left = sum(len(t.transcript) for t in work[done:])
        _status(store / "status.json", scope=scope, pid=os.getpid(), started=started, updated=time.time(),
                done=out["made"], total=len(work), blocked=out["blocked"], chars_made=out["chars_made"],
                chars_left=left, rate=round(rate, 2), seconds_left=round(left / rate) if rate else None,
                finished=finished)
        out["elapsed"], out["left"] = elapsed, len(work) - done

    finished = False
    try:
        for t in work:
            if limit is not None and out["made"] >= limit:
                break
            stem = t.job.stem
            wav_path, mp3 = wav_file(store, stem), mp3_file(store, stem)
            kept = kept_take(store, t)
            try:
                wav = kept if kept is not None else gemini.synthesize_retry(
                    engine, t.prompt, t.gemini_voice, tries=TRIES, sleep=sleep or time.sleep)
            except gemini.Blocked as e:
                blocked[stem] = {"file": stem, "key": t.job.key, "sex": t.job.sex, "tries": TRIES,
                                 "reason": str(e), "it_hash": voice.it_hash(t.it),
                                 "fingerprint": t.fingerprint}
                out["blocked"] += 1
                done += 1
                log(f"voice generate: {stem}: blocked {TRIES} times ({e}), listed in {store / BLOCKED}")
                save()
                continue
            try:
                secs = wav_seconds(wav)
            except (wave.Error, EOFError) as e:
                raise gemini.EngineError(f"{stem}: the engine's audio is not a readable WAV ({e})") from None
            if kept is None:
                keep_take(store, t, wav)
            encode(wav_path, mp3)
            audio[stem] = record_row(t, mp3, secs, {"source": source, "imported": today})
            blocked.pop(stem, None)
            out["made"] += 1
            out["chars_made"] += len(t.transcript)
            out["seconds_made"] += secs
            done += 1
            save()
            log(f"voice generate: {done}/{len(work)} {stem}")
        else:
            finished = True
    except (gemini.EngineError, subprocess.CalledProcessError, OSError) as e:
        out["stopped"] = str(e)
    finally:
        save(finished)
    return out


def run_generate(
    cfg: Mapping[str, Any], root: Path, scope: str, store: Path, env_file: Path | None, limit: int | None
) -> int:
    engine = projects(cfg, env_file)
    try:
        engine.engine(1)  # project 1's key, read before anything is made (another's when first needed)
    except gemini.EngineError as e:
        print(f"voice generate: {e}", file=sys.stderr)
        return 1
    r = generate(root, cfg, scope, store, engine, encode=to_mp3, limit=limit)
    print(
        f"voice generate: made {r['made']} of {r['files']} files in {r['elapsed']:.0f} s"
        f" ({r['seconds_made']:.0f} s of audio) → {store}"
    )
    if r["blocked"]:
        print(f"voice generate: {r['blocked']} take(s) blocked by the filter, listed in {store / BLOCKED}:"
              " give them a spoken version (wfj voice spoken export)")
    for why in (why for _, kind, why in r["silent"] if kind == "refused"):
        print(f"voice generate: not sent: {why}", file=sys.stderr)
    if r["stopped"]:
        print(f"voice generate: stopped: {r['stopped']}; {r['left']} file(s) left: run it again to resume"
              f" (make voice-generate SCOPE={scope})", file=sys.stderr)
        return 1
    return 0


# ---- status ----------------------------------------------------------------------------------------------


def status_lines(store: Path) -> list[str]:
    path = store / "status.json"
    if not path.is_file():
        return [f"voice status: no run recorded in {store}"]
    s = json.loads(path.read_text(encoding="utf-8"))
    alive = False
    if not s.get("finished"):
        try:
            os.kill(int(s["pid"]), 0)
            alive = True
        except (OSError, ValueError, KeyError):
            alive = False
    state = "running" if alive else "stopped (resume: make voice-generate)"
    if s.get("finished"):
        state = "finished"
    left = s.get("seconds_left")
    eta = f", about {left / 3600:.1f} h left" if left else ""
    blocked = f", {s['blocked']} blocked" if s.get("blocked") else ""
    return [
        f"voice status: {state}: {s['done']}/{s['total']} files ({s['scope']}){blocked}, "
        f"{s.get('rate', 0)} characters a second{eta}"
    ]


# ---- entry -----------------------------------------------------------------------------------------------


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "generate", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--store", help="the audio store (default: $VOICE_ROOT)")
        if name == "status":
            continue
        sp.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
        sp.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
        if name == "plan":
            sp.add_argument("--list", action="store_true", help="name each silent line")
        else:
            sp.add_argument("--env-file", help="a .env file holding GEMINI_API_KEY (and _2, … by project)")
            sp.add_argument("--limit", type=int, help="stop after this many files")
    a = p.parse_args(list(argv))
    store = store_dir(a.store)
    if a.cmd == "generate" and a.limit is not None and a.limit < 1:
        p.error("--limit must be at least 1")
    if store is None and a.cmd != "plan":
        p.error(f"{a.cmd} needs the audio store: --store DIR, or VOICE_ROOT in the environment")
    if a.cmd == "status":
        print("\n".join(status_lines(store)))
        return 0
    root = root or data_root()
    try:
        cfg = load_config(Path(a.config) if a.config else root.parent / CONFIG)
        if a.cmd == "plan":
            return run_plan(cfg, root, a.scope, store, a.list)
        env_file = Path(a.env_file) if a.env_file else None
        return run_generate(cfg, root, a.scope, store, env_file, a.limit)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"voice {a.cmd}: {e}", file=sys.stderr)
        return 1
