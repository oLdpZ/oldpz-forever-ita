# ADR-105: Titoli, obiettivi e nomi dei PNG in italiano dentro Questie

- **Status:** Accepted
- **Date:** 2026-11-06
- **Related:** [ADR-103](103-npc-names-in-the-world.md) (nomi dei PNG) · `UI/Questie.lua` · Questie 12.6.2,
  `Localization/l10n.lua` e `docs/adr/0003-external-locale-addons-through-provider-corrections.md`

## Contesto

1. Questie è l'aiuto per le missioni più usato su Classic e ha una versione per Forever. Prende titoli,
   obiettivi e nomi dal proprio database inglese: con Questie attivo il suo tracker, i segnalini della mappa e
   le righe che aggiunge ai tooltip restano in inglese anche dove l'addon ha la traduzione.
2. Questie legge una variabile globale, `QUESTIE_LOCALES_OVERRIDE`, che gli addon di traduzione esterni
   riempiono (la usa per esempio la traduzione ucraina): una lingua, le scritte della sua interfaccia e,
   per id, titoli e obiettivi delle missioni, nomi di PNG, oggetti e oggetti del mondo. La legge una volta
   all'accesso, dopo gli `ADDON_LOADED`; un campo mancante torna all'inglese del suo database.
3. Questie riconosce una missione nei dialoghi confrontando il titolo che dà il client (inglese) con il
   titolo del suo database (`QuestieDB.GetQuestIDFromName`): con i titoli in italiano quel confronto fallisce
   e l'icona della missione nel dialogo torna quella generica.

## Decisione

1. **L'addon riempie `QUESTIE_LOCALES_OVERRIDE`** (lingua `itIT`, nome `Italiano`) solo se nessun altro addon
   l'ha già fatto. Pubblica titolo e obiettivi delle missioni (un obiettivo per riga) e nome e sottotitolo dei
   PNG, dalle stesse righe che l'addon mostra (Core/Lookup), con i nomi marcati nella forma scelta in
   `names.style`. I PNG seguono UnitNames: nessuno con `names.style` = "en".
2. **Un testo con un segnaposto** (`$N1`, `{name}`) non si pubblica: Questie non ha il valore vivo per
   riempirlo e mostra il suo inglese.
3. **Le scritte dell'interfaccia di Questie restano inglesi** (`translations` vuoto): sono migliaia, si
   vedono meno, e il loro testo cambia a ogni versione di Questie.
4. **Il confronto dei titoli si riprova in italiano**: quando Questie carica, l'addon avvolge
   `QuestieDB.GetQuestIDFromName`; se il titolo inglese non trova nulla, riprova con i titoli italiani delle
   missioni la cui impronta inglese (h1) è quella del titolo chiesto.

## Conseguenze

- Con Questie attivo tracker, mappa, diario e tooltip di Questie mostrano titoli, obiettivi e nomi in
  italiano. Le righe di avanzamento del suo tracker ("3/8 Wolf slain") vengono dall'API del client e restano
  inglesi; oggetti e oggetti del mondo non sono pubblicati (l'addon li ha per testo inglese, non per id).
- Cambiare `names.style` vale per Questie dal prossimo accesso o `/reload`: Questie legge le tabelle una volta.
- Se Questie cambia il contratto della variabile, la traduzione dentro Questie si spegne e Questie torna
  all'inglese: l'addon non tocca altro di Questie oltre a `GetQuestIDFromName`.
