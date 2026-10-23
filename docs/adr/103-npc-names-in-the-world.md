# ADR-103: Nomi dei PNG in italiano nel mondo di gioco; Wowhead ammesso solo per i nomi delle creature

- **Status:** Accepted
- **Date:** 2026-10-23
- **Amends:** [ADR-055](055-forever-vo-captures-as-an-english-source.md) (l'elenco delle fonti escluse: Wowhead) e le righe di `docs/legal/licensing.md` e `docs/glossary.md` che vietano Wowhead; la guida di stile passa a `sg14`.
- **Related:** spec `docs/superpowers/specs/2026-10-23-nomi-png-design.md` (§5, §5b) · [ADR-102](102-righe-che-restano-in-inglese-e-glossario-derivato.md)

## Contesto

1. Missioni, dialoghi e tooltip sono in italiano, ma i PNG nel mondo (tooltip dell'unità, riquadro del
   bersaglio, targhette) restano in inglese: il nome sopra la testa non coincide con quello che il giocatore
   legge nel testo. Il confronto con QuestIT-Forever 0.9.4, che traduce questi nomi, ha reso evidente la
   mancanza.
2. Le tabelle del client retail itIT (`Creature.db2`) coprono soprattutto mascotte, cavalcature ed
   evocazioni. Quasi tutti gli altri PNG hanno una forma ufficiale solo su Wowhead in italiano (endpoint dei
   tooltip, `locale=9`). Senza quella fonte la maggior parte dei nomi ufficiali andrebbe inventata.
3. Finora il progetto non usava Wowhead (i suoi termini lo vietano come fonte di dati) e la guida teneva
   inglesi cognomi, nomi composti e creature negli obiettivi.

## Decisione

1. **Nuovo tipo di dato `unit`**, con campi `name` e `subname` (il sottotitolo `<Venditore di armi>`), per id
   di creatura. Segue il flusso degli altri tipi: file in `data/`, generati in `addon/.../Data/` da
   `make generate`, lint e controlli, traduzioni nostre a lotti (`scripts/lotto.sh`).
2. **Tre fonti, in quest'ordine:** (a) forma ufficiale dalle tabelle itIT (`Name_lang` / `Title_lang`, stesso
   id e stesso nome inglese); (b) forma ufficiale da Wowhead in italiano; (c) traduzione nostra, nello stile
   di Blizzard, per i PNG senza forma ufficiale. La forma ufficiale vince sempre. Un nome puro senza forma
   ufficiale (Hogger) resta com'è.
3. **Wowhead è ammesso solo per i nomi delle creature**, salvo questa eccezione resta vietato come fonte (di
   testi, oggetti, abilità, missioni). Le richieste sono distanziate, una tantum, solo per gli id che servono,
   con una cache locale; il grezzo scaricato non si committa, solo la coppia id → nome usata. Il proprietario
   ha confermato sapendo che le coppie finiranno nello zip e nel repository pubblico.
4. **Superfici:** prima riga del tooltip dell'unità (con sottotitolo), riquadro del bersaglio (anche focus,
   bersaglio del bersaglio, boss), targhette. L'identità è l'id della creatura preso dal GUID, confermato
   dal nome inglese mostrato: se non coincide, non si tocca. Solo post-hook, niente sostituzione di funzioni
   Blizzard; un nome *secret* resta com'è; i giocatori non si toccano mai. `/fita nomi en` ripristina
   l'inglese.
5. **Ripiego in combattimento:** se riscrivere le targhette in combattimento risulta rischioso, restano
   inglesi durante il combattimento e tornano italiane a combattimento finito. Si attiva solo se serve.
6. **Guida `sg14`:** nuova regola «Nomi dei PNG» (nome ufficiale itIT se esiste, anche per i nomi propri;
   altrimenti la forma della tabella `unit`; stessa forma negli obiettivi). Sostituisce le righe che tenevano
   inglesi i nomi delle creature. `tooltip_line_kinds.txt`: `UnitName` passa da `english` a `italian`.
7. **Un solo rilascio coerente:** i nomi nel mondo escono nella stessa versione che riallinea i nomi dei PNG
   negli obiettivi, nel tracker, nel testo delle missioni e nella riga «0/4 X slain», così il giocatore non
   vede mai due nomi per lo stesso PNG. Dialoghi e libri possono seguire.

## Conseguenze

- Le tre righe che vietavano Wowhead (`licensing.md`, `glossary.md`, ADR-055) diventano «salvo i nomi delle
  creature, ADR-103»; il divieto resta per ogni altro uso.
- Le bozze fatte con `sg13` che nominano PNG con nomi propri inglesi vanno riallineate (fase 2); la guida
  nuova è una nuova versione, quindi i nomi delle bozze finiscono con `-sg14`.
- Le coppie id → nome da Wowhead entrano in `data/unit` e nello zip del rilascio.
- Plater, ElvUI e simili che sostituiscono targhette e riquadri non sono coperti in questa fase.
- I nomi dei PNG nel mondo (tooltip dell'unità, riquadri del bersaglio, targhette) passano per l'area «ui»:
  con l'area «ui» spenta il mondo mostra i nomi inglesi, mentre i marcatori nel testo delle missioni seguono
  solo `/fita nomi`. Con «ui» spenta e `/fita nomi it` lo stesso PNG può quindi leggersi inglese sulla
  targhetta e italiano nel testo: è una scelta del giocatore, non un difetto dei dati.
- Un PNG, un nome: i nomi con lo stesso inglese escono con una sola forma (quella ufficiale, altrimenti la più
  comune) e ogni marcatore nel testo porta quella forma. `python -m wfj.dev.remark_names` uniforma le bozze
  machine e riscrive i marcatori superati; `wfj validate` rifiuta i dati dove non vale (due forme ufficiali o
  umane diverse per lo stesso inglese chiedono una decisione a mano).
- **Vincolo di rilascio:** la prova in gioco del Task 12 (taint con boss e istanze: `/fita taint` dopo un
  combattimento con le targhette visibili, un'istanza con le targhette amiche proibite, un PNG rinominato) è
  un cancello obbligatorio: nessun rilascio con i nomi nel mondo prima che passi.

## Alternative scartate

- **Solo le tabelle itIT.** Coprono una minoranza dei PNG; il resto andrebbe inventato o lasciato inglese.
- **Tradurre tutto noi.** Contraddice l'obiettivo: dove esiste una forma ufficiale deve vincere.
- **Intercettare i nomi con sostituzione di funzioni Blizzard.** Rischio di taint in combattimento e in istanza.
