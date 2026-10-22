# Primo import dei testi ufficiali (pacchetto 0.1.0)

> Come è stato fatto il primo import dei testi italiani ufficiali di Blizzard, con quali build e con quali numeri.
> Rifare gli stessi passi a ogni nuova build retail o Forever.

## Build usate

| Cosa | Build | Dove |
|---|---|---|
| Tabelle retail enUS + itIT (wago.tools) | `12.1.5.70448` (`RETAIL_BUILD`) | `inputs/clients/retail-12.1.5.70448/`, timbro `wago@12.1.5.70448` |
| Tabelle dei nomi Forever (glossario) | `1.60.1.70532` (`FOREVER_WAGO_BUILD`) | `inputs/clients/forever-names-1.60.1.70532/` |
| Inglese di Forever in `data/english/` | `db2@1.60.1.70450` (già committato) | `data/english/` |

`inputs/` è ignorato da git: le tabelle si riscaricano con `make wago-fetch-retail` e `make wago-fetch-forever-names`.
La data `imported` delle righe ufficiali è fissata nel Makefile (`RETAIL_DATE`, 2026-10-21) insieme alla build,
così un nuovo import sugli stessi input dà le stesse righe.

## Comandi eseguiti

Le tabelle retail erano già scaricate e timbrate alla build giusta, quindi il download è stato saltato.

```sh
make import-official      # testi itIT → data/ (varianti `official`), poi check
make generate             # data/ → Data/*.lua dell'addon
make coverage             # docs/operations/coverage.md e i conteggi in README.md / docs/curseforge.md
make stats
grep -R '\$s[0-9]' addon/OldpZ_ForeverITA/Data   # nessun risultato: nessun codice $s grezzo spedito
bash scripts/wsl-make.sh test lint toc-check validate
make package VERSION=0.1.0
```

`make data` (import → check → generate) ora esegue anche l'import ufficiale: `make import` lo lancia per ultimo,
dopo l'import inglese e il passo `served`.

## Contatori di `OfficialReport`

| Tipo | accettate | inglese diverso | specificatori | markup | ordine argomenti | ambigue | slot | non contabili | uguale all'inglese | senza italiano |
|---|---|---|---|---|---|---|---|---|---|---|
| ui | 8609 | 353 | 0 | 43 | 8 | 289 | – | – | 111 | 0 |
| item | 1232 | 296 | – | – | – | – | 1 | 0 | 1 | 2825 |
| spell | 4863 | 2728 | – | – | – | – | 146 | 2 | 12 | 135 |

- **inglese diverso**: il retail ha riscritto il testo; l'ID da solo non basta, la riga resta inglese.
- **ordine argomenti** (`rejected_order`): due `%s` di testo libero separati solo da uno spazio, scambiati
  nell'italiano: l'addon li divide in modo pigro e i valori finirebbero l'uno al posto dell'altro.
- **ambigue** (`rejected_ambiguous`): più chiavi con lo stesso inglese ma italiano diverso (`All` → `Tutto` /
  `Tutte`). L'addon trova la stringa dal suo inglese e potrebbe mostrarne una sola per tutte, con il genere o il
  numero sbagliato su alcune: quindi non ne spedisce nessuna e il gruppo resta in inglese. Sono 289 chiavi in 98
  gruppi, elencate una per riga (`english`, `key`, `italian`) in `pipeline/ui_ambiguous.tsv`, che l'import
  riscrive: una decisione futura sceglierà un italiano per ogni inglese. I gruppi in cui tutte le chiavi hanno
  lo stesso italiano si spediscono normalmente.
- **senza italiano**, oggetti (2825): rimisurato. In tutti i 2825 casi il retail ha la descrizione vuota in
  **entrambe** le lingue: Blizzard ha tolto il testo di colore da quegli oggetti, non manca una traduzione.

## `wfj stats` (riassunto)

| Tipo | campo | righe | trusted | unaligned | spedite |
|---|---|---|---|---|---|
| ui | text | 8609 | 8609 | 0 | 8609 (tutte `official`) |
| item | description | 1232 | 0 | 1232 | 1232 (tutte `official`) |
| spell | description | 2896 | 0 | 2896 | 2896 |
| spell | aura | 1967 | 0 | 1967 | 1967 |

Missioni, obiettivi, dialoghi (gossip: 10965 chiavi con inglese), libri e zone: 0 righe italiane. `generate`
scrive 8609 stringhe UI, 1232 oggetti e 3761 incantesimi (descrizione e aura dello stesso incantesimo insieme).

## Verifica a campione

Dieci righe a caso per tipo lette a mano: italiano sensato e coerente con l'inglese. Esempi:

- UI: `Non puoi usare oggetti se hai mutato forma.`, `%s è stato aggiunto al gruppo attraverso una pietra del ritrovo.`,
  `Informazioni sulla barra di lancio`, `Acquistato da %s`, `Sconosciuto`.
- Oggetti: `Proprietà della Fiera di Lunacupa.`, `Ti insegna a cucinare un Branzino Piccante Affumicato.`,
  `La superficie è ricoperta da rune oscure.`, `Lascerai i tuoi avversari senza parole.`,
  `Ti insegna a evocare questa mascotte.`
- Incantesimi: `Assorbe $N1 danni da natura. Dura $D1.`, `Probabilità di schivata aumentata del $N1%.`,
  `$N1 danni da natura inflitti ogni $N2 s.`, `Infligge $N1 danni da fuoco ai nemici in un cono frontale.`, `Stordito.`

I codici del client (`$s1`, `$d`) sono tutti convertiti nei segnaposto dell'addon (`$N1`, `$D1`).

## Da guardare in gioco (Piano 3)

- `ui_lint --shipped` segnala 1173 stringhe più larghe di 1,25 volte l'inglese (`too_wide`, solo avviso; 0
  errori): l'italiano è più lungo e in pulsanti o etichette strette potrebbe uscire dal riquadro. Diverse etichette
  brevi sono lunghe almeno il doppio dell'inglese (`Inbox` → `Posta in arrivo`, `IM Style` → `Stile messaggi
  istantanei`, `Axes Skill` → `Competenza con le asce`). Non corretto qui.
- Le descrizioni degli oggetti con effetti *Uso:* / *Equipaggiato:* restano inglesi (vedi le regole del Task 9).
