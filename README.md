> **oLd_pZ Forever - Traduzione Italiana** è basato su [WoW Forever Japanese](https://github.com/zyaga/wow-forever-japanese) di Zyaga (GPL-2.0-or-later), commit 1578af4b. Questo fork è distribuito con la stessa licenza.

# oLd_pZ Forever - Traduzione Italiana

Un addon che mostra World of Warcraft: Forever in italiano: missioni, dialoghi dei PNG, obiettivi, tooltip di
oggetti e abilità e i testi dell'interfaccia. Tieni premuto **Alt** e torna l'inglese originale del gioco; rilascialo
e torna l'italiano. Alt è solo il tasto predefinito: puoi sceglierne un altro.

I nomi di luoghi, personaggi, fazioni, oggetti e abilità usano i nomi italiani ufficiali di Blizzard (Roccavento,
non Stormwind). Se preferisci i nomi inglesi, per parlare con gli altri giocatori o seguire le guide, basta un
comando: `/fita nomi en`.

Funziona solo con **World of Warcraft: Forever**. Non è per WoW Classic né per il gioco attuale.

## Cosa traduce

| | In italiano |
|---|---|
| Missioni | 4.775 |
| Righe di dialogo dei PNG | 10.909 |
| Pagine di libri | 925 |
| Pagine di lettere | 208 |
| Tooltip degli oggetti | 10.479 |
| Tooltip delle abilità | 20.007 |
| Testi dell'interfaccia | 15.271 |

- **Missioni** dei livelli 1–20: titolo, obiettivi, descrizione, testo di avanzamento e di completamento, nella
  finestra della missione, nel registro e nel tracker.
- **Dialoghi dei PNG**: quello che dicono quando ci parli, le opzioni di dialogo, i saluti, le urla e le frasi in
  chat.
- **Tooltip di oggetti e abilità** e **testi dell'interfaccia** (finestre, pulsanti, menu, messaggi): dove il
  client italiano ufficiale di Blizzard usa le stesse parole di Forever, si vede il suo testo.
- **Libri e lettere** per ora restano in inglese.

## Installazione

### Con l'app CurseForge

1. Apri l'app CurseForge, scegli **World of Warcraft** e cerca **oLd_pZ Forever - Traduzione Italiana**.
2. Controlla che in alto sia selezionata l'installazione **Forever**.
3. Fai clic su **Install**.

### A mano

1. Scarica lo zip dell'ultima versione da CurseForge o dalla
   [pagina delle versioni](https://github.com/oLdpZ/oldpz-forever-ita/releases) su GitHub.
2. Apri la cartella di Forever: `World of Warcraft\_forever_\Interface\AddOns` (se `AddOns` non c'è, creala).
   Per trovare `World of Warcraft`: nell'app Battle.net scegli World of Warcraft, seleziona la versione Forever e
   usa **Mostra in Esplora risorse** dal menu a ingranaggio accanto a **Gioca**.
3. Estrai lo zip dentro `AddOns`.
4. Controlla il nome: dentro `AddOns` deve esserci una cartella che si chiama esattamente `OldpZ_ForeverITA`
   (non una cartella dentro un'altra cartella).

### Attivarlo nel gioco

Nella schermata di selezione del personaggio fai clic su **AddOns**, controlla che
**oLd_pZ Forever - Traduzione Italiana** abbia la spunta ed entra nel gioco. La prima volta si apre una piccola
finestra di benvenuto.

## Come si usa

**Alt per l'inglese.** Dove vedi l'italiano, tieni premuto Alt per vedere l'inglese originale; rilascialo per
tornare all'italiano. Puoi cambiare il tasto nelle impostazioni (**Tieni premuto per l'inglese**) o con
`/fita modifier <tasto>`, per esempio `/fita modifier lalt` o `/fita modifier button4`.

**Nomi.** Nella sezione **Nomi** delle impostazioni scegli tra **Italiani ufficiali** (predefinito) e
**Originali inglesi**. Oppure scrivi `/fita nomi it` o `/fita nomi en`; `/fita nomi` da solo passa dall'uno
all'altro. I nomi che Blizzard non ha mai tradotto restano in inglese in ogni caso.

**Indicatori.** Una riga che non ha ancora una traduzione resta in inglese con **[Non tradotto / Not Translated]**.
Una riga il cui inglese è cambiato dopo la traduzione mostra **[Da aggiornare / English Changed]**. Puoi
nasconderli nella sezione **Indicatori** delle impostazioni (**Segna il testo non tradotto**, **Segna le
traduzioni il cui inglese è cambiato**).

**Impostazioni.** Apri **Esc > Opzioni > AddOn > oLd_pZ Forever - Traduzione Italiana**, oppure scrivi
`/fita config`. Puoi:

- attivare o disattivare tutta la traduzione (**Attiva la traduzione**) e assegnare un tasto che la accende e la
  spegne (**Attiva / disattiva la traduzione**);
- scegliere cosa tradurre (**Cosa tradurre**): finestre e registro delle missioni, dialoghi dei PNG, tooltip degli
  oggetti, tooltip delle abilità, testo dell'interfaccia, libri e lettere;
- cambiare il tasto per l'inglese, lo stile dei nomi e gli indicatori;
- mostrare o nascondere il pulsante della minimappa.

Le altre due pagine sono **Raccolta dei testi inglesi** e **Informazioni e aiuto**.

**Il pulsante della minimappa.** Clic sinistro: segnala una riga tradotta male. Clic destro: un menu per accendere
o spegnere la traduzione, segnalare un errore o un'idea, inviare l'inglese raccolto, aprire le impostazioni o
nascondere il pulsante.

**Comandi.** Scrivi `/fita` da solo per vedere tutte le impostazioni e il loro valore.

| Comando | Cosa fa |
|---|---|
| `/fita on`, `/fita off`, `/fita toggle` | accende, spegne o inverte la traduzione |
| `/fita config` | apre le impostazioni (`/fita config collector`, `/fita config about` per le altre pagine) |
| `/fita nomi [it \| en]` | nomi italiani ufficiali o inglesi originali |
| `/fita modifier <tasto>` | il tasto da tenere premuto per l'inglese |
| `/fita togglekey [<tasto> \| none]` | il tasto che accende e spegne la traduzione (per esempio `f5`, `ctrl-j`) |
| `/fita area quests off` | spegne una parte della traduzione (`quests`, `gossip`, `itemTooltips`, `spellTooltips`, `interface`, `books`) |
| `/fita marker missing off` | nasconde un indicatore (`missing` o `stale`) |
| `/fita fix` | segnala una riga tradotta male |
| `/fita bug` | segnala un errore o un'idea |
| `/fita collector [on \| off \| status \| path \| clear \| send]` | la raccolta dei testi inglesi |
| `/fita version` | la versione dell'addon |
| `/fita log`, `/fita debug` | informazioni tecniche, utili quando segnali un problema |

## Perché alcuni testi restano in inglese

- **Testi che arrivano solo dal server.** Molti dialoghi dei PNG, il testo di una missione quando ne controlli
  l'avanzamento o la consegni e le frasi dei PNG in chat non sono nei file del gioco: il server li manda solo quando
  un giocatore li vede. Se nessuno li ha ancora registrati, non hanno una traduzione e restano in inglese con
  **[Non tradotto / Not Translated]**. La raccolta dei testi inglesi (qui sotto) serve proprio a questo.
- **Una parte non è ancora tradotta.** Per ora le missioni arrivano al livello 20, e libri e lettere sono in
  inglese.
- **Cose che il gioco non lascia toccare.** Alcune finestre sono chiuse agli addon: i tooltip di buff e debuff sulla
  finestra del bersaglio, quelli dei buff sotto la minimappa durante il combattimento e il registro di combattimento
  restano in inglese.
- **Alcune righe restano in inglese di proposito**, per esempio dove il gioco mostra testo che non va tradotto.

## La raccolta dei testi inglesi

Quando il gioco mostra un testo inglese che l'addon non sa tradurre (testo delle missioni, dialoghi dei PNG con
l'id del PNG che li dice, descrizioni di oggetti e abilità, nomi dei PNG), l'addon lo annota nel suo file di
salvataggio, così potrà essere tradotto in un aggiornamento futuro.

- **Cosa salva:** il testo inglese, l'id del gioco a cui appartiene, la build del gioco e la versione dell'addon.
  Salva anche classe e razza del personaggio, perché alcune frasi del gioco cambiano in base a queste.
- **Cosa non salva:** il nome del personaggio, l'account, il reame, la posizione, la chat e gli orari. Il tuo nome
  nei testi diventa un segnaposto.
- **Non invia nulla da solo.** Il file resta sul tuo computer finché non decidi tu di mandarlo.

È attiva fin dall'inizio, l'addon lo dice in chat la prima volta e puoi spegnerla nella pagina **Raccolta dei
testi inglesi** (**Registra l'inglese per le traduzioni future**) o con `/fita collector off`. Nella stessa pagina,
**Invia l'inglese** (o `/fita collector send`) apre una finestra con un link: copialo (clic, poi Ctrl+C),
aprilo nel browser e si apre il modulo su GitHub già compilato. Invia la segnalazione, poi nel gioco fai clic su
**L'ho inviato**, così il prossimo invio conterrà solo righe nuove. Se la finestra mostra un secondo riquadro,
copia anche quel testo nel modulo; se il testo è troppo lungo, ti indica il file da comprimere in uno zip e
trascinare nel modulo (`/fita collector path` mostra dove si trova). Serve un account GitHub e la segnalazione è
pubblica: contiene solo quanto descritto sopra.

## Segnalare un problema

Per segnalare una riga tradotta male fai clic sinistro sul pulsante della minimappa (o scrivi `/fita fix`), scegli
la riga tra quelle appena viste, scegli cosa non va e, se vuoi, scrivi come la tradurresti, poi **Salva**. In **Invia
segnalazione** trovi l'indirizzo del modulo e il testo della segnalazione: apri l'indirizzo nel browser, copia la
segnalazione (un clic la seleziona, poi Ctrl+C), incollala nel riquadro **Report** del modulo e inviala. Entro un
minuto un controllo automatico la legge e risponde. Se il tuo italiano viene usato, sei ringraziato in
[`ATTRIBUTION.md`](ATTRIBUTION.md) col nome che scegli.

Per un errore dell'addon o un'idea scrivi `/fita bug` (oppure clic destro sul pulsante della minimappa e
**Segnala errore o idea**). La finestra ti dà un link al modulo con build, versione ed eventuali errori Lua
dell'addon già compilati: aprilo nel browser, scrivi cosa è successo e invia, poi nel gioco fai clic su
**L'ho inviato**. Scegli **Proposta** in alto nella finestra per il modulo delle idee. Se usi BugSack o un addon
simile, la finestra te lo dice: copia da lì gli errori di questo addon.

Tutte le segnalazioni sono su [GitHub](https://github.com/oLdpZ/oldpz-forever-ita/issues): serve un account GitHub
e le segnalazioni sono pubbliche.

## Riconoscimenti

Questo addon è un fork di **WoW Forever Japanese** di **Zyaga**: l'architettura dell'addon, gli strumenti e i test
vengono da lì, modificati per l'italiano. Le traduzioni giapponesi non fanno parte di questo progetto. I nomi e i
testi italiani ufficiali vengono dal client italiano di World of Warcraft di Blizzard; il resto è tradotto per
questo addon seguendo la stessa terminologia. Tutte le fonti sono in [`ATTRIBUTION.md`](ATTRIBUTION.md).

## Licenza

GPL-2.0-or-later ([`LICENSE`](LICENSE)). Da dove vengono i testi e cosa non è nostro:
[licenze](docs/legal/licensing.md) (in inglese).

Questo addon è fatto da un appassionato. Non è affiliato né approvato da Blizzard Entertainment. World of Warcraft,
Warcraft e Blizzard Entertainment sono marchi o marchi registrati di Blizzard Entertainment, Inc. negli Stati Uniti
e/o in altri paesi.

## Per chi sviluppa

Correzioni, segnalazioni e codice sono benvenuti: vedi [`CONTRIBUTING.md`](CONTRIBUTING.md) (in inglese). Come
funziona e perché: [documentazione](docs/overview.md). Cosa cambia in ogni versione: [`CHANGELOG.md`](CHANGELOG.md).
