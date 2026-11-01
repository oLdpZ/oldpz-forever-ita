# Changelog

What changed in each release of oLd_pZ Forever - Traduzione Italiana, written for players.

Every change that reaches the game adds a line under **Unreleased**, in one of these groups:
**Added** (something new), **Changed**, **Fixed**, **Removed**, **Breaking** (your settings are reset or
an old setting stops working). A release moves those lines under its version number. Versions follow
[Semantic Versioning](https://semver.org/); until the first full release they are test builds. The release
history of WoW Forever Japanese, the addon this one is forked from, stays with that project.

## Unreleased

### Added
- Nomi ufficiali in italiano anche dove li mostra il gioco: oggetti, incantesimi, abilità, zone e fazioni nei tooltip, nella reputazione, nelle abilità, in mercanti, bottino, ricompense, minimappa e mappa. Ogni tipo di nome si sceglie in italiano o in inglese nelle opzioni. Il libro incantesimi resta in inglese: scriverci bloccherebbe le barre azioni in combattimento.
- First Italian build: the interface strings, item flavour text and spell tooltips that Blizzard's own Italian client (retail, itIT) words exactly as Forever does now show in Italian.
- Missioni dei livelli 1–20 tradotte in italiano: circa 1.140 missioni, con titolo, obiettivi, descrizione, testo di avanzamento e di completamento.
- Missioni dei livelli 21–30 tradotte in italiano: circa 450 missioni in più.
- Missioni dei livelli 31–40 tradotte in italiano: circa 460 missioni in più.
- Missioni dei livelli 41–50 tradotte in italiano: circa 480 missioni in più.
- Missioni dei livelli 51–60 tradotte in italiano, comprese incursioni, eventi e reputazioni: circa 1.360 missioni in più.
- Missioni proprie di WoW: Forever (contratti d'artigianato, campeggio, Incursioni dell'Incubo, isole e nuove zone): circa 930 missioni in più. Ora quasi tutto il testo delle missioni è in italiano; restano in inglese solo i titoli che sono nomi propri.
- Libri, lettere, biglietti e targhe in italiano: circa 1.200 pagine, dalle cronache della storia di Azeroth alle lettere delle missioni. Restano in inglese solo le pagine che sono un nome o un'immagine.
- Tooltip delle abilità di tutte le classi (descrizioni ed effetti) e descrizioni degli oggetti in italiano: circa 6.100 righe, con i nomi ufficiali italiani delle abilità, delle erbe e degli oggetti quando esistono.
- Tooltip degli incantesimi usati dagli oggetti (effetti di «Equipaggia:» e «Usa:», consumabili, cavalcature e mascotte) e quasi tutta l'interfaccia in italiano: impostazioni, chat, errori, imprese e statistiche, barbiere, emote, posta e code (circa 6.600 stringhe).
- Nuova impostazione "stile dei nomi": `/fita nomi it` mostra i nomi italiani ufficiali di luoghi, personaggi e oggetti (predefinito), `/fita nomi en` quelli inglesi.
- I nomi sono marcati anche nelle descrizioni ufficiali di oggetti e abilità, così seguono lo stile dei nomi scelto.
- Glossario derivato dai nomi ufficiali, usato per tenere coerenti i nomi in tutte le traduzioni.
- Dialoghi dei PNG in italiano: quasi tutto ciò che dicono i personaggi quando parli con loro, le opzioni di dialogo, i saluti, le urla e le frasi in chat (circa 10.800 righe).
- Righe degli obiettivi nel tracker delle missioni e obiettivi di esplorazione ed evento in italiano.
- Nomi dei PNG e delle creature in italiano nel mondo: nel tooltip (con il titolo sotto il nome, es. «Venditore di Armi»), nei riquadri del bersaglio, del focus e dei boss e sulle targhette sopra la testa. Si usano i nomi del client italiano ufficiale (circa 7.200), gli altri sono tradotti nello stesso stile e i nomi propri senza significato restano come sono. Gli stessi nomi compaiono negli obiettivi, nel tracker e nei testi delle missioni. In combattimento le targhette restano in inglese e tornano italiane alla fine; `/fita nomi en` e il tasto Alt mostrano l'inglese.
- Le segnalazioni dal gioco (una riga tradotta male, un errore o un'idea, l'inglese raccolto) aprono i moduli del progetto su GitHub: il link si copia dalla finestra e si apre nel browser.
- Un personaggio femminile vede la reputazione al femminile: Odiata, Avversa, Onorata, Riverita, Osannata (nel pannello della reputazione, in quello della gilda e nei requisiti delle missioni).
- Tooltip degli ultimi incantesimi rimasti in italiano: abilità delle creature e dei famigli, effetti di eventi, cavalcature e oggetti (circa 2.300 righe). Ora quasi tutti i tooltip delle abilità sono in italiano.

### Fixed
- Missioni, dialoghi, libri e tooltip chiamano ogni PNG con lo stesso nome che ha nel mondo (circa 1.000 testi corretti: «l'alchimista Rollabomba», «re Magni Barbabronzea», «sire Valthalak»).
- Nomi dei PNG più coerenti: i titoli seguono quelli ufficiali (Mercante di Forniture, Specialista, Arcaio, Archibugiere), «Famiglio di …» per i famigli, i PNG di prova numerati restano in inglese; Geologa Guastafesta come nelle missioni ufficiali.
- Nomi più coerenti nelle missioni: oggetti degli obiettivi con il nome ufficiale italiano anche nei livelli 1–20, Babbo Inverno e la Masseria Buongusto, Guardiani della Notte, epiteti dei personaggi, arcidruido, segatronchi e i titoli dei personaggi (guardiano, ispettore, signore supremo).
- Termini dei tooltip come nel client italiano: «Equipaggia:», potenza magica, «Incanta in modo permanente», i nomi ufficiali di erbe e ricette nelle spedizioni; Uther è «l'Araldo della Luce» anche nei libri, nelle missioni e nei dialoghi, e Firebloom è Sbocciafuoco.
- Nomi ufficiali italiani di fazioni e luoghi che prima restavano in inglese: il Circolo della Terra, la Roccaforte di Piumaluna, la Città Vecchia e il Distretto dei Nani di Roccavento, il Salone delle Armi, il Varcolargo, la Locanda del Fiero Leone, la Caverna degli Inganni; «Riverito» nella reputazione e i gradi dei mestieri come nel client (Praticante, Esperto, Specialista).

### Changed
- Alcune righe restano in inglese di proposito (ad esempio dove il gioco mostra testo che non va tradotto): non è una traduzione mancante.
- Controlli più severi prima di pubblicare una traduzione: i nomi del glossario e i segnaposto (come il tuo nome o la tua classe) devono corrispondere all'originale.
