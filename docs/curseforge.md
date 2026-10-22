# CurseForge description

The text of the addon's CurseForge project page. It is the README condensed; when one changes, change the other.
Paste everything under "Description" into the project's description with the editor set to Markdown. The
`<span style="color:…">` tags are the editor's own colour syntax. The page has no images. The counts line
("In numeri: …") is rewritten by `make coverage`; paste the page again when it changes.

- **Project name:** oLd_pZ Forever - Traduzione Italiana
- **Summary:** World of Warcraft: Forever in italiano: missioni, dialoghi dei PNG, tooltip e interfaccia, con
  l'inglese originale a portata di tasto.
- **Categories:** Quests & Leveling; also Tooltip, Chat & Communication, Miscellaneous.

## Description

**oLd_pZ Forever - Traduzione Italiana** mostra World of Warcraft: Forever in italiano. L'<span style="color:#8CB8E8;">inglese</span> originale del gioco è sempre a un tasto di distanza: tieni premuto <span style="color:#E0605A;">**Alt**</span> e torna, rilascialo e torna l'italiano.

### <span style="color:#E8C77E;">Cosa traduce</span>

- **Missioni** dei livelli 1–20: titolo, obiettivi, descrizione, avanzamento e completamento, nella finestra della missione, nel registro e nel tracker.
- **Dialoghi dei PNG:** quello che dicono quando ci parli, le opzioni di dialogo, i saluti, le urla e le frasi in chat.
- **Tooltip di oggetti e abilità** e **testi dell'interfaccia** (finestre, pulsanti, menu, messaggi), con il testo del client italiano ufficiale di Blizzard dove usa le stesse parole di Forever.
- **Libri e lettere** per ora restano in inglese.

In numeri: **4.775** missioni, **10.876** righe di dialogo dei PNG, **921** pagine di libri, **208** pagine di lettere, **10.223** tooltip degli oggetti, **14.448** tooltip delle abilità, **15.252** testi dell'interfaccia.

### <span style="color:#E8C77E;">Nomi</span>

Luoghi, personaggi, fazioni, oggetti e abilità usano i nomi italiani ufficiali di Blizzard (Roccavento, non Stormwind). Preferisci i nomi <span style="color:#8CB8E8;">inglesi</span> per parlare con gli altri giocatori o seguire le guide? Scrivi **/fita nomi en** (e **/fita nomi it** per tornare), oppure scegli nella sezione **Nomi** delle impostazioni.

### <span style="color:#E8C77E;">Impostazioni</span>

**Esc > Opzioni > AddOn**, oppure scrivi **/fita config**. Puoi accendere o spegnere la traduzione, tutta o parte per parte; cambiare il tasto da tenere premuto per l'inglese; assegnare un tasto che accende e spegne la traduzione; scegliere lo stile dei nomi; nascondere gli indicatori (<span style="color:#FFD100;">**[Non tradotto / Not Translated]**</span>, <span style="color:#FFD100;">**[Da aggiornare / English Changed]**</span>) e il pulsante della minimappa. **/fita** da solo mostra tutte le impostazioni.

### <span style="color:#E8C77E;">Perché alcuni testi restano in inglese</span>

Molti dialoghi e i testi di consegna delle missioni arrivano solo dal server, quando un giocatore li vede: finché nessuno li ha registrati restano in inglese con <span style="color:#FFD100;">**[Non tradotto / Not Translated]**</span>. Le missioni oltre il livello 20 e i libri non sono ancora tradotti. Alcune finestre sono chiuse agli addon (i buff sulla finestra del bersaglio, i buff sotto la minimappa in combattimento, il registro di combattimento) e restano in inglese.

### <span style="color:#E8C77E;">Cosa registra l'addon</span>

Quando il gioco mostra un testo inglese che l'addon non sa tradurre, l'addon lo annota nel suo file di salvataggio, così potrà essere tradotto in un aggiornamento futuro. Salva classe e razza del personaggio, perché alcune frasi del gioco cambiano in base a queste. Non salva mai nome del personaggio, account, reame, posizione, chat né orari, e non invia nulla da solo. Inviarlo per la traduzione è facoltativo (vedi sotto). Puoi spegnere la raccolta nella pagina **Raccolta dei testi inglesi** o con **/fita collector off**.

### <span style="color:#E8C77E;">Installazione</span>

Installalo con l'app CurseForge (controlla che sia selezionata l'installazione **Forever**), oppure estrai lo zip in `World of Warcraft\_forever_\Interface\AddOns`: dentro deve esserci la cartella `OldpZ_ForeverITA`. Nella selezione del personaggio, in **AddOns**, controlla che l'addon abbia la spunta. Solo World of Warcraft: Forever; non servono altri addon o librerie.

### <span style="color:#E8C77E;">Segnalare un problema</span>

Una riga tradotta male: clic sinistro sul pulsante della minimappa (o **/fita fix**), scegli la riga e cosa non va, poi da **Invia segnalazione** apri il modulo nel browser e incolla la segnalazione. Un errore o un'idea: **/fita bug**, che ti dà un link al modulo già compilato con build, versione ed errori Lua. Anche l'inglese raccolto si invia così (**Invia l'inglese**, o **/fita collector send**). Le segnalazioni sono su GitHub, pubbliche, e serve un account: https://github.com/oLdpZ/oldpz-forever-ita/issues

### <span style="color:#E8C77E;">Riconoscimenti e licenza</span>

Basato su **WoW Forever Japanese** di Zyaga (GPL-2.0-or-later): l'architettura dell'addon viene da lì, le traduzioni giapponesi no. I nomi e i testi italiani ufficiali vengono dal client italiano di World of Warcraft di Blizzard; il resto è tradotto per questo addon con la stessa terminologia. Le fonti sono in `ATTRIBUTION.md`, incluso nell'addon. Licenza GPL-2.0-or-later. Codice sorgente e traduzioni: https://github.com/oLdpZ/oldpz-forever-ita

Questo addon è fatto da un appassionato. Non è affiliato né approvato da Blizzard Entertainment. World of Warcraft, Warcraft e Blizzard Entertainment sono marchi o marchi registrati di Blizzard Entertainment, Inc. negli Stati Uniti e/o in altri paesi.
