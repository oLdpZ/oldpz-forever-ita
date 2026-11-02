-- UI/OptionsText.lua: the settings pages' own copy, English + Italian. Setting labels live on their
-- definitions (`label` / `it`); everything else the pages say lives here. Addon interface text, not game text: no
-- data/ entry, no provenance. `%s` placeholders appear the same number of times, in the same order, in both. Longer
-- help copy breaks between sentences with "\n" (the same break in both languages) rather than wrapping mid-sentence.
local _, WFJ = ...
local Text = {}
WFJ.OptionsText = Text

Text.T = {
  -- the addon's name: the same in both languages
  ["page.main"] = { en = "oLd_pZ Forever - Traduzione Italiana", it = "oLd_pZ Forever - Traduzione Italiana" },
  ["page.collector"] = { en = "English Collector", it = "Raccolta dei testi inglesi" },
  ["page.about"] = { en = "About & Help", it = "Informazioni e aiuto" },
  ["page.voice"] = { en = "Voice", it = "Voce" }, -- only with a voice pack
  ["tagline"] = {
    en = "Italian quest, NPC and tooltip text. Hold a key for the game's English.",
    it = "Missioni, dialoghi dei PNG e tooltip in italiano. Tieni premuto un tasto per l'inglese del gioco.",
  },

  ["section.translation"] = { en = "Translation", it = "Traduzione" },
  ["section.areas"] = { en = "What to translate", it = "Cosa tradurre" },
  ["section.markers"] = { en = "Markers", it = "Indicatori" },
  ["page.names"] = { en = "Names", it = "Nomi" },
  ["section.names"] = { en = "Names", it = "Nomi" },
  ["section.clientNames"] = { en = "Names shown by the game", it = "Nomi mostrati dal gioco" },
  ["section.collector"] = { en = "Collector", it = "Raccolta" },
  ["section.files"] = { en = "Sending it in", it = "Come inviarlo" },
  ["section.help"] = { en = "How it works", it = "Come funziona" },
  ["section.slash"] = { en = "Slash commands", it = "Comandi slash" },
  ["section.voice"] = { en = "Italian voices", it = "Voci italiane" },
  ["section.voiceKinds"] = { en = "What is read aloud", it = "Cosa si legge ad alta voce" },
  -- the voice panel's buttons (UI/VoicePanel), as their tooltips
  ["voice.stop"] = { en = "Stop (and drop the lines waiting)", it = "Ferma (e togli le battute in attesa)" },
  ["voice.skip"] = { en = "Next line", it = "Battuta successiva" },

  ["toggleKey"] = { en = "Turn translation on / off", it = "Attiva / disattiva la traduzione" },
  ["key.notSet"] = { en = "Not set", it = "Non assegnato" },

  ["button.capture"] = { en = "Change", it = "Cambia" },
  ["button.capturing"] = { en = "Press a key", it = "Premi un tasto" },
  ["button.setKey"] = { en = "Set key", it = "Assegna tasto" },
  ["button.unbind"] = { en = "Unbind", it = "Rimuovi" },
  ["button.replace"] = { en = "Replace", it = "Sostituisci" },
  ["button.settings"] = { en = "Settings", it = "Impostazioni" },

  ["warn.takeover"] = {
    en = "%s is used for \"%s\". While this addon is loaded, %s shows English instead.",
    it = "%s è assegnato a \"%s\". Finché questo addon è attivo, %s mostra invece l'inglese.",
  },
  ["warn.toggleConflict"] = {
    en = "%s is already the key for turning translation on / off.",
    it = "%s è già il tasto per attivare / disattivare la traduzione.",
  },
  ["warn.revealConflict"] = {
    en = "%s is already the key for showing English.",
    it = "%s è già il tasto per mostrare l'inglese.",
  },
  ["warn.bindReplace"] = { en = "%s is used for \"%s\". Replace it?",
    it = "%s è assegnato a \"%s\". Vuoi sostituirlo?" },
  ["warn.combat"] = { en = "Keys can't be changed in combat.", it = "Non puoi cambiare i tasti in combattimento." },
  ["warn.afterCombat"] = { en = "%s takes effect after combat.", it = "%s avrà effetto alla fine del combattimento." },
  ["warn.addonChanges"] = {
    en = "Apply or cancel your AddOn changes first.",
    it = "Prima applica o annulla le modifiche agli AddOn.",
  },

  ["collector.explain"] = {
    en = "The addon notes English it has no translation for.\n"
      .. "Nothing is sent anywhere unless you send it yourself with the steps below.",
    it = "L'addon annota l'inglese per cui non ha una traduzione.\n"
      .. "Non viene inviato nulla, a meno che non lo invii tu con i passaggi qui sotto.",
  },
  ["collector.status"] = { en = "Status", it = "Stato" },
  -- the status line in the page's language (the slash command keeps Collector.describe's English)
  ["collector.statusLine"] = { en = "%s · %s entries · %s of %s", it = "%s · %s voci · %s di %s" },
  ["collector.on"] = { en = "on", it = "attiva" },
  ["collector.off"] = { en = "off", it = "disattivata" },
  ["collector.full"] = { en = "full", it = "piena" },
  ["collector.paused"] = { en = "paused (file from a newer version)",
    it = "in pausa (file di una versione più recente)" },
  ["collector.errors"] = { en = "%s errors", it = "%s errori" },
  ["collector.path"] = {
    en = "Too long to paste? Zip this file and attach it to the same issue:",
    it = "Troppo lungo da incollare? Comprimi questo file in uno zip e allegalo alla stessa segnalazione:",
  },
  ["collector.steps"] = {
    en = "1. Click Send English.\n"
      .. "2. Copy the link in the window (click it, then Ctrl+C) and open it in your web browser.\n"
      .. "3. If the window shows a second box, copy that text into the form's box too.\n"
      .. "4. Submit the issue on GitHub, then click I sent it.",
    it = "1. Fai clic su Invia l'inglese.\n"
      .. "2. Copia il link nella finestra (fai clic, poi Ctrl+C) e aprilo nel browser.\n"
      .. "3. Se la finestra mostra un secondo riquadro, copia anche quel testo nel modulo.\n"
      .. "4. Invia la segnalazione su GitHub, poi fai clic su L'ho inviato.",
  },
  ["collector.send"] = { en = "Send English", it = "Invia l'inglese" },
  ["send.title"] = { en = "Send collected English", it = "Invia l'inglese raccolto" },
  ["send.summary.empty"] = {
    en = "Nothing new to send. /fita collector send all sends every line again.",
    it = "Niente di nuovo da inviare. /fita collector send all invia di nuovo tutte le righe.",
  },
  ["send.summary.unavailable"] = {
    en = "This game client cannot pack the text, so the saved file goes with the issue instead.",
    it = "Questo client non può comprimere il testo, quindi alla segnalazione va allegato il file salvato.",
  },
  ["send.summary.readonly"] = {
    en = "The saved file is from a newer version of the addon. Update the addon to send it.",
    it = "Il file salvato è di una versione più recente dell'addon. Aggiorna l'addon per inviarlo.",
  },
  ["send.summary"] = {
    en = "%s lines to send in one issue (%s already in Italian, left out).",
    it = "%s righe da inviare in una segnalazione (%s già in italiano, escluse).",
  },
  ["send.step1"] = {
    en = "1. Copy this link (click it, then Ctrl+C) and open it in your web browser:",
    it = "1. Copia questo link (fai clic, poi Ctrl+C) e aprilo nel browser:",
  },
  ["send.step2.link"] = { en = "2. The form opens filled in.", it = "2. Si apre il modulo già compilato." },
  ["send.step2.paste"] = {
    en = "2. Copy this text too (click it, then Ctrl+C) and paste it into the form:",
    it = "2. Copia anche questo testo (fai clic, poi Ctrl+C) e incollalo nel modulo:",
  },
  ["send.step2.file"] = {
    en = "2. Zip this file and drag it into the form (/reload first saves it):",
    it = "2. Comprimi questo file in uno zip e trascinalo nel modulo (prima /reload lo salva):",
  },
  ["send.step3"] = { en = "3. Submit the issue on GitHub.", it = "3. Invia la segnalazione su GitHub." },
  ["send.step4"] = { en = "4. Then click:", it = "4. Poi fai clic su:" },
  ["send.sent"] = { en = "I sent it", it = "L'ho inviato" },
  ["send.later"] = {
    en = "%s new lines are not in the file yet: /reload, then open this again.",
    it = "%s righe nuove non sono ancora nel file: /reload, poi riapri questa finestra.",
  },
  ["send.markedFull"] = {
    en = "%s lines marked as sent. Full: Clear collected English makes room.",
    it = "%s righe segnate come inviate. Raccolta piena: Svuota l'inglese raccolto fa spazio.",
  },
  ["send.marked"] = {
    en = "%s lines marked as sent. The next send holds only new lines.",
    it = "%s righe segnate come inviate. Il prossimo invio conterrà solo righe nuove.",
  },
  -- the report window (UI/ReportWindow): a bug or an idea; its link and I sent it reuse send.step1 / step4 / sent
  ["report.title"] = { en = "Report a bug or an idea", it = "Segnala un errore o un'idea" },
  ["report.bug"] = { en = "Bug", it = "Errore" },
  ["report.idea"] = { en = "Idea", it = "Proposta" },
  ["report.summary.errors"] = {
    en = "%s new Lua errors from this addon go with the report.",
    it = "La segnalazione include %s nuovi errori Lua di questo addon.",
  },
  ["report.summary.none"] = {
    en = "No new Lua errors from this addon. Build and version go with it.",
    it = "Nessun nuovo errore Lua di questo addon. Si inviano build e versione.",
  },
  ["report.summary.other"] = {
    en = "Another addon (BugSack or similar) catches Lua errors: paste ours from it.",
    it = "Un altro addon (es. BugSack) raccoglie gli errori Lua: incollali da lì.",
  },
  ["report.summary.idea"] = {
    en = "Ideas and code changes go to GitHub.",
    it = "Idee e modifiche al codice vanno su GitHub.",
  },
  ["report.step2.link"] = {
    en = "2. The form opens with build, version and errors filled in.",
    it = "2. Si apre il modulo con build, versione ed errori già compilati.",
  },
  ["report.step2.paste"] = {
    en = "2. Copy this text (click, Ctrl+C) into the form's Lua errors box:",
    it = "2. Copia questo testo (clic, Ctrl+C) nel riquadro degli errori Lua:",
  },
  ["report.step3"] = {
    en = "3. Write what happened, then submit the issue on GitHub.",
    it = "3. Scrivi cosa è successo, poi invia la segnalazione su GitHub.",
  },
  ["report.idea.step2"] = {
    en = "2. Write your idea, then submit the issue on GitHub.",
    it = "2. Scrivi la tua idea, poi invia la segnalazione su GitHub.",
  },
  ["report.marked"] = {
    en = "%s errors marked as sent. The next report holds only new ones.",
    it = "%s errori segnati come inviati. Il prossimo invio avrà solo quelli nuovi.",
  },
  ["about.bug"] = {
    en = "Something not working, or an idea? Send it from here.",
    it = "Qualcosa non funziona, o hai un'idea? Inviala da qui.",
  },
  ["button.reportBug"] = { en = "Report a bug or idea", it = "Segnala errore o idea" },
  ["collector.clear"] = { en = "Clear collected English", it = "Svuota l'inglese raccolto" },
  ["collector.confirm"] = { en = "Click again to clear %s entries", it = "Fai di nuovo clic per eliminare %s voci" },
  ["collector.cleared"] = { en = "Cleared %s entries", it = "%s voci eliminate" },

  ["about.open"] = {
    en = "Open settings: Esc > Options > AddOns  /  the AddOn List's \"Settings\"  /  /fita config",
    it = "Aprire le impostazioni: Esc > Opzioni > AddOn  /  \"Impostazioni\" nell'elenco degli AddOn  /  /fita config",
  },
  -- %s: the reveal key's name ("Alt", "Mouse Button 4")
  ["about.hold"] = {
    en = "Hold %s to see the game's own English; let go to return to Italian.",
    it = "Tieni premuto %s per vedere l'inglese originale del gioco; rilascialo per tornare all'italiano.",
  },
  -- %s, %s: the two markers as they show (WFJ.MARKER.stale, .missing)
  ["about.markers"] = {
    en = "%s  the English changed after translation.\n%s  this line has no translation yet.",
    it = "%s  l'inglese è cambiato dopo la traduzione.\n%s  questa riga non ha ancora una traduzione.",
  },
  -- the line under a page title: version, memory, how much data ships
  ["header.data"] = { en = "data: %s quests · %s items · %s spells · %s UI strings",
    it = "dati: %s missioni · %s oggetti · %s abilità · %s stringhe UI" },
  ["header.noData"] = { en = "data: none", it = "dati: nessuno" },
  ["header.noMemory"] = { en = "memory n/a", it = "memoria n/d" },

  -- the fix window (UI/FixWindow) and the About page's way into it
  ["about.fix"] = {
    en = "Spotted a wrong or awkward line? Pick it from the lines you just saw.",
    it = "Hai trovato una riga sbagliata o poco naturale? Sceglila tra le righe appena viste.",
  },
  ["button.reportLine"] = { en = "Report a line", it = "Segnala una riga" },
  ["fix.title"] = { en = "Report a translation", it = "Segnala una traduzione" },
  ["fix.tab.recent"] = { en = "Translations", it = "Traduzioni" },
  ["fix.tab.pending"] = { en = "Pending (%s)", it = "In attesa (%s)" },
  ["fix.tab.copy"] = { en = "Send report", it = "Invia segnalazione" },
  ["fix.recent.explain"] = {
    en = "Lines shown this session, newest first. Click the one to report.",
    it = "Righe mostrate in questa sessione, dalla più recente. Fai clic su quella da segnalare.",
  },
  ["fix.filter.story"] = { en = "Quests & NPCs", it = "Missioni e PNG" },
  ["fix.filter.tooltips"] = { en = "Tooltips", it = "Tooltip" },
  ["fix.filter.windows"] = { en = "Windows", it = "Finestre" },
  ["fix.filter.all"] = { en = "All", it = "Tutte" },
  ["fix.recent.empty"] = {
    en = "Nothing yet. Read some quest or NPC text, then open this again.",
    it = "Ancora niente. Leggi il testo di qualche missione o PNG, poi riapri questa finestra.",
  },
  ["fix.edit.reason"] = { en = "What is wrong?", it = "Cosa non va?" },
  ["fix.edit.note"] = { en = "Note (optional)", it = "Nota (facoltativa)" },
  ["fix.edit.it"] = { en = "The line. Rewrite it if you like (optional)",
    it = "La riga. Riscrivila se vuoi (facoltativo)" },
  ["reason.wrong"] = { en = "Wrong meaning", it = "Significato sbagliato" },
  ["reason.awkward"] = { en = "Awkward / unnatural", it = "Italiano poco naturale" },
  ["reason.typo"] = { en = "Typo / broken text", it = "Refuso / testo rovinato" },
  ["reason.name"] = { en = "A name was changed", it = "Un nome è stato cambiato" },
  ["reason.other"] = { en = "Other", it = "Altro" },
  ["button.saveFix"] = { en = "Save", it = "Salva" },
  ["button.back"] = { en = "Back", it = "Indietro" },
  ["button.delete"] = { en = "Delete", it = "Elimina" },
  ["button.clearSent"] = { en = "Clear sent reports", it = "Elimina le segnalazioni inviate" },
  ["fix.saved"] = { en = "Saved. Send it from Send report.", it = "Salvata. Inviala da Invia segnalazione." },
  ["fix.unavailable"] = {
    en = "Saving is unavailable: the addon's saved settings did not load. Try /reload.",
    it = "Impossibile salvare: le impostazioni salvate dell'addon non sono state caricate. Prova /reload.",
  },
  ["fix.noReason"] = { en = "Pick what is wrong first.", it = "Prima scegli cosa non va." },
  ["fix.exists"] = {
    en = "This line is already saved. Click again to replace it.",
    it = "Questa riga è già salvata. Fai di nuovo clic per sostituirla.",
  },
  ["fix.full"] = {
    en = "%s reports are waiting. Send them and clear them first.",
    it = "%s segnalazioni sono in attesa. Prima inviale ed eliminale.",
  },
  ["fix.tooLong"] = { en = "The note or your version is too long.", it = "La nota o la tua versione è troppo lunga." },
  ["fix.deleted"] = { en = "Deleted.", it = "Eliminata." },
  ["fix.pending.explain"] = {
    en = "Saved reports, kept until you clear them. Click one to change or delete it.",
    it = "Segnalazioni salvate, conservate finché non le elimini. Fai clic su una per modificarla o eliminarla.",
  },
  ["fix.pending.empty"] = { en = "Nothing saved yet.", it = "Nessuna segnalazione salvata." },
  ["fix.copy.step1"] = {
    en = "1. Open the report form: click the address, Ctrl+C, paste it into your browser.",
    it = "1. Apri il modulo: fai clic sull'indirizzo, Ctrl+C, incollalo nel browser.",
  },
  ["fix.copy.step2"] = {
    en = "2. Copy the report: click it (it selects itself), then Ctrl+C.",
    it = "2. Copia la segnalazione: fai clic (si seleziona da sola), poi Ctrl+C.",
  },
  ["fix.copy.step3"] = {
    en = "3. Paste the report into the form's Report box and submit it.",
    it = "3. Incolla la segnalazione nel riquadro Report del modulo e inviala.",
  },
  ["fix.copy.step4"] = {
    en = "4. Sent? Clear the reports you sent:",
    it = "4. Inviata? Elimina le segnalazioni inviate:",
  },
  ["fix.copy.empty"] = {
    en = "Nothing to send yet. In Translations, click a line, choose what is wrong and click Save.",
    it = "Ancora niente da inviare. In Traduzioni fai clic su una riga, scegli cosa non va e fai clic su Salva.",
  },
  ["fix.clear.confirm"] = { en = "Click again to clear %s reports",
    it = "Fai di nuovo clic per eliminare %s segnalazioni" },
  ["fix.cleared"] = { en = "Cleared %s reports", it = "%s segnalazioni eliminate" },
  ["type.quest"] = { en = "Quest", it = "Missione" },
  ["type.gossip"] = { en = "NPC talk", it = "Dialogo PNG" },
  ["type.item"] = { en = "Item", it = "Oggetto" },
  ["type.spell"] = { en = "Spell", it = "Abilità" },
  ["type.book"] = { en = "Book", it = "Libro" },
  ["type.ui"] = { en = "Window text", it = "Testo delle finestre" },
  ["type.objective"] = { en = "Objective", it = "Obiettivo" },
  ["type.area"] = { en = "Area objective", it = "Obiettivo di zona" },
  ["minimap.tip"] = {
    en = "Left-click: report a line · Right-click: menu",
    it = "Clic sinistro: segnala una riga · Clic destro: menu",
  },
  ["minimap.enabled"] = { en = "Translation on", it = "Traduzione attiva" },
  ["minimap.hide"] = { en = "Hide this button", it = "Nascondi questo pulsante" },
  ["reminder.title"] = { en = "Untranslated English", it = "Inglese non tradotto" },
  ["reminder.saved"] = { en = "While you played, the addon collected %s English lines it has no translation for.",
    it = "Mentre giocavi, l'addon ha raccolto %s righe in inglese senza traduzione." },
  ["reminder.ask"] = { en = "Send them in and they will be translated in a future update.",
    it = "Inviale e saranno tradotte in un prossimo aggiornamento." },
  ["reminder.send"] = { en = "Send English", it = "Invia l'inglese" },
  ["reminder.later"] = { en = "Later", it = "Più tardi" },
  ["reminder.stop"] = { en = "Don't remind me again", it = "Non ricordarmelo più" },
  -- the intro window a first install shows once (UI/IntroWindow): an Italian block above an English one, each point
  -- short enough for one line in its block; %s in intro.hold is the reveal key's name
  ["intro.lead"] = { en = "Quest text, NPC talk and tooltips now show in Italian.",
    it = "Missioni, dialoghi dei PNG e tooltip ora sono in italiano." },
  ["intro.hold"] = { en = "Hold %s to see the game's English.",
    it = "Tieni premuto %s per vedere l'inglese del gioco." },
  ["intro.minimap"] = { en = "Minimap button: left-click to report a line, right-click for the menu.",
    it = "Pulsante della minimappa: clic sinistro per segnalare, clic destro per il menu." },
  ["intro.close"] = { en = "Close", it = "Chiudi" },
  ["minimap.sendEnglish"] = { en = "Send collected English (%s)", it = "Invia l'inglese raccolto (%s)" },
  ["minimap.version"] = { en = "Version %s", it = "Versione %s" },
  ["minimap.collected"] = { en = "The collector has %s lines we need. Right-click to send them.",
    it = "La raccolta ha %s righe che ci servono. Clic destro per inviarle." },
}

-- Slash reference on the About page (English: it is the literal grammar, like the chat output).
-- Every top-level verb of UI/Slash and every debug sub-verb (options_spec checks the list).
Text.SLASH = {
  "/fita  (status)  ·  /fita on | off | toggle  ·  /fita version",
  "/fita modifier <key>  (alt, lalt, button4, q …)",
  "/fita togglekey [<key> | none]  (f5, ctrl-j …)",
  "/fita area quests off  ·  /fita marker missing on",
  "/fita nomi [it | en]  (official Italian or original English names)",
  "/fita config [collector | about]  ·  /fita fix  (report a line)",
  "/fita bug  (report a bug or an idea)",
  "/fita voce stop  (with a voice pack: stop the voice and the lines waiting)",
  "/fita collector [on | off | status | path | clear | send [all]]",
  "/fita log [<n>]  (the problem log)  ·  /fita taint  (action-bar taint scan)",
  "/fita debug [hash | quest <id> | item <id> | spell <id>]",
  "/fita debug [gossip | book | objective | fonts | ui [scan]]",
  "/fita debug tooltip [on | off]  (record spell / item tooltip passes)",
}

-- the translation-report issue form the fix window's report is pasted into (.github/ISSUE_TEMPLATE); without it the
-- window would show the report to copy only
Text.FIX_URL = "https://github.com/oLdpZ/oldpz-forever-ita/issues/new?template=translation-report.yml"

-- → en, it; a missing key raises (a typo must fail the spec, not ship a blank).
function Text.get(key, ...)
  local t = Text.T[key]
  assert(t, "OptionsText: no copy for " .. tostring(key))
  if select("#", ...) == 0 then return t.en, t.it end
  return t.en:format(...), t.it:format(...)
end
