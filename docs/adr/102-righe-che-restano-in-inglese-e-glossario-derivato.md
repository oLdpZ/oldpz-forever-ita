# ADR-102: Righe che restano in inglese (`"it": null`) e glossario derivato

- **Status:** Accepted
- **Date:** 2026-10-22
- **Related:** Piano 2, Task 3 / 3b / 3c · [ADR-101](101-niente-controllo-nomi-latini-in-italiano.md) · guida di stile `sg1`

## Contesto

1. Alcune righe di un lotto sono giuste in inglese: un titolo di missione che è solo un nome proprio
   ("Milly Osworth"). Il lint le rifiutava (`not_italian`), quindi il traduttore doveva inventare qualcosa o
   bloccare il lotto; e una riga non tradotta veniva ritagliata da `cut` a ogni giro.
2. Il testo delle missioni usa forme brevi dei nomi ufficiali ("Northshire" per *Northshire Valley*, "the
   Crossroads" per *The Crossroads*). Il glossario ufficiale non le contiene, quindi il lint non chiedeva la
   forma italiana e i nomi uscivano in inglese o inventati.

## Decisione

1. **`{"ref": "…", "it": null}` = la riga resta in inglese.** `translate_lint` la conta come `kept_english`
   (né tradotta né fallita), la conta presente per `missing` / `duplicate` e la scrive in
   `<bozza>.keep.jsonl`; non entra in `.ok.jsonl`, quindi non viene mai importata: nessuna riga in `data/`, il
   client mostra l'inglese come per ogni riga non tradotta. Una riga senza la chiave `it` resta un errore.
2. **La decisione si registra in `pipeline/keep_english.tsv`** (`tipo\tid\tcampo\thash\ten`, nel repo), scritta
   da `translate_batch keep` dentro `lotto importa` (ripristinata con `data/` e `addon/` se un passo fallisce).
   `cut` salta una riga elencata finché l'hash dell'inglese è quello registrato; se una patch cambia
   l'inglese la decisione è scaduta e la riga torna nei lotti. `--redraft` non la salta (la riga è stata
   chiesta per id). Scelto un file a parte invece di una riga di `data/` con uno stato o un *ruling*: lo
   store non ha un modo di dire "questa riga non ha italiano di proposito" senza un testo italiano, e ogni
   regola di `check` presume che una riga ne abbia uno.
3. **Glossario derivato `pipeline/glossario_derivato.tsv`** (`tipo\tid\ten\tit\tda`, curato a mano):
   le forme brevi, ciascuna legata al termine ufficiale da cui deriva (`da`, stesso tipo e id). Un solo
   caricatore (`glossary_it.load_terms`) lo legge dopo il glossario ufficiale per `cut`, il lint,
   `import draft` e `import official`, e rifiuta una riga il cui `da` non è un termine ufficiale o il cui
   italiano non è parte dell'italiano ufficiale: una forma breve si ritaglia dal nome Blizzard, non si
   inventa. `make glossary` lo ricontrolla contro il glossario appena costruito.
4. La guida resta `sg1`: `"it": null` è un chiarimento del formato d'uscita, non una regola di traduzione
   nuova; nessuna bozza va rifatta.

## Conseguenze

- Un nome derivato vale anche dentro nomi di creature o oggetti non nel glossario ("Redridge Brutes",
  "Stonetalon Sap"): il lint chiede `Crestarossa` / `Petrartiglio` nella riga, come fa il client italiano.
- Forme brevi uguali in italiano (Elwynn, Tirisfal, Menethil, Sen'jin) non si elencano; "Bloodhoof" no
  (è anche il cognome di Cairne e Baine), "Ragefire" no (solo nomi di creature).
