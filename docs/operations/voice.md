# Runbook: the Italian voice over

> Make the NPC voices from the shipped Italian, build the pack, install it and try it in game. How it works: [Voice over](../systems/voice.md). Why: [ADR-104](../adr/104-voce-italiana-con-gemini.md).

## Goal
A pack folder, `OldpZ_ForeverITA_Voce`, and its zip, holding the audio of one scope (today the undead starting area, `tirisfal`), in step with the Italian the addon ships now, ready to install beside the main addon. For the whole game (`SCOPE=tutto`), one pack per quest level band plus `OldpZ_ForeverITA_Voce_Altro` ([The packs](../systems/voice.md#the-packs)), each under 420 MB.

The work runs from the repository root through `make voice-*` targets, or `cd pipeline && python -m wfj voice <verb>` for the verbs that have no target. `SCOPE` defaults to `tirisfal`.

## One-time setup
- **`lame`** on the path: it encodes the MP3s. `generate` checks before the first paid take and stops if it is missing.
- **The Gemini key.** The key belongs to the maintainer's Google account and is billed there; it never enters the repository. Give it to the run one of two ways:
  - the environment: `export GEMINI_API_KEY=…`;
  - a `.env` file kept **outside the checkout**, a line `GEMINI_API_KEY=…`, named with `VOICE_ENV=<file>` (`--env-file`).

  The key travels only in the request header; the tools print no key. Billing and quota are managed in the Google account, not here: check the account's quota and spend before a long run.
- **The audio store**: a folder outside the repository, `VOICE_STORE` (default `voce-store` in the home folder; `VOICE_ROOT` in the environment sets it). It holds the paid takes (`wav/`), the MP3s (`mp3/`), `blocked.jsonl`, `status.json` and the audition page. Never put it under the checkout: a worktree's removal or a `git clean` would lose takes that were paid for. Back it up like any paid work.
- **The inputs** (the VMaNGOS database, forever-vo, the client's display tables) are the ones the import already uses: [Local setup](local-setup.md).

## Steps
Each step reads the data of the one before. A step that only reads (`plan`, `status`) costs nothing; the paid ones are `audition` and `generate`.

### 1. Scope
```
cd pipeline && python -m wfj voice scope tirisfal --vmangos <mangos.sqlite> --forever-vo <forever-vo>
```
Writes `pipeline/voice_tirisfal.txt`: the zone's quests and book pages. It prints how many Forever quests it could not place (no giver captured, given by an object, given by a creature the database never spawns); `--list` names them. Commit the file when it changes.

### 2. Speakers
```
make voice-speakers SCOPE=tirisfal
```
Its inputs are variables with defaults under `predecessors/` (the import's inputs folder, not tracked; a worktree reads the main checkout's): `VOICE_DB` is the VMaNGOS database (default: `VMANGOS_PRIORITY_DB`, `predecessors/vmangos-priority/mangos.sqlite`) and `VOICE_DB_SHA` the commit its provenance names (default: `VMANGOS_UNIT_SHA`); `FOREVER_VO` is the forever-vo checkout (default `predecessors/forever-vo`) at `FOREVER_VO_SHA`, the pinned commit, which names the speakers of the quests the database lacks. Override any of them on the command line. The scope step takes the same database and forever-vo folder.

Writes `data/voice/speakers.jsonl`: who says each line. It prints the lines read by a narrator, the quests the database lacks, the lines with several speakers and the scoped lines with no Italian. Look at the narrator lines: a quest started by a creature that is not known should not be a narrator.

### 3. Profiles
```
cd pipeline && python -m wfj voice profiles build --vmangos <mangos.sqlite> --commit <sha> --client <client tables folder>
```
Writes `data/voice/profiles.jsonl`: race, gender, kind of being and role from the client's tables and VMaNGOS. Age, and what the tables do not say, comes from a casting pass:

```
python -m wfj voice profiles export --vmangos <mangos.sqlite> --out <folder>      # part-NN.jsonl of what needs judgement
python -m wfj voice profiles import --drafts <draft files> --model <id> --batch <name>
```
A draft never replaces a table value or a ruling; the import prints the speakers still owed an age. A ruling of the maintainer is written into the profile row with a `maintainer` provenance. `make validate` checks the file.

### 4. Cast
Edit `pipeline/voice.toml` if a kind of speaker needs another voice (the roster is the prebuilt Gemini voices; the notes are **English only**: loading `voice.toml` and the prompt builder refuse an accented letter or a common Italian word). Then:
```
make voice-cast SCOPE=tirisfal
```
Writes `data/voice/voices.jsonl`; it prints how many creatures each row got. One creature's voice, by a ruling, goes in `data/voice/overrides.jsonl` (`{"creature": id, "voice": "<roster id>"}`). Recasting a kind of speaker remakes only its lines.

### 5. Plan
```
make voice-plan SCOPE=tirisfal
```
Prints the files to make (new, changed, gone from the store), the characters, hours of audio and an estimated cost, the files per voice, and the **silent lines** by reason: no voice cast, no spoken version, a stale spoken version, a line the voice cannot read. Add `cd pipeline && python -m wfj voice plan --scope tirisfal --list` to name each silent line. Fix what can be fixed (a missing profile, a refused line) before paying.

### 6. Audition
```
make voice-audition SCOPE=tirisfal PER=2 VOICE_ENV=<.env>
```
Paid, a few files: it makes the first lines of each speaker (both sexes' files where a line has them) and writes `<store>/audition/index.html`: a row per speaker with its audio profile, the Gemini voice, the notes and a player for each file, then the spoken versions and the blocked takes. The owner listens and approves or rejects each voice. A rejected voice is changed in `voice.toml` (or an override) and the audition run again: only the changed files are made.

### 7. Spoken versions
```
cd pipeline && python -m wfj voice spoken export --scope tirisfal --out <file> --store <store>
```
Lists the lines that need a spoken version: those naming the player's class or race, and the takes the filter blocked (read from the store's `blocked.jsonl`), with a stale version offered again to revise. Each row: `{key, sex, it_hash, it, spoken, reason}`. Write `spoken` for each row: the same sense, lightly reworded, no `{class}` or `{race}`, English tags only. A line with no acceptable spoken version stays silent. Then:
```
python -m wfj voice spoken import <file> [--source <who wrote them>]
```
Checks every written row and writes `data/voice/spoken.jsonl`; one bad row and nothing is written. If the Italian changed since the export, export again. The owner listens to the spoken versions at the next audition.

### 8. Generate
```
make voice-generate SCOPE=tirisfal VOICE_ENV=<.env>
make voice-status
```
Paid. `LIMIT=n` stops after n files, a trial at a known cost: do `LIMIT=20` first and listen. Run it in the background for the whole scope; `make voice-status` shows done / total, the rate and the time left, and whether the process is alive. Every made file is recorded in `data/voice/audio.jsonl` as soon as it exists. Commit the record with the data it belongs to.

**Costs.** `plan` estimates from the text: about 11 characters of Italian a second, 25 audio tokens a second, 20 dollars a million tokens: about 1.80 dollars per hour of audio at the standard rate. It is an estimate: the real duration of a take varies (the same line took 30 to 37 seconds in three tries) and is measured on the WAV. A line re-made for a changed voice, note or profile is paid again; `plan` shows how many.

**Blocked lines.** The safety filter is random. A take is asked up to four times; a take blocked four times goes to `<store>/blocked.jsonl` and is not asked again until its line, spoken version, voice or profile changes. `generate` prints how many, and the next step is step 7: give them a spoken version, or leave them silent.

**Resume.** If the run stops it says why and how many files are left. Run the same command again: it continues from the record. After the engine answered busy (429, 503) the run already waited 5, 15, 45 and 120 seconds without spending a take; if it still stops, wait (evenings are busy) and run it again. A paid take whose MP3 was not written is encoded again from its kept WAV, not asked of the engine again. A missing `lame` or an unreadable take stops the run before more is spent.

**Daily cap.** On the owner's tier the TTS models take 100 requests a day each (reset at midnight Pacific time) and 10 a minute; `generate` asks one request per file, so it fits auditions, fixes and a pilot, not a whole game. For more, use batch mode (below).

### 8b. Generate in batch mode
```
make voice-batch-submit SCOPE=tirisfal VOICE_ENV=<.env>
make voice-batch-fetch VOICE_ENV=<.env>
```
Paid, at half the standard price, outside the daily request cap (batch has limits of its own, in enqueued tokens). `submit` sends every take `plan` lists, as one job (a JSONL file of `{key, request}` lines uploaded through the File API), and records it in `<store>/batches/<time>.json` with the fingerprint each take was sent for; a take the store holds or a waiting job was sent for is not sent again. Gemini targets a day; a job not done in 48 hours expires. `fetch` asks after every job not fetched yet: a finished job's takes are kept in the store's `wav/` and encoded and recorded exactly as `generate` does with a take it already holds, without asking the engine for anything. A take the filter blocked, or that failed, is listed and goes into the next `submit`; a line changed after sending is not shipped and is sent again. `wfj voice batch cancel` cancels the waiting jobs. `LIMIT=n` sends the first n (a trial).

### 9. Pack
```
make voice-pack SCOPE=tirisfal
```
Writes `build/voice-pack/OldpZ_ForeverITA_Voce/` (TOC, `Register.lua`, `LEGGIMI.txt`, `Sound/*.mp3`) and `build/OldpZ_ForeverITA_Voce-<version>.zip` (`--version`, default today's date). It prints the lines and files shipped, their size, and what it left out by reason: `blocked`, `missing`, `stale` (the Italian or the voice changed since the file), `damaged` (the file in the store is not the recorded one). A silent line is not an error; a file left out for `stale` means run `plan` and `generate` again. It refuses over 420 MB and writes nothing.

For the whole game, build the packs of `pipeline/voice-packs.toml`:
```
make voice-pack SCOPE=tutto PACK=all       # every pack
make voice-pack SCOPE=tutto PACK=21_40     # one pack, after a fix to its lines
```
Each pack is `build/voice-pack/OldpZ_ForeverITA_Voce_<suffix>/` and `build/OldpZ_ForeverITA_Voce_<suffix>-<version>.zip`, with the counts printed per pack; a pack with no line of the scope is not built. Any pack over 420 MB stops the run before anything is written: move a band boundary in the table (both packs it touches are released again). Install the zips beside the main addon like the single pack; remove an old `OldpZ_ForeverITA_Voce` folder.

## Install and test in game
1. Install the main addon `OldpZ_ForeverITA` as usual.
2. Unzip `OldpZ_ForeverITA_Voce-<version>.zip` into `Interface\AddOns\`, beside it. Restart the client fully (a new folder is not seen by `/reload`).
3. Run the [Voice over checklist](../testing/strategy.md#voice-over-checklist): it walks the pack loading, the Voce page, an offer, Alt, stop and skip, the queue, a female and a male character, books, the quest log button and the game's English voice coming back. The facts it settles are listed in [Voice over → Unverified in game](../systems/voice.md#unverified-in-game); record what you see.
4. Without the folder the addon behaves as before: no Voce page, no panel.

To remove the voice, delete the folder; the main addon is unchanged.

## Verify
- `make validate`: the voice tables are well formed (speakers, profiles, voices).
- `make test`, `make lint`: the voice tests use a fake engine and never call Gemini.
- `make voice-plan`: no file to make and no silent line you did not expect.

## Troubleshooting
| Symptom | Cause and fix |
|---|---|
| `no GEMINI_API_KEY in the environment` | export it, or give `VOICE_ENV=<.env>` |
| `generate` stops with `HTTP 429` or `503` | the engine is busy or over quota: wait, run it again |
| `generate` stops with `lame is not installed` | install `lame`; nothing was spent |
| a line is silent in game and `/fita debug` counts it as `stale` | its Italian changed after the audio was made: `make voice-plan`, `make voice-generate`, `make voice-pack` |
| a line is silent and counted `missing` | the pack has no file for it: it is silent in `plan` (no voice, no spoken version, blocked) |
| a female character hears nothing for a line | the pack has no female take (`nofemale`): the line needs `<key>_f` made |
| a voice reads the direction aloud | the notes or profile carry Italian; every verb that reads `voice.toml` names the voice and refuses to run |
| the pack is over 420 MB | narrow the scope, or build the level-band packs (`PACK=all`) and, if one is still over, split its band in `pipeline/voice-packs.toml`; nothing was written |
| `no voice pack '…'` | `PACK` is a suffix of `pipeline/voice-packs.toml` (`01_20`), a folder name, or `all` |
| the NPC's English voice stays off after a crash | it is put back at the next login; `Sound_EnableDialog 1` by hand otherwise |

## Related
- [Voice over](../systems/voice.md) · [ADR-104](../adr/104-voce-italiana-con-gemini.md) · [Local setup](local-setup.md) · [Release](release.md)
