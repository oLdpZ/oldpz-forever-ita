"""wfj import: bring source data into data/ (see docs/systems/pipeline.md).

  wfj import english pfquest <quests.lua> --commit SHA
  wfj import english wago-ids <ItemSparse.csv> <SpellName.csv> --build VERSION [--id-col C --name-col C]
      [--src wago|db2]
  wfj import english client-text <ItemSparse.csv> <Spell.csv> <ItemEffect.csv> --build VERSION
      [--src wago|db2]
                         (item / spell tooltip text and buff text, raw client templates)
  wfj import english collector <SavedVariables/OldpZ_ForeverITA.lua>
  wfj import english vmangos <mangos.sqlite> --commit SHA   (quest progress/completion + gossip)
  wfj import english forever-vo <checkout> --commit SHA     (quest progress/completion players recorded)
  wfj import english wdb <questcache.wdb> --build VERSION [--questv2 QuestV2.csv [--missing PATH]]
                         [--allow-shrink] [--dry-run]
                         (Blizzard's cached quest title / objectives / description, ADR-020)
  wfj import english served <QuestV2.csv> <questcache.wdb> <ItemSparse.csv> <SpellName.csv>
      [--map-cache WDB]... [--dry-run]
                         (drop English for ids the target client, Forever, does not serve; run last)
  wfj import english wago-ui <GlobalStrings.csv> <ItemSubClass.csv> --keys ui_keys.txt --build VERSION
      [--src wago|db2]
      [--enchantments SpellItemEnchantment.csv]
                         (exactly the curated UI keys)
  wfj import draft <type> <draft.jsonl> --model ID [--critic ID] --date D --name NAME   (ADR-014)
  wfj import official <retail folder> --build VERSION --date D [--names PATH]
                         (Blizzard's itIT text where the retail English is Forever's: cmd/import_official)

English importers merge by source: an importer replaces its own lines and any line whose
(id, field) it provides, and keeps every other source's lines; a collector line (English a client recorded in
game) outranks pfQuest and VMaNGOS, and the collector import replaces those stand-ins (ADR-053).

Every line written is `status: pending` (`check` assigns real statuses). Duplicate (id, field) pairs
with identical Italian collapse (origins recorded); different Italian lands in `conflicts`.
`draft` merges machine-drafted text into any
type's store as `machine` variants and never edits a hand-written one (run_draft, ADR-014).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from wfj.cmd import import_official, served
from wfj.cmd.import_draft import run_draft
from wfj.cmd.import_english import (
    CLIENT_TABLE_SOURCES,
    MERGE_HELP,
    SRC_HELP,
    run_client_text,
    run_collector,
    run_forever_vo,
    run_pfquest,
    run_vmangos,
    run_wago,
    run_wago_ui,
    run_wdb,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wfj import")
    sub = p.add_subparsers(dest="source", required=True)
    _add_english(sub)
    _add_draft(sub)
    import_official.add_parser(sub)
    return p


def _add_english(sub: Any) -> None:
    """`wfj import english <kind>`: every English source."""
    en = sub.add_parser("english")
    esub = en.add_subparsers(dest="kind", required=True)
    pf = esub.add_parser("pfquest")
    pf.add_argument("file")
    pf.add_argument("--commit", required=True)
    pf.set_defaults(fn=run_pfquest)
    _add_client_tables(esub)
    co = esub.add_parser("collector")
    co.add_argument("file")
    co.set_defaults(fn=run_collector)
    vm = esub.add_parser("vmangos")
    vm.add_argument("file")
    vm.add_argument("--commit", required=True)
    vm.set_defaults(fn=run_vmangos)
    fv = esub.add_parser("forever-vo")
    fv.add_argument("folder")
    fv.add_argument("--commit", required=True)
    fv.add_argument(
        "--skip", metavar="FILE", help="greeting keys never imported, `<key>\\t<reason>` per line"
    )
    fv.set_defaults(fn=run_forever_vo)
    wd = esub.add_parser("wdb")
    wd.add_argument("--merge", choices=("replace", "union"), default="replace", help=MERGE_HELP)
    wd.add_argument("file")
    wd.add_argument("--build", required=True)
    wd.add_argument("--questv2", metavar="CSV", help="wago QuestV2.csv: print coverage")
    wd.add_argument("--missing", metavar="PATH", help="write the unanswered QuestV2 ids (needs --questv2)")
    wd.add_argument(
        "--allow-shrink", action="store_true", help="accept a cache missing quests of the same build"
    )
    wd.add_argument("--dry-run", action="store_true", help="run every check, print the report, write nothing")
    wd.set_defaults(fn=run_wdb)
    served.add_parser(esub)


def _add_client_tables(esub: Any) -> None:
    """The imports read from client tables (a wago export or the local archive): ids, UI, item/spell text."""
    wg = esub.add_parser("wago-ids")
    wg.add_argument("item_csv")
    wg.add_argument("spell_csv")
    wg.add_argument("--build", required=True)
    wg.add_argument("--id-col")
    wg.add_argument("--name-col")
    wg.add_argument("--src", choices=CLIENT_TABLE_SOURCES, default="wago", help=SRC_HELP)
    wg.add_argument(
        "--merge", choices=("replace", "union"), default="replace", help=MERGE_HELP
    )
    wg.set_defaults(fn=run_wago)
    wu = esub.add_parser("wago-ui")
    wu.add_argument("globalstrings_csv")
    wu.add_argument("itemsubclass_csv")
    wu.add_argument("--keys", required=True)
    wu.add_argument("--enchantments", help="SpellItemEnchantment.csv: the SpellItemEnchantment:* family")
    wu.add_argument("--subtexts", help="Spell.csv (ID, NameSubtext_lang): the SpellSubtext:* family")
    wu.add_argument(
        "--families",
        help="a client folder holding the text-family tables (Faction.csv, Achievement.csv, …): every "
        "io/wago.TEXT_FAMILIES family",
    )
    wu.add_argument("--build", required=True)
    wu.add_argument("--src", choices=CLIENT_TABLE_SOURCES, default="wago", help=SRC_HELP)
    wu.add_argument(
        "--merge", choices=("replace", "union"), default="replace", help=MERGE_HELP
    )
    wu.set_defaults(fn=run_wago_ui)
    ct = esub.add_parser("client-text")
    ct.add_argument("item_csv", help="ItemSparse.csv (ID, Description_lang)")
    ct.add_argument("spell_csv", help="Spell.csv (ID, Description_lang, AuraDescription_lang)")
    ct.add_argument("itemeffect_csv", help="ItemEffect.csv (ParentItemID, LegacySlotIndex, SpellID)")
    ct.add_argument(
        "--itemxitemeffect",
        dest="itemxitemeffect_csv",
        help="ItemXItemEffect.csv: the item an effect belongs to, for a build whose ItemEffect "
        "carries no relationship map and writes ParentItemID 0 on every row (Forever). Omit on a build "
        "that does the join inline (Classic Era ships no such table).",
    )
    ct.add_argument("--build", required=True)
    ct.add_argument("--src", choices=CLIENT_TABLE_SOURCES, default="wago", help=SRC_HELP)
    ct.add_argument(
        "--merge", choices=("replace", "union"), default="replace", help=MERGE_HELP
    )
    ct.add_argument("--dry-run", action="store_true",
                    help="read and join every table, raise on any problem, write nothing (make's preflight)")
    ct.set_defaults(fn=run_client_text)


def _add_draft(sub: Any) -> None:
    """`wfj import draft`: a machine translation batch."""
    dr = sub.add_parser("draft")
    dr.add_argument("type")
    dr.add_argument("file")
    dr.add_argument("--model", required=True)
    dr.add_argument("--critic")
    dr.add_argument("--date", required=True)
    dr.add_argument("--name", required=True)
    dr.add_argument(
        "--reverify",
        action="store_true",
        help="record the current English on each named line (ui, quest, objective, item, spell)",
    )
    dr.set_defaults(fn=run_draft)


def run(argv: Sequence[str]) -> int:
    a = build_parser().parse_args(list(argv))
    try:
        return a.fn(a)
    except (ValueError, OSError) as e:  # OSError: a missing file, or a directory given as a file
        print(f"wfj import: {e}", file=sys.stderr)
        return 1
