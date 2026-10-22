# ADR-101: Niente controllo dei "nomi latini" in italiano; l'allineamento guarda solo i numeri

- **Status:** Accepted
- **Date:** 2026-10-21
- **Amends:** [ADR-007](007-unaligned-ships-with-runtime-gate.md) (il cancello di allineamento a runtime) e la regola dei nomi di `core/status.py` (regola 5 della tabella delle decisioni).
- **Related:** Piano 1, Task 5 e Task 10 (glossario ufficiale EN→IT)

## Contesto

L'addon giapponese da cui deriviamo controllava ogni riga tradotta così: le parole in alfabeto latino dentro il testo giapponese erano nomi propri lasciati in inglese ("Silverwind Refugeに…"), e ognuna doveva comparire nell'inglese della stessa riga. Se mancava, la riga era rifiutata (`alignment_failed:<nome>`) offline (`align.check_names`, chiamato da `status._evaluate`) e a runtime (`Align.checkNames`, chiamato da `Align.check`); lo stesso controllo distingueva le varianti di una riga a rami (`align.indistinguishable`, `Align.checkVariants`).

In italiano ogni parola è latina. Con quel controllo "Porta 8 Pelli di Lupo a Roccavento." contro "Bring 8 Wolf Pelts to Stormwind." viene rifiutata per `Porta`, `Pelli`, `Lupo` e `Roccavento`: nessuna riga italiana passerebbe. Un elenco di parole ammesse non basta, perché dovrebbe contenere tutto il vocabolario italiano, e i nomi tradotti (Roccavento per Stormwind) per definizione non sono nell'inglese.

## Decisione

1. **`check` non legge più i nomi.** `status._evaluate` non chiama `align.check_names` e non scrive più `names` in `checks`; `Align.check` non chiama `Align.checkNames`. Il controllo dei numeri (`check_numbers` / `Align.checkNumbers`) resta identico: "Porta 9 …" contro "Bring 8 …" è ancora rifiutata (`numbers_changed:9`), e a runtime l'inglese resta.
2. **Le varianti a rami si distinguono per forma, numeri o chiave.** `align.indistinguishable` (lato italiano) e `Align.checkVariants` non usano più i nomi. Due varianti che differiscono solo per un nome ora si fanno ombra; la pipeline le spedisce solo con le chiavi di variante ([ADR-064](064-aura-inclusions-list-tails-and-variant-keys.md)), altrimenti la riga resta in inglese. Meglio inglese che il ramo sbagliato.
3. **Le funzioni restano, inattive.** `check_names` / `latin_names`, `Align.checkNames` / `Align.names`, `pipeline/allowlist.txt` e `Align.ALLOWLIST` restano gemelli e provati dai vettori (`vectors/align_vectors.*`), ma il cancello non li chiama. Il parametro `allowlist` di `decide` e `indistinguishable` resta per non cambiare i chiamanti e non viene letto.
4. **La coerenza dei nomi la garantisce il glossario.** Che "Stormwind" diventi sempre "Roccavento" non è un controllo sulla singola riga contro il suo inglese, ma sul lessico: lo verifica il lint del glossario ufficiale EN→IT (Task 10), costruito dai testi Blizzard itIT.

## Conseguenze

- Una traduzione che inventa o sbaglia un nome non è più fermata dall'allineamento; fino al Task 10 nessun controllo automatico la ferma.
- Le righe a rami che differiscono solo per un nome richiedono le chiavi di variante.
- Cambiano i test upstream che si basavano sui nomi (decisioni di stato, conflitti, varianti): ora usano numeri.
