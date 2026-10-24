"""wfj voice batch: a scope's audio made in Gemini's batch mode (half the price, no daily request cap, results
within a day).

  batch submit --scope S --store DIR [--limit N] [--env-file F] [--config F]
      Sends, as one batch job, every take `wfj voice plan` would make that the store does not hold yet and no
      batch still waiting was sent for (the same take is never paid twice): a JSONL file of `{key, request}`
      lines, the key being the file's stem, uploaded through the File API. The job is recorded in
      DIR/batches/<id>.json with the fingerprint each take was sent for.
      --limit N sends the first N (a trial).
  batch fetch [--store DIR] [--env-file F] [--config F]
      Asks after every job not fetched yet. A finished one's results are downloaded and each take is kept in
      the store (wav/, with the fingerprint it was sent for), then encoded and recorded exactly as `generate`
      does with a take it already holds: the engine is not asked for anything. A take
      the filter blocked, or that failed, is left out and goes into the next submit. A job still pending or
      running is reported and asked after again on the next fetch.
  batch cancel --store DIR [--env-file F]
      Cancels every job not finished yet (a take it already made is not lost: fetch it first).

A take whose line, voice or notes changed after it was sent is kept with its old fingerprint, so `generate`
never ships it: it is sent again.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from wfj.cmd import voice_make
from wfj.cmd.voice_cast import CONFIG, load_config
from wfj.core import voice
from wfj.io import gemini
from wfj.paths import data_root

BATCHES = "batches"


def jobs_dir(store: Path) -> Path:
    return store / BATCHES


def read_jobs(store: Path) -> list[tuple[Path, dict[str, Any]]]:
    """(record file, record) of every batch job sent from this store, oldest first."""
    d = jobs_dir(store)
    if not d.is_dir():
        return []
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(d.glob("*.json"))]


def _write_job(path: Path, job: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    voice_make._write_bytes(path, (json.dumps(job, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def waiting(store: Path) -> dict[str, str]:
    """stem → fingerprint of every take a job not fetched yet was sent for."""
    out: dict[str, str] = {}
    for _, job in read_jobs(store):
        if not job.get("fetched"):
            out.update(job["takes"])
    return out


def submit(  # noqa: PLR0913 - the clock is injected for the tests
    root: Path,
    cfg: Mapping[str, Any],
    scope: str,
    store: Path,
    engine: Any,
    limit: int | None = None,
    now: Callable[[], datetime.datetime] = lambda: datetime.datetime.now(datetime.UTC),
) -> dict[str, Any] | None:
    """Sends the takes to make as one batch job and records it; None when there is nothing to send."""
    sent = waiting(store)
    work = [
        t for t in voice_make.plan(root, cfg, scope, store)["work"]
        if voice_make.kept_take(store, t) is None and sent.get(t.job.stem) != t.fingerprint
    ]
    if limit is not None:
        work = work[:limit]
    if not work:
        return None
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    lines = "".join(
        json.dumps({"key": t.job.stem, "request": gemini.request_body(t.prompt, t.gemini_voice)},
                   ensure_ascii=False) + "\n"
        for t in work
    )
    display = f"ofi-{scope}-{stamp}"
    file_name = engine.upload(display, lines.encode("utf-8"))
    name = engine.create_batch(display, file_name)
    job = {
        "name": name, "scope": scope, "model": cfg["model"], "submitted": stamp, "input": file_name,
        "takes": {t.job.stem: t.fingerprint for t in work},
        "chars": sum(len(t.transcript) for t in work), "fetched": False,
    }
    _write_job(jobs_dir(store) / f"{stamp}.json", job)
    return job


def _results(path: Path) -> Sequence[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fetch_one(store: Path, record: Path, job: dict[str, Any], engine: Any) -> dict[str, Any]:
    """Asks after one job; a finished one's takes are kept in the store. → {state, kept, blocked, failed}."""
    answer = engine.get_batch(job["name"])
    state = gemini.batch_state(answer)
    out: dict[str, Any] = {"state": state, "kept": 0, "blocked": [], "failed": []}
    if state not in gemini.BATCH_DONE:
        return out
    if state == "SUCCEEDED":
        results = gemini.batch_results_file(answer)
        if results is None:
            raise gemini.EngineError(f"{job['name']}: succeeded with no results file")
        dl = record.with_suffix(".out.jsonl")
        engine.download(results, dl)
        for row in _results(dl):
            stem = row.get("key")
            fingerprint = job["takes"].get(stem)
            if fingerprint is None:
                continue
            if "response" not in row:
                out["failed"].append(f"{stem}: {json.dumps(row.get('error') or row.get('status'))[:200]}")
                continue
            try:
                wav = gemini.answer_wav(row["response"])
                voice_make.wav_seconds(wav)
            except gemini.Blocked as e:
                out["blocked"].append(f"{stem}: {e}")
                continue
            except (gemini.EngineError, ValueError, EOFError) as e:
                out["failed"].append(f"{stem}: {e}")
                continue
            voice_make.keep_wav(store, stem, fingerprint, wav)
            out["kept"] += 1
        missing = set(job["takes"]) - {r.get("key") for r in _results(dl)}
        out["failed"] += [f"{stem}: no result" for stem in sorted(missing)]
        dl.unlink()
    job.update(fetched=True, state=state, kept=out["kept"], blocked=out["blocked"], failed=out["failed"])
    _write_job(record, job)
    return out


class _NoEngine:
    """The engine `generate` gets after a fetch: every take it encodes is already in the store."""

    def synthesize(self, _prompt: str, _voice: str) -> bytes:
        raise gemini.EngineError("a batch fetch never asks the engine")


def fetch(
    root: Path, cfg: Mapping[str, Any], store: Path, engine: Any, log: Callable[[str], None] = print,
    encode: Callable[[Path, Path], None] | None = None,
) -> dict[str, Any]:
    """Every job not fetched yet: asked after, its takes kept, then the kept takes of its scope encoded and
    recorded. → {"pending": n, "kept": n, "made": n, "stopped": reason or None}."""
    out: dict[str, Any] = {"pending": 0, "kept": 0, "made": 0, "stopped": None}
    scopes: set[str] = set()
    for record, job in read_jobs(store):
        if job.get("fetched"):
            continue
        r = fetch_one(store, record, job, engine)
        if r["state"] not in gemini.BATCH_DONE:
            out["pending"] += 1
            log(f"voice batch: {job['name']} ({len(job['takes'])} takes): {r['state'].lower()}")
            continue
        out["kept"] += r["kept"]
        scopes.add(job["scope"])
        log(f"voice batch: {job['name']}: {r['state'].lower()}, {r['kept']} take(s) kept, "
            f"{len(r['blocked'])} blocked, {len(r['failed'])} failed")
        for why in (*r["blocked"], *r["failed"]):
            log(f"voice batch:   {why}")
    for scope in sorted(scopes):
        g = voice_make.generate(root, cfg, scope, store, _NoEngine(), encode=encode, kept_only=True,
                                log=lambda _: None)
        out["made"] += g["made"]
        if g["stopped"]:
            out["stopped"] = g["stopped"]
    return out


def cancel(store: Path, engine: Any, log: Callable[[str], None] = print) -> int:
    n = 0
    for _, job in read_jobs(store):
        if not job.get("fetched"):
            engine.cancel_batch(job["name"])
            log(f"voice batch: {job['name']}: cancel asked (fetch to keep what it made)")
            n += 1
    return n


def run(argv: Sequence[str], root: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="wfj voice batch")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("submit", "fetch", "cancel"):
        sp = sub.add_parser(name)
        sp.add_argument("--store", help="the audio store (default: $VOICE_ROOT)")
        sp.add_argument("--env-file", help="a .env file holding GEMINI_API_KEY")
        sp.add_argument("--config", help="voice.toml (default: pipeline/voice.toml)")
        if name == "submit":
            sp.add_argument("--scope", required=True, choices=sorted(voice.SCOPES))
            sp.add_argument("--limit", type=int, help="send only the first N takes")
    a = p.parse_args(list(argv))
    store = voice_make.store_dir(a.store)
    if store is None:
        p.error("batch needs the audio store: --store DIR, or VOICE_ROOT in the environment")
    if getattr(a, "limit", None) is not None and a.limit < 1:
        p.error("--limit must be at least 1")
    root = root or data_root()
    try:
        cfg = load_config(Path(a.config) if a.config else root.parent / CONFIG)
        key = gemini.read_key(Path(a.env_file) if a.env_file else None)
        engine = voice_make.make_engine(key, cfg["model"])
        if a.cmd == "submit":
            job = submit(root, cfg, a.scope, store, engine, a.limit)
            if job is None:
                print("voice batch: nothing to send")
            else:
                print(f"voice batch: sent {len(job['takes'])} take(s), {job['chars']:,} characters, as "
                      f"{job['name']}; results within a day: wfj voice batch fetch")
            return 0
        if a.cmd == "cancel":
            print(f"voice batch: {cancel(store, engine)} job(s) cancelled")
            return 0
        r = fetch(root, cfg, store, engine)
    except (ValueError, KeyError, FileNotFoundError, gemini.EngineError) as e:
        print(f"voice batch: {e}", file=sys.stderr)
        return 1
    print(f"voice batch: {r['kept']} take(s) received, {r['made']} file(s) made,"
          f" {r['pending']} job(s) waiting")
    if r["stopped"]:
        print(f"voice batch: stopped: {r['stopped']}", file=sys.stderr)
        return 1
    return 0
