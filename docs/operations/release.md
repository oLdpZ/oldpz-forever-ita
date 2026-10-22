# Runbook: validate, package, release

> How every pull request is checked, and how a release reaches CurseForge and GitHub in one action. Decision: [ADR-046](../adr/046-one-action-release.md) (with [ADR-006](../adr/006-git-repo-is-the-database.md), [ADR-008](../adr/008-generated-data-layout.md) and [ADR-034](../adr/034-forever-is-the-only-target.md)).

## Goal

A release is one action: start the **Release** workflow on `main`. The run checks everything, then releases what changed. The addon, when `## Unreleased` has lines: it writes the changelog, tags, builds and checks the zip, and publishes it to CurseForge and to a GitHub release. With nothing under `## Unreleased`, the run only runs the checks and releases nothing. The addon has no voice packs: there is no voice job and no voice secret. No local tools, no hand-made tags, no second pull request.

## One-time setup

The owner's checklist for this project, done once, in this order. Until the repository is public, the in-game
links to its issue forms open a page players cannot see.

### Before the repository goes public

Do these on the local checkout. [ADR-047](../adr/047-public-repository-hygiene.md) is why: what is published
stays published.

1. **Commit with your GitHub noreply address.** On GitHub, **Settings → Emails**, tick *Keep my email addresses
   private* and copy the address shown there (`<id>+oLdpZ@users.noreply.github.com`). Set it with
   `git config user.email "<that address>"`. The `text` check of every pull request (`wfj public-check pr`) fails a
   commit whose author or committer is not a noreply address, and every pushed commit publishes its address.
2. **Publish one commit of the tree, not the working history.** The history holds the old author address on every
   commit, upstream's Japanese data that this fork removed, and the planning notes. Make the public `main` a single
   commit: `git checkout --orphan public`, `git commit -m "oLd_pZ Forever - Traduzione Italiana"`, then push it as
   `main`. If the private GitHub repository already received the old history, delete the repository and create it
   again with the same name before that push: a force-push leaves the old commits reachable on GitHub by their id.
   Push no other branch or tag.
3. **Keep private material out of it.** Planning notes are not written for contributors: they live in a private
   folder outside the repository, linked into the checkout, and the link is listed in the git folder's
   `info/exclude` under a block headed `# Private project internals` (`wfj public-check paths` reads it). No tracked
   doc links into it. Keep the private rules file
   (`info/public-check-private.json` in the git folder, or `$WFJ_PRIVATE_RULES`) with the names, addresses and
   words that must never be published, so `wfj public-check content` runs them too.
4. **Run the checks.** `make lint` (it runs `wfj public-check all`: paths, content, comments, links, images) and
   `make test`. With the rules file in place the first line of `public-check` no longer says "no private rules".
   Then, on the new commit, `cd pipeline && BASE_REF=main PR_TITLE=x PR_BODY=x python -m wfj public-check pr`
   should print no problem.

### GitHub

5. **Make the repository public**: **Settings → General → Danger Zone → Change visibility**.
6. **Create the labels the issue forms set**: `translation-report` and `collector-send` (**Issues → Labels → New
   label**; `bug` and `enhancement` exist by default). A form only applies a label that exists, and the report and
   collector checks run only on issues that carry theirs.
7. **Actions settings** (**Settings → Actions → General**): allow GitHub Actions; workflow permissions *Read
   repository contents*; *Require approval for all outside collaborators* on fork pull requests.
8. **Private vulnerability reporting** (**Settings → Code security**): turn it on. `SECURITY.md` and the security
   link of the issue forms point at it; the setting does not exist on a private repository.
9. **Protect `main`** (**Settings → Rules → Rulesets**): require the `validate`, `lua` and `text` checks of
   `pr.yml` before a merge, and add a bypass that lets the Release workflow (GitHub Actions, pushing with the
   workflow's own token) push its changelog commit and tag to `main`. Confirm the exact bypass entry when the
   ruleset is made. Without it, a release fails at the push step and nothing is published.
10. Optional: **decide who can release.** Anyone with write access can run a workflow, so write access is the
    release permission.

### CurseForge

11. **Create the CurseForge project** **oLd_pZ Forever - Traduzione Italiana**, as a World of Warcraft addon, under
    the owner's account. Listing text, summary and categories: [CurseForge description](../curseforge.md); icon:
    `docs/images/logo.png`.
12. **Put the project's numeric id in the TOC**: `## X-Curse-Project-ID: <id>` in
    `addon/OldpZ_ForeverITA/OldpZ_ForeverITA.toc`, in a pull request with a changelog line, e.g. under
    `### Changed`: `- Linked the addon to its CurseForge project.` The package check accepts a TOC without the line,
    but then the packager has no CurseForge project to upload to and publishes the GitHub release only.
13. **Add the CurseForge API token as the repository secret `CF_API_KEY`.** Make the token on the CurseForge author
    site, under your account's API tokens (the packager's README links the current page), and add it under
    **Settings → Secrets and variables → Actions → New repository secret**. It is never written into the repo.
    Without it the run stops in its first job.

### First release

14. Run the [in-game test checklist](../testing/collaudo-rilascio.md) on the zip of `make package`, then cut the
    release as below.

## Cutting a release

1. Check `CHANGELOG.md` on `main`: the lines under `## Unreleased` are what players will read. With none, the run only runs the checks and releases nothing.
2. Start the run, either way:
   - GitHub: **Actions → Release → Run workflow**, branch `main`. Leave **Version** empty to use the [version rule](#versioning), or type one.
   - Terminal: `make release` (or `make release VERSION=x.y.z`). This needs the GitHub CLI (`gh`), signed in, with write access. It starts the same workflow on `main` and follows it until it ends.
3. When it is green, the job summary shows the version, the zip's file count and SHA-256, the GitHub release link and the notes. The CurseForge file appears after CurseForge processes it.

Only one Release run happens at a time: a second one waits until the first ends (if a third is started meanwhile, GitHub cancels the waiting one). A run that waited checks out `main` as it was when it was started; if the first release moved `main`, it fails at the push, before publishing. Start releases one by one.

To run a release again, always start a **new** run (Run workflow, or `make release`). GitHub's **Re-run** buttons repeat the old run's commit and inputs: they fail safely, but never finish a release.

## What the run does

Three jobs, in order. Nothing leaves the runner until the zip has passed the package check.

| Job | Steps |
|---|---|
| **plan** | Fails unless it runs on `main`. Fails if the `CF_API_KEY` secret is not set (this job only learns whether it is set, never its value). Picks the version with `wfj release next-version --allow-empty`: with `## Unreleased` empty it reports no addon release (`addon=false`) and the release job is skipped; otherwise it fails if `CHANGELOG.md` is out of shape (below), if a released section differs from the one at the latest release tag, if a typed version is malformed, or if it is not higher than the latest release. When re-running a release whose publish failed, refuses if its GitHub release already holds the zip (CurseForge never replaces a file, so publishing again would upload a duplicate). |
| **validate** | Every pull-request check (`pr.yml`, reused), on `main`. |
| **release** | 1. On the runner only: `wfj release changelog` moves the `## Unreleased` lines under `## X.Y.Z - YYYY-MM-DD`, leaves an empty `## Unreleased`, and writes this version's notes to `.release-notes.md`; commits `CHANGELOG.md` as `github-actions[bot]`; makes the annotated tag `vX.Y.Z`. 2. Builds the zip with the BigWigsMods packager (build only), from `.pkgmeta` and the TOC; `## Version: @project-version@` becomes `vX.Y.Z`. 3. `wfj package-check` checks the zip (below). 4. Pushes the commit and the tag together (`git push --atomic`): if `main` moved since the run started, the push fails and nothing is published. 5. Runs the packager again on the folder it just checked (no fresh copy: the same files, byte for byte, zipped again), which zips it and uploads it to CurseForge (an alpha, beta or release file, from the tag name) and creates the GitHub release with the same zip and the version's notes (a pre-release for alpha and beta). This is the only step that sees the CurseForge token; the write token is only given to the push and this step. 6. Checks the zip once more (a failure here is a warning: the file is already live) and writes the job summary. |

The zip is `OldpZ_ForeverITA-vX.Y.Z-forever.zip`. Inside is one folder, `OldpZ_ForeverITA/`: the files of `addon/OldpZ_ForeverITA/` plus `LICENSE` and `ATTRIBUTION.md`. The packager uploads it under the Forever game version, which it reads from the TOC's `## Interface`. The addon targets Forever only and is never published under another game version.

**The package check** (`wfj package-check <zip> --version X.Y.Z`) fails, naming the path or field, when:
- the zip has a top-level entry other than `OldpZ_ForeverITA/`;
- it holds a file that is not a tracked file of `addon/OldpZ_ForeverITA/` (dotfiles such as `.gitkeep` never ship), `LICENSE` or `ATTRIBUTION.md`, or lacks one of them;
- a file the TOC lists is missing;
- the TOC's `## Version` is not `vX.Y.Z`;
- `## X-Curse-Project-ID` is there but is not a number (the line may be missing until the CurseForge project exists);
- the TOC has a `## Dependencies`, `## RequiredDeps`, `## OptionalDeps` or other `## Dep…` line.

The release commit is pushed with the workflow's token, so it does not start the other workflows again.

## Versioning

Versions follow [Semantic Versioning](https://semver.org/). Allowed forms: `X.Y.Z`, `X.Y.Z-alpha.N`, `X.Y.Z-beta.N`. With the Version field empty, the next version is:

| Latest release tag | Next version |
|---|---|
| none | `0.1.0-alpha.1` |
| a pre-release, e.g. `0.1.0-alpha.3` | the same base, N + 1: `0.1.0-alpha.4` |
| a release, and `## Unreleased` has a `### Breaking` line | next major: `2.0.0` after `1.4.2` |
| a release, and `## Unreleased` has an `### Added` line | next minor: `1.5.0` after `1.4.2` |
| a release, otherwise | next patch: `1.4.3` after `1.4.2` |

The addon ships as **alpha** until the maintainer decides otherwise. Leaving alpha (to beta, or to a full release) is done by typing the version, e.g. `0.1.0-beta.1` or `1.0.0`; after that the rule counts on from it. A typed version must be higher than the latest release.

What the groups mean for players: **Breaking** is a change that resets their settings or stops an old setting or saved data from working; **Added** is something new; **Changed**, **Fixed** and **Removed** are the rest.

## Writing changelog lines

`CHANGELOG.md` is the only source of release notes: the run publishes a version's section as the CurseForge changelog and the GitHub release text.

- Every pull request that changes `addon/` or `data/` (moving a file out of them counts) adds at least one line under `## Unreleased`, in the right group (`### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Breaking`). Add the group heading if it is not there yet.
- Each line is a `- ` entry under a group heading; a long entry may continue on indented lines. Released sections are headed `## X.Y.Z - YYYY-MM-DD` (a hyphen), written by the release run.
- Write for players: what they will see in the game, in plain words. Not how it was built.
- No local file paths, and nothing the private rules of `wfj public-check` name.
- Never edit a released section.

The **Changelog** check on every pull request (`wfj release changelog-gate`) enforces the shape, the line for `addon/` and `data/` changes, released sections staying as they were (compared at the point the pull request branched from), and no ticket ids or local paths. Writing for players is up to the author and the reviewer. Pull requests that only change docs, CI, tests or the pipeline need no line.

A pull request that branched before a release can still merge its line into the section that release wrote (git merges it without a conflict). The next release run catches it: it compares the released sections with those at the latest release tag and stops, naming the tag. Move the line back under `## Unreleased` in a pull request.

## Dry run

`make package` rehearses the next release on your machine. It clones the committed `HEAD` into `build/package-src`, cuts the changelog and tags there, runs the same pinned packager (downloaded once into `build/`), runs the package check, and copies the zip to `build/`. Nothing is pushed or uploaded. Uncommitted changes are not included. It needs bash 4 or later (macOS: `brew install bash`) and takes a few minutes. It stops with "nothing to release" when `## Unreleased` is empty, and at the package check while the TOC has no CurseForge project id. Details: [Local setup](local-setup.md).

## Every pull request

`.github/workflows/pr.yml` runs on every pull request, on pushes to `main`, by hand, and inside the Release run. Its token is read-only, and every third-party action is pinned to a full commit SHA (the version is in a comment next to it). It has three jobs that run beside each other: `validate` (the Python checks and the data gate, steps 1 to 4), `lua` (the addon's tests under coverage, step 5) and `text` (the pull request's wording; [Pull-request gates](../testing/strategy.md#continuous-integration)). The wait is the longest job, not the three in a row.

1. Check out with full history (the base branch is needed), set up Python 3.14 with a pip cache keyed on `pipeline/pyproject.toml`, `pip install -e "pipeline[dev]"`.
2. Pull requests only: **Changelog** (`wfj release changelog-gate --base origin/<base>`, above), and **Data delta**: when the pull request changes `data/`, `wfj stats --delta origin/<base>` (what the English gained, lost or changed, and which lines moved status) is written to the run's job summary. A summary needs no write permission; a pull-request comment would, and pull requests from forks never get one.
3. The Lua toolchain, from the local composite action `.github/actions/lua-toolchain/action.yml` (the `lua` job runs the same action): PUC Lua 5.1 and luarocks with the rocks pinned in `.github/lua-rocks.txt`, restored from one cache whose key covers the runner image, the Lua and luarocks versions (the action's inputs, with defaults), the pin file, `.github/scripts/lua-rocks.sh` and the action file itself. A run with nothing changed downloads no toolchain; a pin bump or an edit of the action rebuilds it once in each of the two jobs that run the action (both save the same key, and the second save is refused without failing). On a miss the toolchain is built from a clean slate, each install action gets one retry after cleaning up, the rocks are installed by `lua-rocks.sh install`, and the cache is saved. `lua-rocks.sh verify` then checks the installed tree equals the pins. The build has no time limit of its own; the job's limit bounds it. A broken cache is removed with `gh cache delete` ([Local setup → Bumping a Lua rock](local-setup.md#bumping-a-lua-rock)).
4. `make lint LUA=lua` → `make coverage-py` (the pipeline's tests under coverage) → `make luac LUA=lua` → `make toc-check` → `make validate LUA=lua VALIDATE_FLAGS="${BASE_REF:+--base origin/$BASE_REF}"`. On pull requests the base branch arrives through the step's `env`, never as an expression inside the script. `make validate` runs `wfj validate` (schema; the provenance rule: no line that was `human` at the base may be `machine` now; no English hash collisions; every shipped line's references; a regenerate-and-diff of `addon/OldpZ_ForeverITA/Data/` and the TOC's generated block), then `luac` over every addon file ([Pipeline → Generate + validate](../systems/pipeline.md)). Outside pull requests there is no base, and the provenance rule is skipped with a note.
5. The `lua` job: check out, the same toolchain action, `make coverage-lua LUA=lua` (the addon's tests under coverage). It sets up no Python.

## Forever patch day

A new Forever client build: a pull request that updates `pipeline/clients.toml` and the TOC's `## Interface` → re-import the English from the new client ([Local setup](local-setup.md)) → `make data` → review `wfj check --report` (new stale or rejected lines) → `make letter-pages` (which book pages are letters) → `make coverage` (also rewrites the counts in the README and the CurseForge description) → the pull request, with its changelog line → a release run.

## Verify

- The run is green and its summary shows the version, file count and SHA-256.
- The GitHub release `vX.Y.Z` has the zip and the notes (marked pre-release for alpha and beta).
- The file is on the CurseForge project under the Forever game version, and the CurseForge app updates a test install.
- `main` has the `Release X.Y.Z` commit and the tag `vX.Y.Z`; `CHANGELOG.md` has an empty `## Unreleased` on top.
- If the counts in the README changed since the last release: the CurseForge description is pasted again from [CurseForge description](../curseforge.md).

## Rollback

Releases always ship the tip of `main`; there is no rebuilding an old commit.

1. Revert the bad change in a pull request. It touches `addon/` or `data/`, so it adds its own changelog line saying what was undone (e.g. under `### Fixed`).
2. Merge it, then run a release. The next version ships the fix.
3. Optional: on the CurseForge project page, archive the bad file so it is no longer offered.

## Rotating the CurseForge token

Create a new token on the CurseForge author site, replace the value of the `CF_API_KEY` secret (**Settings → Secrets and variables → Actions**), then revoke the old token on CurseForge. The next release run uses the new one; nothing in the repo changes.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `release: HEAD is already released as vX: to finish that release, run again with version X …` | Nothing was merged since the last release. If that release's publish failed, run again typing its version; otherwise merge a change first. |
| `release: released sections of CHANGELOG.md differ from vX …` | A change merged across a release put its line inside a released section. Move it back under `## Unreleased` in a pull request, then release. |
| `release: … needs exactly one '## Unreleased' section`, `… is not '## Unreleased' or '## X.Y.Z - YYYY-MM-DD'`, `… is not a changelog group`, `… not a '- ' entry` | `CHANGELOG.md` is out of shape ([Writing changelog lines](#writing-changelog-lines)). Fix it in a pull request. |
| `release: nothing to release: '## Unreleased' in CHANGELOG.md has no entries` | No change since the last release added a changelog line. Nothing to do, or merge the pending changes first. |
| `release: version X is not higher than the latest release Y` | A typed version is at or below the latest tag. Type a higher one, or leave the field empty. |
| `release: 'X' is not a version …` | Use `X.Y.Z`, `X.Y.Z-alpha.N` or `X.Y.Z-beta.N`, with no leading `v`. |
| `The CF_API_KEY repository secret is not set` | Add it ([One-time setup](#one-time-setup), step 13). |
| `Run the Release workflow on the main branch.` | The run was started on another branch. Start it on `main`. |
| `package-check: ## X-Curse-Project-ID is '…': fill in the CurseForge project id` | The TOC's id line is there but is not a number. Put the project's numeric id ([One-time setup](#one-time-setup), step 12). |
| `package-check: not a shipped file: …` / `missing from the zip: …` / `the TOC lists a file the zip lacks: …` | The zip does not match the addon folder. Check `.pkgmeta` (`move-folders`, `ignore`) and the TOC's file list; rehearse with `make package`. |
| `package-check: ## Dependencies: the addon never depends on another addon` | Remove the dependency line from the TOC. The addon has no dependencies. |
| The push step fails (rejected, not a fast-forward) | `main` moved while the run was going. Nothing was published and nothing was pushed. Run the release again. |
| The push step fails on a rule of the `main` ruleset | The release's bypass is missing ([One-time setup](#one-time-setup), step 9). Nothing was published. |
| The publish step fails after the push (CurseForge down, a token problem, or CurseForge has no Forever game version yet) | The commit and tag are on `main`, but the zip may not be published. First look at the CurseForge project's files and the GitHub release `vX.Y.Z`. If CurseForge already has the file (the packager uploads there first), do not run again: attach the zip to the GitHub release by hand if it is missing. Otherwise fix the cause, then start a new run, **typing the same version**: it sees the tag on `main`'s tip, skips the changelog, commit, tag and push, rebuilds from the tagged commit and publishes. It refuses if the GitHub release already holds the zip. This only works while the release commit is still the tip of `main`; if other changes were merged since, the next release (a higher version) ships them all, and its notes cover only its own `## Unreleased` lines. |
| `Changelog` fails on a pull request: `this change touches addon/ or data/: add a line for players …` | Add a line under `## Unreleased` ([Writing changelog lines](#writing-changelog-lines)). |
| `Changelog` fails: `released sections of CHANGELOG.md changed` or `changelog line names a local path or something private` | Only `## Unreleased` may change, and its lines are for players. |
| `v… is already published on GitHub. If CurseForge lacks it, upload that zip there by hand` | The release finished (or finished on GitHub): there is nothing to re-run. If CurseForge lacks the file, download the zip from the GitHub release and upload it on the CurseForge project page. |
| `validate` drift on a contributor pull request (`regenerate: … differs from a regeneration`, a missing or extra shard, or a TOC-block difference) | Run `make generate` and commit the regenerated `Data/` and TOC with the `data/` change. Never hand-edit `Data/` or the lines between the TOC's generated markers. (`make data` is the full re-import; see [Local setup](local-setup.md).) |
| `validate` fails the provenance rule (`… <type> <id>/<field> was human at origin/main, now machine`) | A human translation was overwritten by machine output. Restore the human line, or record a `correction`: machine output never replaces a human line silently. |

## Related

- [ADR-046: one-action release](../adr/046-one-action-release.md)
- [Local setup](local-setup.md) (`make package`, `make release`)
- [Testing strategy](../testing/strategy.md) (what CI and the release gates check)
- [Pipeline](../systems/pipeline.md) (`wfj release`, `wfj package-check`)
- [`CHANGELOG.md`](../../CHANGELOG.md)
