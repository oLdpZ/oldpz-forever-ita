# ADR-106: L'inglese raccolto dal progetto giapponese come fonte aggiuntiva

- **Status:** Accepted
- **Date:** 2026-11-26
- **Related:** [ADR-019](019-quest-english-per-field-and-live-check.md) (VMaNGOS) · ADR-033 (passo served) ·
  `pipeline/wfj/cmd/import_english.py` (`run_upstream`) · `pipeline/upstream-source.txt`

## Contesto

1. Le nostre scansioni dell'inglese di Forever sono parziali: la cache delle missioni, le tabelle del client e le
   registrazioni di forever-vo non coprono tutto quello che il gioco mostra. Dove manca l'inglese, la riga non
   si può né allineare né tradurre.
2. Il progetto giapponese da cui discende questo repository continua a raccogliere testi (missioni, dialoghi,
   libri) con le proprie scansioni e con il database di VMaNGOS. Parte di quell'inglese ci manca.
3. Quel progetto contiene anche la sua traduzione giapponese e dati di unit e aree con uno schema diverso dal
   nostro: non servono e non vanno importati.

## Decisione

1. **Nuova fonte `import english upstream`**, da un clone del progetto giapponese fissato a un commit
   (`UPSTREAM_SHA`, release 0.15.0 = `065ac52d`). L'importatore rifiuta un clone il cui `HEAD` non inizia con
   `--commit`. Lo SHA del clone va in `pipeline/upstream-source.txt` (`wfj-upstream <sha>`).
2. **Solo additivo.** Non sostituisce né cancella mai una riga esistente. Una chiave (tipo, id, campo) che
   abbiamo già con un inglese diverso si **riporta** in `pipeline/upstream-conflicts.tsv`
   (`tipo`, `id`, `campo`, `nostro`, `loro`) e non si scrive.
3. **`src` originale.** La riga importata conserva il `src` upstream (`wdb@…`, `collector@…`, `vmangos@…`): è
   la vera origine, e il passo served la tratta come le righe nostre.
4. **Solo quest, gossip, obiettivi e libri.** Unit e aree non si importano. **La traduzione giapponese non si
   legge mai.** Campi ammessi: `id, field, en, hash, src` (+ `npcs` per il gossip).
5. **Hash ricalcolato:** `hash_key(normalize_for(type_, en))`. Per il gossip l'id è l'hash: se il ricalcolo
   differisce dall'id upstream, la riga si salta e si conta.
6. **Segnaposto scartati:** un titolo segnaposto, o un campo che contiene `temp text`, `<CHANGE TO GOSSIP>` o un
   `TEST` iniziale, scarta l'intera missione (tutti i suoi campi).
7. **Posizione nella pipeline:** `make import-upstream` gira subito prima del passo served in `import`,
   `import-english` e `import-forever`. Se il clone (`UPSTREAM`, `$(INPUTS)/wfj-upstream`) non c'è, stampa un
   avviso ed esce con 0: le altre fonti non dipendono da lui.

## Conseguenze

- Rilanciare a ogni release del progetto giapponese: alzare `UPSTREAM_SHA` e riportare il clone a quel commit.
- I conflitti si rivedono a mano in `pipeline/upstream-conflicts.tsv` (file generato, non è una decisione).
- Le righe importate che nessun Forever serve vengono tolte dal passo served come ogni altra riga.
- L'inglese è testo Blizzard: non entra mai nell'addon (vedi ATTRIBUTION.md).
- Le righe importate tengono il `src` di upstream (`wdb@…`, `collector@…`) e da quel momento non si distinguono più dalle nostre; `pipeline/upstream-source.txt` dice solo quale commit è stato letto, non quali righe ne vengono.
- Alzare `UPSTREAM_SHA` aggiunge soltanto le chiavi che mancano: non corregge mai una riga importata prima. Le correzioni che upstream fa in seguito a righe già importate riappaiono come conflitti in `pipeline/upstream-conflicts.tsv`, da rivedere a mano.
- `make rebuild-check` tratta le righe `collector@` di upstream come già registrate: `reset_english` le tiene come quelle raccolte da noi, e il passo upstream le ritrova.
