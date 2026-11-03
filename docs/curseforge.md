# CurseForge description

The text of the CurseForge project pages: the addon, and one page per voice pack. Paste everything under a
"Description" heading into that project's description with the editor set to Markdown. The `<span style="color:…">`
tags are the editor's own colour syntax. The counts line ("In numeri: …") follows `make coverage`
(docs/operations/coverage.md); paste the page again when it changes.

The addon and the voice packs are separate projects because the CurseForge app installs one file per project:
each voice pack lists the addon as a **Required Dependency**, so the app installs the addon with it (set it on
each voice file at upload: an unapproved project is not found by the Default Relations search).

Projects (created 2026-11-03, Unlisted): addon 1781383; voices 1-20 1781385, 21-40 1781387, 41-55 1781388,
56-60 1781391, libri/dialoghi/altro 1781395. CurseForge requires the **Summary in English** and an **English section first** in the description
(moderators asked for it on 2026-11-03), Italian below. Logo: dist/curseforge/logo-ita.png (the owner's; CurseForge forbids game logos). Files: flavor **Forever**,
game version 1.60.x.

## Addon

- **Project name:** oLd_pZ Forever - Traduzione Italiana
- **Summary:** Italian translation of WoW Forever: quests, NPC dialogue, books, tooltips, interface and official
  Italian names, with optional Italian NPC voices.
- **Main category:** Quests & Leveling. **Additional:** Tooltip, Chat & Communication, Audio & Video, Miscellaneous.
- **License:** GNU General Public License version 2 (GPLv2) — the addon is GPL-2.0-or-later.
- **Logo:** dist/curseforge/logo-ita.png

### Description

## <span style="color:#E8C77E;">English</span>

**oLd_pZ Forever - Traduzione Italiana** shows World of Warcraft: Forever in Italian. The game's original <span style="color:#8CB8E8;">English</span> is always one key away: hold <span style="color:#E0605A;">**Alt**</span> and it comes back, release it and the Italian returns.

### <span style="color:#E8C77E;">What it translates</span>

- **Quests** of every level: title, objectives, description, progress and completion, in the quest window, the quest log and the tracker.
- **NPC dialogue:** what NPCs say when you talk to them, gossip options, greetings, yells and chat lines.
- **Books and letters.**
- **Item and spell tooltips** and **interface text** (windows, buttons, menus, messages), using Blizzard's official Italian client text wherever it uses the same words as Forever.
- **Names** of items, spells, zones, factions and NPCs, including above characters' heads and in the game's windows.

In numbers: **4,775** quests, **10,876** NPC dialogue lines, **921** book pages, **208** letter pages, **10,223** item tooltips, **19,870** spell tooltips, **15,257** interface texts.

### <span style="color:#E8C77E;">Italian NPC voices</span>

NPCs can also **speak Italian**: quest offers, progress and turn-ins, greetings, books and letters. The voices come in five separate packs, by level band, to install only if you want them (see the **oLd_pZ Forever - Voci italiane** projects). The voices are generated with Google Gemini text-to-speech, with a voice of their own for the main characters. On the **Voce** settings page you choose what is read aloud and how the speaker panel is shown: with portrait, without portrait, or no panel.

### <span style="color:#E8C77E;">Names</span>

Places, characters, factions, items and spells use Blizzard's official Italian names (Roccavento, not Stormwind). Prefer the <span style="color:#8CB8E8;">English</span> names to talk with other players or follow guides? Type **/fita nomi en** (and **/fita nomi it** to switch back), or choose kind by kind on the **Nomi** settings page. The spellbook stays in English on purpose: writing to it would block the action bars in combat.

### <span style="color:#E8C77E;">Settings</span>

**Esc > Options > AddOns**, or type **/fita config**. You can turn the translation on or off, all of it or part by part; change the key you hold for English; bind a key that toggles the translation; choose the name style; hide the markers (<span style="color:#FFD100;">**[Non tradotto / Not Translated]**</span>, <span style="color:#FFD100;">**[Da aggiornare / English Changed]**</span>) and the minimap button. **/fita** alone lists every command.

### <span style="color:#E8C77E;">Why some text stays in English</span>

Some text only arrives from the server when a player sees it: if it is not translated yet it stays in English with <span style="color:#FFD100;">**[Non tradotto / Not Translated]**</span>. Some windows are closed to addons (buffs on the target frame, buffs under the minimap in combat, the combat log) and stay in English.

### <span style="color:#E8C77E;">What the addon records</span>

When the game shows English text the addon cannot translate, the addon notes it in its own saved-variables file, so it can be translated in a future update. It saves the character's class and race, because some game lines change with them. It never saves character name, account, realm, position, chat or times, and never sends anything by itself. You can turn collection off on the **Raccolta dei testi inglesi** page or with **/fita collector off**.

### <span style="color:#E8C77E;">Installation</span>

Install it with the CurseForge app (make sure the **Forever** installation is selected), or extract the zip into `World of Warcraft\_forever_\Interface\AddOns`: the `OldpZ_ForeverITA` folder must be inside. At character selection, in **AddOns**, make sure the addon is ticked. World of Warcraft: Forever only; no other addons or libraries needed.

### <span style="color:#E8C77E;">Reporting a problem</span>

A badly translated line: left-click the minimap button (or **/fita fix**), pick the line and what is wrong, then copy the report from **Invia segnalazione**. A bug or an idea: **/fita bug**, which prepares the text with build, version and Lua errors. You can leave everything in this page's comments.

### <span style="color:#E8C77E;">Credits and license</span>

Based on **WoW Forever Japanese** by Zyaga (GPL-2.0-or-later): the addon architecture comes from it, the Japanese translations do not. Official Italian names and text come from Blizzard's Italian World of Warcraft client; the rest is translated for this addon with the same terminology. Sources are listed in `ATTRIBUTION.md`, included in the addon. License GPL-2.0-or-later.

This addon is made by a fan. It is not affiliated with or endorsed by Blizzard Entertainment. World of Warcraft, Warcraft and Blizzard Entertainment are trademarks or registered trademarks of Blizzard Entertainment, Inc. in the U.S. and/or other countries.

---

## <span style="color:#E8C77E;">Italiano</span>

**oLd_pZ Forever - Traduzione Italiana** mostra World of Warcraft: Forever in italiano. L'<span style="color:#8CB8E8;">inglese</span> originale del gioco è sempre a un tasto di distanza: tieni premuto <span style="color:#E0605A;">**Alt**</span> e torna, rilascialo e torna l'italiano.

### <span style="color:#E8C77E;">Cosa traduce</span>

- **Missioni** di tutti i livelli: titolo, obiettivi, descrizione, avanzamento e completamento, nella finestra della missione, nel registro e nel tracker.
- **Dialoghi dei PNG:** quello che dicono quando ci parli, le opzioni di dialogo, i saluti, le urla e le frasi in chat.
- **Libri e lettere.**
- **Tooltip di oggetti e abilità** e **testi dell'interfaccia** (finestre, pulsanti, menu, messaggi), con il testo del client italiano ufficiale di Blizzard dove usa le stesse parole di Forever.
- **Nomi** di oggetti, abilità, zone, fazioni e PNG, anche sopra la testa dei personaggi e nelle finestre del gioco.

In numeri: **4.775** missioni, **10.876** righe di dialogo dei PNG, **921** pagine di libri, **208** pagine di lettere, **10.223** tooltip degli oggetti, **19.870** tooltip delle abilità, **15.257** testi dell'interfaccia.

### <span style="color:#E8C77E;">Voci italiane dei PNG</span>

I PNG possono anche **parlare in italiano**: proposte, avanzamento e consegna delle missioni, saluti, libri e lettere. Le voci sono in cinque pacchetti a parte, per fascia di livello, da installare solo se le vuoi (vedi i progetti **oLd_pZ Forever - Voci italiane**). Le voci sono generate con la sintesi vocale di Google Gemini, con una voce propria per i personaggi principali. Dalla pagina **Voce** delle impostazioni scegli cosa leggere ad alta voce e come mostrare il pannello di chi parla: con il ritratto, senza ritratto o nessun pannello.

### <span style="color:#E8C77E;">Nomi</span>

Luoghi, personaggi, fazioni, oggetti e abilità usano i nomi italiani ufficiali di Blizzard (Roccavento, non Stormwind). Preferisci i nomi <span style="color:#8CB8E8;">inglesi</span> per parlare con gli altri giocatori o seguire le guide? Scrivi **/fita nomi en** (e **/fita nomi it** per tornare), oppure scegli tipo per tipo nella pagina **Nomi** delle impostazioni. Il libro degli incantesimi resta in inglese apposta: scriverci bloccherebbe le barre delle azioni in combattimento.

### <span style="color:#E8C77E;">Impostazioni</span>

**Esc > Opzioni > AddOn**, oppure scrivi **/fita config**. Puoi accendere o spegnere la traduzione, tutta o parte per parte; cambiare il tasto da tenere premuto per l'inglese; assegnare un tasto che accende e spegne la traduzione; scegliere lo stile dei nomi; nascondere gli indicatori (<span style="color:#FFD100;">**[Non tradotto / Not Translated]**</span>, <span style="color:#FFD100;">**[Da aggiornare / English Changed]**</span>) e il pulsante della minimappa. **/fita** da solo mostra tutti i comandi.

### <span style="color:#E8C77E;">Perché alcuni testi restano in inglese</span>

Alcuni testi arrivano solo dal server, quando un giocatore li vede: se non sono ancora tradotti restano in inglese con <span style="color:#FFD100;">**[Non tradotto / Not Translated]**</span>. Alcune finestre sono chiuse agli addon (i buff sulla finestra del bersaglio, i buff sotto la minimappa in combattimento, il registro di combattimento) e restano in inglese.

### <span style="color:#E8C77E;">Cosa registra l'addon</span>

Quando il gioco mostra un testo inglese che l'addon non sa tradurre, l'addon lo annota nel suo file di salvataggio, così potrà essere tradotto in un aggiornamento futuro. Salva classe e razza del personaggio, perché alcune frasi del gioco cambiano in base a queste. Non salva mai nome del personaggio, account, reame, posizione, chat né orari, e non invia nulla da solo. Puoi spegnere la raccolta nella pagina **Raccolta dei testi inglesi** o con **/fita collector off**.

### <span style="color:#E8C77E;">Installazione</span>

Installalo con l'app CurseForge (controlla che sia selezionata l'installazione **Forever**), oppure estrai lo zip in `World of Warcraft\_forever_\Interface\AddOns`: dentro deve esserci la cartella `OldpZ_ForeverITA`. Nella selezione del personaggio, in **AddOns**, controlla che l'addon abbia la spunta. Solo World of Warcraft: Forever; non servono altri addon o librerie.

### <span style="color:#E8C77E;">Segnalare un problema</span>

Una riga tradotta male: clic sinistro sul pulsante della minimappa (o **/fita fix**), scegli la riga e cosa non va, poi da **Invia segnalazione** copia la segnalazione. Un errore o un'idea: **/fita bug**, che prepara il testo con build, versione ed errori Lua. Puoi lasciare tutto nei commenti di questa pagina.

### <span style="color:#E8C77E;">Riconoscimenti e licenza</span>

Basato su **WoW Forever Japanese** di Zyaga (GPL-2.0-or-later): l'architettura dell'addon viene da lì, le traduzioni giapponesi no. I nomi e i testi italiani ufficiali vengono dal client italiano di World of Warcraft di Blizzard; il resto è tradotto per questo addon con la stessa terminologia. Le fonti sono in `ATTRIBUTION.md`, incluso nell'addon. Licenza GPL-2.0-or-later.

Questo addon è fatto da un appassionato. Non è affiliato né approvato da Blizzard Entertainment. World of Warcraft, Warcraft e Blizzard Entertainment sono marchi o marchi registrati di Blizzard Entertainment, Inc. negli Stati Uniti e/o in altri paesi.

## Voice packs

Five projects, one per pack; only the name, summary and the range line change.

| Project name | Pack folder | Range line | Range en |
|---|---|---|---|
| oLd_pZ Forever - Voci italiane (livelli 1-20) | OldpZ_ForeverITA_Voce_01_20 | le missioni dei livelli 1–20 | the quests of levels 1–20 |
| oLd_pZ Forever - Voci italiane (livelli 21-40) | OldpZ_ForeverITA_Voce_21_40 | le missioni dei livelli 21–40 | the quests of levels 21–40 |
| oLd_pZ Forever - Voci italiane (livelli 41-55) | OldpZ_ForeverITA_Voce_41_55 | le missioni dei livelli 41–55 | the quests of levels 41–55 |
| oLd_pZ Forever - Voci italiane (livelli 56-60) | OldpZ_ForeverITA_Voce_56_60 | le missioni dei livelli 56–60 | the quests of levels 56–60 |
| oLd_pZ Forever - Voci italiane (libri, dialoghi e altro) | OldpZ_ForeverITA_Voce_Altro | libri, lettere, dialoghi dei PNG e missioni senza una fascia di livello | books, letters, NPC dialogue and quests without a level band |

- **Summary:** Italian NPC voices for the quests of levels N-M (Altro: for books, letters, NPC dialogue and quests
  without a level band): an optional voice pack for the oLd_pZ Forever - Traduzione Italiana addon.
- **Main category:** Audio & Video. **Additional:** Quests & Leveling.
- **License:** All Rights Reserved (the audio is not GPL code).
- **Relations:** Required Dependency → oLd_pZ Forever - Traduzione Italiana.
- **Logo:** dist/curseforge/logo-ita.png

### Description (replace <range line> and <range en>)

**English:** Italian NPC voices for <range en>, for the **oLd_pZ Forever - Traduzione Italiana** addon, which is required to hear them (the CurseForge app installs it too). NPCs read aloud in Italian what they say: quest offers, progress and turn-ins, greetings, books and letters. Install only the packs you want; each works on its own. Settings are on the addon's **Voce** page; **/fita voce stop** stops the voice. The voices are AI-generated with Google Gemini text-to-speech from the Italian translation. Manual install: extract the zip into `World of Warcraft\_forever_\Interface\AddOns`, next to `OldpZ_ForeverITA`. Not affiliated with or endorsed by Blizzard Entertainment.

---

**Italiano:** **Voci italiane dei PNG** per <range line>, per l'addon **oLd_pZ Forever - Traduzione Italiana**, che serve per sentirle (l'app CurseForge lo installa insieme).

I PNG leggono ad alta voce in italiano quello che dicono: proposta, avanzamento e consegna delle missioni, saluti, libri e lettere. Installa solo le fasce che ti servono; ogni pacchetto funziona da solo.

- **Impostazioni:** pagina **Voce** delle impostazioni dell'addon (compare quando c'è almeno un pacchetto). Scegli cosa leggere, se silenziare le voci inglesi del gioco mentre parla un PNG e come mostrare il pannello di chi parla: con il ritratto, senza ritratto o nessuno (solo la voce).
- **Comandi:** **/fita voce stop** ferma la voce e le battute in attesa.
- **Voci generate con l'intelligenza artificiale:** le battute sono state create con la sintesi vocale di Google Gemini a partire dalla traduzione italiana, con voci progettate per i personaggi principali e voci per razza e sesso per gli altri. Qualche battuta può avere una pronuncia imperfetta: segnalala nei commenti.
- **Installazione a mano:** estrai lo zip in `World of Warcraft\_forever_\Interface\AddOns`, accanto alla cartella `OldpZ_ForeverITA`.

Non affiliato né approvato da Blizzard Entertainment. World of Warcraft è un marchio di Blizzard Entertainment, Inc.
