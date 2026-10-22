# Collaudo in gioco prima del rilascio

> Da fare quando i server di World of Warcraft: Forever riaprono, sulla versione che stai per pubblicare (lo zip di `make package`, o la cartella `addon/OldpZ_ForeverITA` copiata a mano). Un personaggio **umano nuovo** di livello 1, nella **Contea del Nord** (Northshire) e poi a **Goldshire**. Ogni controllo dice dove andare e cosa deve succedere. Se un controllo fallisce, annota cosa vedi e l'output di `/fita debug` e `/fita log`. La lista completa, più tecnica, è in [Testing strategy](strategy.md); questa è la parte che serve per il rilascio.

## Preparazione

- Nessun altro addon attivo, tranne eventualmente BugSack (aiuta a vedere gli errori Lua).
- Errori Lua visibili: `/console scriptErrors 1`.
- L'addon installato in `World of Warcraft\_forever_\Interface\AddOns\OldpZ_ForeverITA` (una sola cartella, non una dentro l'altra).
- Per un primo avvio "pulito", togli `OldpZ_ForeverITA.lua` da `WTF\Account\<ACCOUNT>\SavedVariables\` (fanne una copia se ti serve).

## Avvio

1. **Elenco degli AddOn.** *Dove:* selezione del personaggio → **AddOns**. *Deve succedere:* c'è **oLd_pZ Forever - Traduzione Italiana** con la sua icona, spuntato, senza "dipendenza mancante" né "non aggiornato".
2. **Entrare senza errori.** *Dove:* entra col personaggio. *Deve succedere:* nessun errore Lua; si apre una volta la finestra di benvenuto in italiano (missioni, dialoghi e tooltip in italiano, tieni premuto Alt, pulsante della minimappa); in chat compare l'avviso della raccolta dei testi inglesi. `/fita debug` stampa `surface errors: none`; `/fita log` stampa `errors: 0 recorded`.
3. **Versione.** *Dove:* `/fita version`. *Deve succedere:* `oLd_pZ Forever - Traduzione Italiana` con la versione che stai pubblicando.
4. **Stato.** *Dove:* `/fita`. *Deve succedere:* l'elenco delle impostazioni con i valori predefiniti (`enabled = on`, `names.style = it`, i due `marker.*` = on).

## Impostazioni

5. **Pagina delle impostazioni.** *Dove:* `/fita config`, poi anche **Esc > Opzioni > AddOn**. *Deve succedere:* si apre la pagina **oLd_pZ Forever - Traduzione Italiana** con le sezioni **Traduzione**, **Cosa tradurre**, **Indicatori**, **Nomi**; sotto ci sono **Raccolta dei testi inglesi** e **Informazioni e aiuto**. Testo leggibile, niente righe sovrapposte o tagliate.
6. **Pulsante nell'elenco degli AddOn.** *Dove:* menu di gioco → AddOns, accanto all'addon. *Deve succedere:* il pulsante **Impostazioni** apre la stessa pagina.
7. **Spegnere e riaccendere.** *Dove:* `/fita off`, apri una finestra di missione, poi `/fita on`. *Deve succedere:* con `off` tutto torna in inglese, con `on` torna l'italiano, senza `/reload`.

## Missioni

8. **Finestra della missione.** *Dove:* parla con **Deputy Willem** davanti all'abbazia e apri **Una minaccia interna** (783). *Deve succedere:* titolo, descrizione e obiettivi in italiano, senza segnaposto tipo `{class}` o `{name}` (al loro posto la tua classe e il tuo nome), nessun indicatore. Nella descrizione si legge **Contea del Nord** e **Roccavento**.
9. **Alt.** *Dove:* la stessa finestra, tieni premuto Alt. *Deve succedere:* torna l'inglese originale; rilascialo e torna l'italiano. Il testo non esce dalla pergamena e lo scorrimento funziona.
10. **Nomi.** *Dove:* `/fita nomi en`, riapri la missione 783; poi `/fita nomi it`. *Deve succedere:* in chat `Nomi: originali inglesi`, nel testo **Northshire** e **Stormwind**; poi `Nomi: italiani ufficiali` e di nuovo **Contea del Nord** e **Roccavento**.
11. **Registro e tracker.** *Dove:* accetta da **Marshal McBride** **Ripulire l'accampamento dei coboldi** (7); apri il registro delle missioni (L). *Deve succedere:* titolo e descrizione in italiano nel registro; la riga dell'obiettivo nel tracker sullo schermo in italiano, e il contatore sale quando uccidi i coboldi.
12. **Avanzamento e completamento.** *Dove:* torna da Marshal McBride con la missione fatta. *Deve succedere:* il testo di avanzamento e quello di completamento in italiano (o in inglese con **[Non tradotto / Not Translated]** se Forever lo ha cambiato: annotalo), ricompense e pulsanti al loro posto.

## Dialoghi dei PNG

13. **Una guardia.** *Dove:* parla con una guardia (per esempio una **Stormwind Guard** a Goldshire). *Deve succedere:* saluto e opzioni in italiano, nessuna riga sovrapposta; Alt mostra l'inglese.
14. **Un locandiere.** *Dove:* **Innkeeper Farley** al Lion's Pride Inn di Goldshire. *Deve succedere:* saluto e opzioni (per esempio impostare la locanda come casa) in italiano; le opzioni funzionano come prima.
15. **Frasi in chat e urla.** *Dove:* resta vicino ai PNG che parlano da soli (all'abbazia o a Goldshire) o combatti un nemico che parla. *Deve succedere:* le frasi dei PNG in chat (dice / urla) e nei fumetti in italiano, con il nome del PNG come lo mostra il gioco.

## Tooltip, libri, interfaccia

16. **Tooltip di un oggetto.** *Dove:* borse, passa sopra un oggetto con una descrizione o un effetto (per esempio una ricompensa di missione, un cibo o una bevanda). *Deve succedere:* la descrizione in italiano dove esiste il testo ufficiale, i valori del gioco al loro posto; Alt mostra l'inglese.
17. **Tooltip di un'abilità.** *Dove:* libro delle abilità (P) e barra delle azioni, passa sopra la prima abilità della classe. *Deve succedere:* descrizione in italiano con i numeri veri del gioco; Alt mostra l'inglese.
18. **Un libro resta in inglese.** *Dove:* apri un libro, una targa o una lettera nel gioco. *Deve succedere:* il testo resta in inglese, senza errori; con **Libri e lettere** spento non cambia nulla.
19. **Interfaccia.** *Dove:* apri borse, personaggio (C), libro delle abilità, mappa e menu di gioco. *Deve succedere:* titoli e pulsanti tradotti dove c'è il testo ufficiale, nessuna scritta che esce dal pulsante.

## Indicatori e raccolta

20. **Indicatore "non tradotto".** *Dove:* una riga senza traduzione: un dialogo o un testo di consegna nuovo, o `/fita debug ui scan` per trovare testo inglese visibile. *Deve succedere:* la riga resta in inglese con **[Non tradotto / Not Translated]** in oro; `/fita marker missing off` lo nasconde, `/fita marker missing on` lo rimette.
21. **Raccolta.** *Dove:* dopo aver visto una riga non tradotta, `/fita collector status`. *Deve succedere:* il numero di voci è salito; `/fita collector path` mostra dove si trova il file.
22. **Invio della raccolta.** *Dove:* `/fita collector send` (o **Invia l'inglese** nella pagina **Raccolta dei testi inglesi**). *Deve succedere:* si apre la finestra **Invia l'inglese raccolto** con il riepilogo e il testo da copiare (non c'è ancora un link a un modulo); **L'ho inviato** segna le righe come inviate.
23. **Segnalare una riga.** *Dove:* clic sinistro sul pulsante della minimappa (o `/fita fix`). *Deve succedere:* la finestra **Segnala una traduzione** elenca le righe appena viste; scegline una, scegli cosa non va, **Salva**; in **Invia segnalazione** c'è il testo che inizia con `OFI-REPORT 1`, che si seleziona con un clic.
24. **Segnalare un errore.** *Dove:* `/fita bug`, oppure clic destro sul pulsante della minimappa → **Segnala errore o idea**. *Deve succedere:* la finestra **Segnala un errore o un'idea** con build e versione; la scheda **Proposta** cambia il testo.

## Ricaricare e combattere

25. **`/reload`.** *Dove:* cambia un'impostazione (per esempio `/fita nomi en`), poi `/reload`. *Deve succedere:* nessun errore Lua, la finestra di benvenuto non si riapre, l'impostazione è rimasta; `/fita collector status` ha ancora le voci di prima. Rimetti `/fita nomi it`.
26. **Combattimento.** *Dove:* combatti qualche coboldo usando la barra delle azioni, passando sopra le abilità e tenendo premuto Alt. *Deve succedere:* nessun messaggio "azione bloccata" o "interfaccia bloccata da un addon", la barra delle azioni funziona; `/fita taint` stampa `0 tainted fields, 0 globals`.
27. **Dopo il combattimento.** *Dove:* finito il combattimento, passa sopra un tuo buff sotto la minimappa. *Deve succedere:* il tooltip torna in italiano (in combattimento può restare in inglese: è normale).
28. **Uscita.** *Dove:* esci dal gioco e rientra. *Deve succedere:* nessun errore; `/fita log` non ha errori nuovi; `/fita debug` stampa la memoria (annotala) e nessuna superficie in errore.

## Esito

Annota per ogni numero: ok, oppure cosa hai visto. Se tutto è ok, la versione si può pubblicare ([Release](../operations/release.md)).
