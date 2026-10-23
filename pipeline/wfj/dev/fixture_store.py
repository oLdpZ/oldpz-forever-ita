"""Write the Italian fixture store the tests use while the committed `data/` holds no translation yet.

    python -m wfj.dev.fixture_store

`tests/fixtures/it-store/data/` gets a few hand-written Italian lines (quest 2, 7, 791 and 8234, item 117,
spells 133 and 1229741, two gossip keys, a handful of interface keys) with their English copied from this
repository's `data/english/`; `tests/fixtures/it-store/addon/` gets the shards `wfj generate` makes from them
and `files.txt`, their TOC order, which the Lua specs load in place of the addon's own generated block
(`Loader.load(name, { data = … })`). tests/python/test_fixture_store.py fails when the committed files
differ from a regeneration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wfj.cmd import generate
from wfj.io.jsonl_store import Store

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "tests" / "fixtures" / "it-store"

QUEST = {
    2: {
        "title": "L'artiglio di Sharptalon",
        "objectives": "Porta l'Artiglio di Sharptalon a Senani Thunderheart, allo Splintertree Post di "
                      "Valtetra.",
        "description": "Il potente ippogrifo Sharptalon è stato ucciso, e l'artiglio della bestia abbattuta "
                       "è la prova della tua vittoria. Senani Thunderheart, allo Splintertree Post, vorrà di "
                       "certo vedere questo trofeo come prova delle tue gesta.",
        "progress": "Sì, potente {class}, ho percepito il tuo arrivo. Hai altre notizie da riferirmi sulla "
                    "caccia?",
        "completion": "Davvero notevole, {name}... l'artiglio di Sharptalon non dev'essere stato facile da "
                      "ottenere! La Caccia di Valtetra ti sorride!\n\nSharptalon terrorizzava da tempo i "
                      "peoni dei campi di taglialegna lungo il suo cammino verso lo Splintertree Post. "
                      "Quando si saprà che hai abbattuto tu la bestia, molti canti sul tuo coraggio "
                      "risuoneranno intorno ai fuochi e nelle segherie di tutta Valtetra!",
    },
    7: {
        "title": "Ripulire il campo dei Coboldi",
        "objectives": "Uccidi 10 Coboldi Infestanti, poi torna da Marshal McBride.",
        "description": "Il tuo primo compito è fare pulizia, {name}. Un clan di coboldi ha infestato i "
                       "boschi a nord. Vai là e combatti i coboldi infestanti che trovi. Riduci il loro "
                       "numero, così un giorno potremo cacciarli da Northshire.",
        "progress": "Come procede la caccia, {name}? Hai trovato e sconfitto quei parassiti?",
        "completion": "Ben fatto, cittadino. Quei coboldi sono ladri e codardi, ma in gran numero sono una "
                      "minaccia per noi. E gli umani di Roccavento non hanno bisogno di un'altra minaccia."
                      "\n\nPer averli sconfitti, hai la mia gratitudine.",
    },
    791: {
        "completion": "Eccellente, {name}. Qualunque buon {class} troverà di certo un uso per questa borsa "
                      "sul campo di battaglia.\n\nSaluto il tuo vigore e la tua volontà di morire nel nome "
                      "dell'Orda!",
    },
    8234: {
        "title": "Borsa azzurra sigillata",
        "completion": "Vedo che hai la borsa di Lord Ravenholdt. Perché non l'hai detto subito, giovane?",
    },
}
ITEM = {117: {"description": "Ripristina $N1 punti Salute in $D1. Devi restare seduto mentre mangi."}}
_N = "\r\n\n"
SPELL = {
    133: {
        "description": "Scaglia una palla infuocata che infligge $N1 danni da Fuoco e altri $N2 danni da "
                       "Fuoco in $D1.",
        "aura": "$N1 danni da Fuoco ogni $N2 secondi.",
    },
    1229741: {
        "aura": "Hai ottenuto i seguenti benefici dell'accampamento:" + _N
        + "$?a1230587[Mana Well: ripristina $N1 Mana ogni $N2 secondi." + _N + "][]"
        + "$?a1230172[Sharpening Wheel: Forza aumentata di $N3." + _N + "][]"
        + "$?a1230653[Enchanted Lute: Armatura aumentata di $N4, tutte le caratteristiche aumentate di $N5 "
          "e tutte le resistenze aumentate di $N6." + _N + "][]"
        + "$?a1230124[First Aid Kit: Tempra aumentata di $N7." + _N + "][]"
        + "$?a1230098[Fish Bowl: tutte le caratteristiche aumentate del $N8%." + _N + "][]"
        + "$?a1229513[Incense Candle: Intelletto aumentato di $N9." + _N + "][]"
        + "$?a1230164[Lodestone: Potere d'attacco in mischia aumentato di $N10." + _N + "][]"
        + "$?a1229519[Camp Chair: probabilità di critico di tutti gli incantesimi e attacchi aumentata del "
          "$N11%." + _N + "][]"
        + "$?a1229718[Faction Banner: Spirito aumentato di $N12.][]",
    },
}
GOSSIP = {"0001ce030c010973": "Sergra cade in trance per un momento, poi guarda il cielo.",
          "3360566d1f7995c8": "Fai di questa locanda la tua casa."}
UI = {
    "ABANDON_QUEST": "Abbandona missione", "ACCEPT": "Accetta", "BACK": "Indietro", "CANCEL": "Annulla",
    "CLOSE": "Chiudi", "COMPLETE": "Completa", "CONTINUE": "Continua", "DECLINE": "Rifiuta",
    "DONE": "Fatto", "EXIT": "Esci", "GOSSIP_OPTION_PREPEND": "|cnPURE_BLUE_COLOR:%s|r %s",
    "INT_SPELL_DURATION_MIN": "%d min", "INT_SPELL_DURATION_SEC": "%d s",
    "ITEM_SPELL_TRIGGER_ONEQUIP": "Equipaggiato:", "LEVEL": "Livello", "NAME": "Nome", "OKAY": "Va bene",
    "QUEST_LOG": "Registro delle missioni", "QUEST_PREPEND": "(Missione)", "REWARDS": "Ricompense",
    "SELL_PRICE": "Prezzo di vendita", "YES": "Sì",
    "ItemSubClass:4:1": "Stoffa",  # a client-table key: the index finds it by its English fingerprint
}
UNIT = {12696: {"name": "Senani Cuore Tonante"}, 15006: {"subname": "Maestro di battaglia del Bacino Arathi"}}
STATUS = {"quest": "trusted", "item": "unaligned", "spell": "unaligned", "gossip": "trusted", "ui": "trusted",
          "unit": "trusted"}


def _prov(type_: str) -> dict[str, Any]:
    name = "ui-fixture" if type_ == "ui" else f"{type_}-fixture-sg1"
    return {"class": "machine", "model": "fixture-model", "source": f"draft-{name}@2026-10-21",
            "imported": "2026-10-21"}


def _lines(
    type_: str, english: list[dict[str, Any]], wanted: dict[Any, dict[str, str]]
) -> list[dict[str, Any]]:
    by = {(ln["id"], ln["field"]): ln for ln in english}
    out = []
    for id_, fields in wanted.items():
        for field, it in fields.items():
            en = by[(id_, field)]
            out.append({"id": id_, "field": field, "it": it, "status": STATUS[type_], "checks": [],
                        "provenance": _prov(type_), "english": {"hash": en["hash"], "src": en["src"]},
                        "reasons": [], "conflicts": []})
    return out


def write(repo: Path = REPO, fixture: Path = FIXTURE) -> None:
    src = Store(repo / "data", english=True)
    data = fixture / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "SCHEMA").write_text((repo / "data" / "SCHEMA").read_text(encoding="utf-8"), encoding="utf-8")
    # generate reads the allowlist beside the store (`<data>/../pipeline/allowlist.txt`) for branch lines
    (fixture / "pipeline").mkdir(exist_ok=True)
    allowlist = (repo / "pipeline" / "allowlist.txt").read_bytes()
    (fixture / "pipeline" / "allowlist.txt").write_bytes(allowlist)
    wanted = {"quest": QUEST, "item": ITEM, "spell": SPELL,
              "gossip": {k: {"text": v} for k, v in GOSSIP.items()},
              "ui": {k: {"text": v} for k, v in UI.items()}, "unit": UNIT}
    for type_, rows in wanted.items():
        ids = set(rows)
        english = [ln for ln in src.load(type_) if ln["id"] in ids]
        Store(data, english=True).save(type_, english)
        Store(data).save(type_, _lines(type_, english, rows))
    planned = generate.plan(Store(data), generate.vectors_rows(repo / "data"), {})
    addon = fixture / "addon"
    for rel, text in planned.items():
        path = addon / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    files = "".join(f + "\n" for f in generate.toc_files(planned))
    (addon / "files.txt").write_text(files, encoding="utf-8")


def main() -> int:
    write()
    print(f"wrote {FIXTURE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
