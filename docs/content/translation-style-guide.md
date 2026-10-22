# Guida di stile della traduzione: testi del server, tooltip e interfaccia

version: sg11

> Ciò che riceve un modello che scrive le bozze, insieme a un file di batch, per tradurre in italiano i testi di missione (titolo, obiettivi, descrizione, avanzamento, completamento), i dialoghi dei PNG, le pagine di libri, lettere e targhe, e le descrizioni dei tooltip di oggetti e abilità. Cambiare una regola o un esempio è una nuova versione: si aumenta `version:` (al numero `sg` successivo) e i nomi delle bozze finiscono con il nuovo `-sg<N>`. La sezione **Testo d'interfaccia** fa eccezione: governa le bozze del dizionario dell'interfaccia, che non hanno versione, quindi cambiarla non aumenta nulla.

## Il compito

- Ogni riga del batch è `{"ref", "kind", "en", "targets"}`; le righe di missione (`progress`, `completion`) portano anche `"items"`, i nomi degli oggetti negli obiettivi della missione (spesso vuoto). `kind` è `progress` (il PNG chiede se il compito è fatto, prima della consegna), `completion` (il PNG ringrazia e consegna la ricompensa), `gossip` (ciò che un PNG dice quando gli si parla), `book` (una pagina di libro, lettera, biglietto o targa), uno dei tipi **missione** `quest_title` / `quest_objectives` / `quest_description` (vedi **Missioni**) o uno dei tipi **tooltip** `item_description`, `spell_description`, `spell_aura`, le cui righe portano anche `"slots"` (vedi **Tooltip**).
- Scrivi una riga di uscita per ogni riga del batch: `{"ref": "<il ref della riga>", "it": "<italiano>"}`, un oggetto JSON per riga, nient'altro. Ogni ref esattamente una volta.
- Se una riga è solo un nome proprio che resta uguale (o non c'è nulla da tradurre), scrivi `{"ref": "…", "it": null}`.
- Traduci il significato di tutto il testo inglese. Non aggiungere frasi, non toglierne, non riassumere, non spiegare.

## Terminologia ufficiale

- Il riferimento è il client ufficiale italiano di World of Warcraft (itIT): si usano le sue parole per classi, razze, abilità, oggetti, zone, fazioni e interfaccia (`quest` → `missione`, `Health` → `Salute`, `Stamina` → `Tempra`, `Hearthstone` → `Pietra del Ritorno`).
- I nomi propri ufficiali italiani vengono dal glossario (`pipeline/glossario_ufficiale.tsv`, generato dalle tabelle itIT). Un nome che il glossario elenca si scrive come lo dà il glossario (`Stormwind` → `Roccavento`, `Elwynn Forest` → `Foresta di Elwynn`).
- Un nome che il glossario non elenca (un personaggio, una creatura o un luogo che il client italiano non traduce) resta esattamente come lo scrive l'inglese: `Marshal McBride`, `Hogger`. Non inventare traduzioni di nomi.
- Un titolo o un nome comune usato da solo si traduce, anche se l'inglese lo scrive maiuscolo: `the Captain` → `il capitano`, `the Warchief` → `il Capoguerra`, `the Inn` → `la locanda`.

## Lessico fissato (sg11)

Termini ricorrenti che il glossario non copre, o copre solo dentro un nome più lungo, decisi una volta per tutti i lotti (sg2 raccoglie le decisioni della revisione delle missioni 1–20, sg3 e sg4 quelle dei dialoghi dei PNG, sg5 quelle della revisione delle missioni 21–30, sg6 quelle della revisione delle missioni 31–40, sg7 quelle della revisione delle missioni 41–50, sg8 quelle della revisione delle missioni 51–60, sg9 quelle della revisione delle missioni senza livello, sg10 quelle della revisione dei libri, sg11 quelle del pilota dei tooltip). Valgono come il glossario: un termine della tabella si scrive sempre così.

| Inglese | Italiano | Non |
|---|---|---|
| People's Militia | Milizia del Popolo | Brigata del Popolo |
| The Den (Valle delle Sfide) | Antro del Tirocinio | la Tana |
| (the) Talon Den, «the Den» sul Picco di Petrartiglio | Eremo Grinfialunga (zona ufficiale); il titolo 1089 «The Den» resta inglese, perché il controllo vi pretende Antro del Tirocinio | Antro del Tirocinio |
| (The) Barrens | Savane (le Savane) | Barrens |
| Stonemasons' Guild, the Stonemasons | la Gilda dei Tagliapietre, i Tagliapietre (da Mantello dei Tagliapietre) | Stonemasons' Guild |
| Uther the Lightbringer | Uther il Portatore di Luce | Uther the Lightbringer |
| Silvermoon | Lunargenta (da Resti di Lunargenta) | Silvermoon |
| the Frozen Throne; Frostmourne | il Trono di Ghiaccio; Gelidanima | Frozen Throne, Frostmourne |
| Icecrown | Corona di Ghiaccio | Icecrown |
| Council / Order / Guardians of Tirisfal; Guardian (la carica) | Consiglio / Ordine / Guardiani di Tirisfal; il Guardiano, la Guardiana, maiuscolo anche davanti al nome | Order of Tirisfal |
| the Great Dark (Beyond) | la Grande Oscurità (dell'Oltre) | Grande Oscurità Esterna |
| titoli degli Aspetti | la Protettrice della Vita, la Sognatrice, il Tessitore di Incantesimi, il Senza Tempo, il Custode della Terra, Aspetto della Morte | il Senzatempo |
| sin'dorei, quel'dorei, kaldorei | minuscolo, come nome di popolo | Sin'dorei |
| Plaguelands | Terre Infette | Plaguelands |
| Silver Hand / Knights of the Silver Hand | Mano d'Argento / Cavalieri della Mano d'Argento | Silver Hand |
| Twilight's Hammer | Martello del Crepuscolo | Twilight's Hammer |
| Shadow Council | Concilio dell'Ombra | Shadow Council |
| Well of Eternity | Pozzo dell'Eternità | Well of Eternity |
| Emerald Dream | Sogno di Smeraldo | Emerald Dream |
| Earthmother | Madre Terra | Earthmother |
| Greatmother | Grande Madre | Greatmother |
| the Dark Lady | la Dama Oscura | Dark Lady |
| Venture Co. / Venture Company | S.P.R. & Co. | Venture Co. |
| SI:7 | IR:7 | SI:7 |
| Explorers' League | Lega degli Esploratori | Explorers' League |
| Great Forge | Grande Forgia | Great Forge |
| Dark Iron | Ferroscuro | Dark Iron |
| Blackrock | Roccianera | Blackrock |
| Warsong (clan) | Cantaguerra | Warsong |
| Sentinels | Sentinelle | Sentinels |
| Highborne | Alti Nobili | Highborne |
| Deathstalker(s) | Inseguitore/i della Morte | Deathstalker |
| voidwalker | ombra del Vuoto | voidwalker |
| moonkin | lunagufo / lunagufi | moonkin |
| furbolg | mezzorso / mezzorsi | furbolg |
| quilboar (razza) | verrospino / verrospini (minuscolo) | Quilboar |
| pet (di cacciatore o stregone) | famiglio | pet |
| Twisting Nether | Distorsione Fatua | Twisting Nether |
| the Nether (da solo) | Nether | — |
| Mage Quarter | Quartiere dei Maghi | Quartiere del Mago |
| Magic Quarter | Quartiere della Magia | Magic Quarter |
| Trade Quarter / Trade District | Quartiere del Commercio | Trade Quarter |
| Rogues' Quarter | Quartiere dei Ladri | Rogues' Quarter |
| War Quarter | Quartiere della Guerra | War Quarter |
| Cathedral of Light | Cattedrale della Luce | Cathedral of Light |
| Temple of the Moon | Tempio della Luna | Temple of the Moon |
| Valley of Strength / Spirits / Honor / Trials | Valle della Forza / degli Spiriti / dell'Onore / delle Sfide | Valley of … |
| Sepulcher (zona) | la Mausolea (femminile: «alla Mausolea», «nella Mausolea») | a Mausolea |
| wind rider / gryphon / hippogryph / bat master | maestro delle viverne / dei grifoni / degli ippogrifi / dei pipistrelli | — |
| Apothecary / Mountaineer / Brave (titoli) | speziale / montanaro / valoroso | — |
| (Rank 2) | (Grado 2) | (Rank 2) |
| Lunar Festival | Celebrazione della Luna | Lunar Festival |
| Hallow's End | Veglia delle Ombre | Hallow's End |
| Winter Veil / Feast of Winter Veil / Feast of Great-Winter | Grande Inverno / Festa del Grande Inverno («Buon Grande Inverno», «Buona Festa del Grande Inverno») | Winter Veil, festa di Great-Winter |
| Greatfather Winter / Great-father Winter | Babbo Inverno (da Birra Stagionale di Babbo Inverno) | Greatfather Winter |
| Smokywood Pastures (anche «Smokeywood») | la Masseria Buongusto (dagli oggetti ufficiali: «della», «dalla Masseria Buongusto») | Smokywood Pastures |
| Wickerman (festa, fantoccio) | Uomo di Paglia | Wickerman |
| Light's Hope (Chapel) | Cappella della Luce | Light's Hope |
| Stranglethorn (Vale) | Rovotorto (Valle di Rovotorto) | Stranglethorn |
| Night Watch | Guardiani della Notte | Night Watch |
| Hydraxis | Idraxis (Seguaci di Idraxis) | Hydraxis |
| Swordsmith / Axesmith / Weaponsmith | Fabbro di Spade / d'Asce / d'Armi | forgiatore |
| Stable Master | stalliere | maestro di stalla |
| Arch Druid | arcidruido, minuscolo come gli altri titoli, anche da solo («l'arcidruido Staghelm», «In aiuto dell'arcidruido Runetotem», «L'arcidruido vuole…») | l'Arcidruido |
| Deathwing | Alamorte | Deathwing |
| Lich King | Re dei Lich | Lich King |
| Old Gods | Dei Antichi | Old Gods |
| Eastern Kingdoms | Regni Orientali | Eastern Kingdoms |
| Ashbringer | il Brandicenere | Ashbringer |
| Frostwolf (clan) | Lupi Bianchi | Frostwolf |
| Stormpike (esercito, clan; non il cognome) | Piccatonante | Stormpike |
| Iceblood (Torre, Presidio, Fortilizio) | Brinarossa (Torre di Brinarossa) | Iceblood |
| Snowfall (luogo) | Nevealta | Snowfall |
| Stormwind Keep | Castello di Roccavento | fortezza di Roccavento |
| Sunken Temple | Tempio di Atal'Hakkar | Tempio Sommerso |
| Burning Legion | Legione Infuocata | — |
| War of the Ancients | Guerra degli Antichi | War of the Ancients |
| (the) Sundering | la Separazione | Frattura, Sundering |
| Valley of Wisdom | Valle della Saggezza | — |
| Highlord / Warmaster / Windlord | gran signore / maestro di guerra / Signore del Vento | — |
| High Tinker | alto inventore | gran tecnico |
| witch doctor | santone | stregone |
| dragonspawn | dragobestia / dragobestie | — |
| crypt fiend | ragno delle cripte | crypt fiend |
| spirit healer | guaritore degli spiriti | — |
| Mining | Estrazione | — |
| Friendly / Honored / Revered / Exalted (reputazione) | Amichevole / Onorato / Reverito / Osannato | — |
| Stonesplinter (tribù) | Scheggiadura | Pietrarotta |
| Earthen Ring, Old Town, Dwarven District, Hall of Arms, The Drag, Tinker Town, Lion's Pride Inn, Gilded Rose, Hall of the Brave, Forlorn Cavern, Scarab Gong, silithyst | restano inglesi | Anello della Terra, Città Vecchia |
| Alterac: luoghi senza forma nel glossario (Frostwolf Relief Hut, Stormpike Aid Station, Dun Baldar North/South Bunker, East/West Frostwolf Tower) | restano inglesi interi | — |
| High Executor | alto esecutore / alta esecutrice (secondo il personaggio: l'alta esecutrice Darthalia) | somma esecutrice |
| High Priest / High Priestess | sommo sacerdote / somma sacerdotessa | alta sacerdotessa |
| High Mage / High Sorcerer | sommo mago / alto stregone | — |
| Dragonmaw (clan, testo libero) | Fauci di Drago (le Fauci di Drago, gli orchi delle Fauci di Drago; dagli oggetti ufficiali) | Dragonmaw, gli orchi Fauci di Drago |
| Lady Sylvanas | Lady Sylvanas (L maiuscola) | lady Sylvanas |
| Lady + nome | Lady sempre maiuscola: Lady Proudmoore, Lady Jaina Proudmoore, anche nella grafia inglese «Lady Proudmore»; «Miss Proudmoore» resta «la signorina Proudmoore» | lady Proudmoore |
| Magus (titolo) | magus («il magus Voidglare», «il magus Tirth»; dall'oggetto Testa della Magus Rimtori) | mago Voidglare, il Magus |
| Prospector (titolo) | prospettore («il prospettore Ironband»; dagli oggetti Piccone da Prospettore…) | cercatore |
| Witherbark / Crushridge / Boulderfist / Shadowforge (testo libero) | Scorzasecca / Sfasciacresta / Rocciadura / Forgiascura («gli Scorzasecca»; dalle zone e dagli oggetti ufficiali) | i Witherbark |
| outrunner(s) | staffetta / staffette (Ashenvale Outrunners → Staffette di Valtetra; dagli oggetti … della Staffetta) | esploratori, Outrunner |
| dark riders | cavalieri oscuri | Dark Rider |
| Orb (catena di Orahil) | come gli oggetti ufficiali: Infernal Orb → Globo Infernale («il globo»), Cleansed Infernal Orb → Sfera Infernale Purificata («la sfera purificata»), Orb of Noh'Orahil → Globo di Noh'Orahil | un'unica parola per tutti |
| Sparklematic 5200 | la Lavatutto 5200 (femminile; dalla Scatola Incartata dalla Lavatutto) | lo Sparklematic 5200 |
| Gelkis Village | Villaggio dei Gelkis (zona ufficiale) | — |
| Mithril Order, Scarlet Brotherhood, Magram Village | restano inglesi (nessuna forma ufficiale verificabile) | Ordine del Mithril, confratelli scarlatti, villaggio dei Magram |
| Epiteti di una parola comune (the Wise, the Ancient, the Devout, the Swift, the Foul, the Lost…) | tradotti, articolo minuscolo ed epiteto maiuscolo: Uthek la Saggia, Galvan l'Antico, Raleigh il Devoto, Helgrum il Rapido, Hank il Martello, Aturk l'Incudine, Balgaras il Lurido, Theldurin il Perduto, Delgren il Purificatore, Taragaman il Famelico (ufficiale) | Uthek the Wise, Raleigh il devoto |
| Epiteti coniati o giochi di parole (Gakin the Darkbinder, Rethiel the Greenwarden, Neptulon the Tidehunter, Zardeth the Black Claw, Shoni the Shilent) | restano inglesi con il nome | Rethiel il Greenwarden |
| felhunter | vilsegugio / vilsegugi (da Evocazione: Vilsegugio) | felhunter |
| Blackfathom (Deeps), il luogo | Abissi di Fondocupo («negli Abissi di Fondocupo»); Fondocupo da solo è la fazione | a Fondocupo |
| Steelsnap / Sarltooth / Gobbler / Grimson (testo libero) | Ganascia / Dentesauro / Glugot / Rocciatorva (da Costola di Ganascia, Artigli di Dentesauro, Testa di Glugot, Testa di Rocciatorva; «Rocciatorva il Pallido») | — |
| Thistlefur (tribù) | Mantocardo | Thistlefur |
| Ravenholdt Manor | Maniero dei Corvolesto | maniero di Corvolesto |
| Tarren Mill | il Mulino di Tarren («al», «del», «dal Mulino di Tarren») | a / di Mulino di Tarren |
| Tinkmaster / Dawnwatcher / Windwatcher / Cliffwatcher / Argent Guard (titoli) | mastro inventore / vegliante dell'alba / osservatore dei venti / guardiacolli / guardia argentea | Dawnwatcher, the Windwatcher |
| The Affray (la prova dell'Isola della Contesa) | la Rissa | — |
| Mekgineer, Zardeth the Black Claw, Druids of the Fang, Scythe of Elune, Eye of Azora, Nightbane (worgen) | restano inglesi (nessuna forma ufficiale verificabile) | Falce di Elune, Occhio di Azora, Druidi della Zanna |
| Watcher (titolo) | guardiano / guardiana («il guardiano Mahar Ba», «la guardiana Sarah Ladimore»); stone watcher → guardiano di pietra | osservatore |
| Surveyor (titolo) | ispettore / ispettrice; Junior Surveyor → ispettore apprendista («l'<ispettore/ispettrice> apprendista {name}»), Senior Surveyor → ispettore anziano | rilevatore, ispettore capo |
| Overlord (titolo) | signore supremo («il signore supremo Mok'Morokk») | il supremo |
| Huntsman (titolo) | predatore («il predatore Markhor»; dagli oggetti Teschio del Predatore Malkhor, Stivali del Predatore…) | cacciatore |
| Shredder (goblin) | segatronchi, maschile invariabile («il segatronchi», «i segatronchi XT:4 e XT:9»; da Segatronchi d'Osso Bianco, Manuale di Funzionamento del Segatronchi) | shredder, trinciatrice, trituratore |
| wildkin, owlbeast | silvagufo / silvagufi (da Penna di Silvagufo); nelle creature degli obiettivi resta l'inglese (Savage Owlbeast) | bestiagufo |
| Zanzil the Outcast | Zanzil l'Esiliato | Zanzil il Reietto (si confonde con i Reietti) |
| Hakkar the Soulflayer, the Soulflayer | Hakkar lo Scortica Anime, senza virgole (dall'abilità ufficiale); da solo «lo Scortica Anime» | Hakkar, lo Scortica Anime,; il Soulflayer |
| (The) Hinterlands | Entroterre, zona ufficiale, femminile plurale («nelle Entroterre», «delle Entroterre», «Verso le Entroterre») | negli Hinterlands |
| Grimlok (testo libero) | Tetrok (da Maglia Tribale di Tetrok, Guisarma di Tetrok); negli obiettivi resta Grimlok, come Ganascia/Glugot | — |
| Hatetalon | cognome (Edana Hatetalon) e luogo (le pietre Hatetalon): restano inglesi; Bramartiglio solo nell'oggetto Corno di Bramartiglio | Bramartiglio nel testo libero |
| Broken Alliances (titolo) | Alleanze infrante | Alleanze spezzate |
| Discs of Norgannon, Stone Watcher of Norgannon, Plates of Uldum, Tablet of the Seven, Seal of the Earth | restano inglesi («i Discs of Norgannon», «lo Stone Watcher of Norgannon»; nessuna forma ufficiale verificabile); «i dischi», «il guardiano di pietra» da soli si traducono | Dischi di Norgannon, Tavoletta dei Sette, Sigillo della Terra |
| Windcaller (titolo) | evocatore / evocatrice dei venti («l'evocatore dei venti Proudhorn», «all'evocatrice dei venti Yessendra») | evocatore del vento, invocatore dei venti |
| Fleet Master (titolo) | ammiraglio («l'ammiraglio Seahorn», «l'ammiraglio Firallon»); negli obiettivi la creatura da uccidere resta inglese (`Uccidi Fleet Master Seahorn`) | comandante della flotta |
| Quartermaster | quartiermastro / quartiermastri (dallo Scrigno del Quartiermastro Zigris): «il quartiermastro dei Lupi Bianchi», «a Hasana, quartiermastro della Granbarricata» | furiere, intendente |
| Keeper of the Rolls | il Custode degli Archivi, maiuscolo (dalla Lettera dal Custode degli Archivi) | custode dei registri |
| Warden (titolo) | sorvegliante («il sorvegliante Haro»); il direttore di una prigione resta direttore (il direttore Thelwater); A Warden of the Alliance/Horde (Settimana dei Bambini) → «Un tutore dell'Alleanza/dell'Orda». Custode è Keeper; gli oggetti Warden's… (… del Custode) restano come sono | custode Haro |
| X the Elder, Elder X (Celebrazione della Luna e altri anziani) | «l'anziano X», «l'anziana X» se l'inglese mostra una donna (l'anziana Ragetotem: «her days»); nei titoli «L'anziano Morndeep»; il nome resta inglese, cognomi di tribù compresi (l'anziano Thunderhorn, Winterhoof, Grimtotem) | Morndeep l'Anziano, l'anziano Corno Tonante |
| Lord Valthalak | «lord Valthalak» nel testo libero (anche «il frammento sinistro dell'amuleto di lord Valthalak»); negli oggetti la forma ufficiale «Sire» (Frammento Sinistro dell'Amuleto di Sire Valthalak, Amuleto di Sire Valthalak) | Sire Valthalak nel testo libero |
| X Dragonflight, the X Flight (stormi dei draghi) | la forma della fazione, maiuscola: Stormo dei Draghi Neri / Rossi / Blu / Verdi / di Bronzo, anche per «the Black Flight» e per le righe minuscole («lo stormo nero»); il draco campione dello Stormo dei Draghi Blu; Ysera's Dragonflight → Stormo di Ysera. I nomi ufficiali di oggetti e abilità restano: Muta dello Stormo Nero, Fiamme dello Stormo Nero. «lo stormo», «gli stormi» da soli e «lo stormo cromatico» sono nomi comuni | Stormo Nero nel testo libero, stormo dei draghi verdi |
| dreadlord | signore del terrore, minuscolo (nome comune) | Signore del Terrore |
| Blazerunner | Fiammafulgida (dall'abilità Aura di Fiammafulgida) | Blazerunner |
| Emberstrife | Braceardente (dalla Tana di Braceardente); Scryer → Alasaggia e Chronalis → Tac nel testo libero (dai Teschi di Alasaggia e di Tac); le creature da uccidere negli obiettivi restano inglesi | Emberstrife nel testo libero |
| Cathedral District, Altar of Zanza, Firebloom | restano inglesi (nessuna forma ufficiale verificabile): «nel Cathedral District di Roccavento», «l'Altar of Zanza», «Porta 20 Firebloom» | quartiere della Cattedrale, Altare di Zanza |
| Thorium Bar (e gli altri Bar) | Lingotto di Torio (ufficiale); senza numero «i lingotti di torio» | barre di torio |
| Warsong Outriders / Outrider (oggetti) | Predoni Cantaguerra (fazione ufficiale); negli oggetti la forma ufficiale «Perlustratore» (Kit Curativo di Base dei Perlustratori) | — |
| Myranda the Hag | Myranda la Megera | Myranda la Strega |
| Al'tabim the All-Seeing | Al'tabim l'Onniveggente | Al'tabim l'Onnisciente |
| the Blood God (Hakkar) | il Dio del Sangue, maiuscolo come titolo; «un antico dio del sangue» generico minuscolo | il dio del sangue Hakkar |
| C'Thun | C'thun, come il glossario (Armate di C'thun, Occhio di C'thun) | C'Thun |
| Warbringer (Orda, campi di battaglia) | araldo della guerra | araldo di guerra, Warbringer |
| Primal (Primal Torntusk) | la primordiale Torntusk (donna: «her mate») | il primordiale Torntusk |
| Peacekeeper(s) (Zephras) | i Pacificatori, il gruppo, maiuscolo (dagli oggetti Cintura del Pacificatore Shen'dorei…); il singolo pacificatore / pacificatrice, minuscolo («il pacificatore Vaaniel», «era una pacificatrice»); Valennia Stormfist è la capitana dei Pacificatori | custodi della pace, guardiani della pace |
| leyline(s) | linea / linee di potere; l'abilità razziale Read Leyline resta inglese | linee di energia |
| Supreme Magister / High Elder / Grand Skyseer | magistro supremo / alto anziano, alta anziana / gran scrutacieli | supremo magistro, anziano supremo |
| skysight | lo skysight, come l'abilità razziale Skysight | la vista del cielo |
| Constable Aonda | la conestabile Aonda (donna: «a good woman») | il conestabile Aonda |
| Deathguard + nome | il guardiamorte X, minuscolo, invariabile (dal Mantello del Guardiamorte); l'articolo segue il personaggio, maschile salvo che l'inglese mostri una donna (la guardiamorte Linnea); più persone «i guardiamorte»; il corpo armato resta la Guardia della Morte («un membro della Guardia della Morte») | la Guardia della Morte Dillinger |
| Druid of the Claw | druido / druida dell'Artiglio, titolo minuscolo («la druida dell'Artiglio Alara Grovemender»); il titolo di missione «Druido dell'Artiglio» | il Druido dell'Artiglio |
| Nightmare Incursion(s) | Incursione / Incursioni dell'Incubo, maiuscola («nell'Incursione dell'Incubo di Feralas»); i titoli «Missione di Boscovespro I: sconfiggere i worgen», «Missione delle Entroterre XVI: salvare …», infinito minuscolo dopo i due punti | incursione dell'Incubo, Nightmare Incursion, Missione a Valtetra |
| Field Captain | capitano / capitana di campo, davanti al nome («dalla capitana di campo Hannalah», «dal capitano di campo Arunnel») | Hannalah, capitano di campo; il capitano Palandar |
| Dreamwarden | sorvegliante del Sogno («il sorvegliante del Sogno Thalinar», «la sorvegliante del Sogno Amalia»; senza genere noto «da Laninar, sorvegliante del Sogno,») | Dreamwarden |
| Oracle Glade / Oracle Tree | la Radura dell'Oracolo (zona ufficiale: «nella», «dalla Radura dell'Oracolo») / l'Albero dell'Oracolo; l'oggetto Oracle Tree Bark resta inglese | Oracle Glade, Oracle Tree |
| Rotting Orchard, Greymane Wall, Durnholde Keep | Frutteto Marcescente, Muro dei Mantogrigio, Forte Durnholde (zone ufficiali), anche nelle missioni dei livelli 1–60 | Rotting Orchard, Greymane Wall |
| Darkspear Islands | Isole dei Lanciascura (come Riva dei Lanciascura, Stivali dei Lanciascura) | Isole Lanciascura |
| War of the Three Hammers | Guerra dei Tre Martelli | War of the Three Hammers |
| Great Bear Spirit / Great Cat Spirit | Grande Spirito Ursino / Grande Spirito Felino; The Great Ursera Spirit → Il Grande Spirito Ursera | Great Bear Spirit |
| Long Vigil | la Lunga Veglia | Long Vigil |
| Great Sundering | la Grande Separazione (come la Separazione) | Frattura, grande Separazione |
| dragonkin | dragoide / dragoidi (da Calma Dragoide, Individua Dragoidi) | draconidi |
| bat rider / Batrider | cavalcatore di pipistrelli («al cavalcatore di pipistrelli Pele'keiki») | cavaliere di pipistrelli |
| Witch Doctor Zalazane | il santone Zalazane; dove l'inglese dice warlock, lo stregone Zalazane | lo stregone Zalazane per witchdoctor |
| Wrenix the Wretched | Wrenix il Miserabile | — |
| Rot Hide (gnoll) | Pellemarcia nel testo libero (da Icore di Pellemarcia: «gli gnoll Pellemarcia», «i Pellemarcia»); negli obiettivi le creature restano inglesi (Rot Hide Graverobber) | i Rot Hide |
| hunter trainer | istruttore / istruttrice dei cacciatori, minuscolo | istruttore dei Cacciatori |
| Keeper (titolo) / Warden delle Segrete | il custode Remulos, il custode del bosco; Warden Thelwater è il direttore anche nei dialoghi («Morte al direttore!») | il Custode, il guardiano delle Segrete |
| Craftsman's Writ / Camping 101 | Contratto d'Artigianato: <oggetto nella forma ufficiale>; Campeggio 101: <professione ufficiale> (Alchimia, Forgiatura, Incantamento, Ingegneria, Erbalismo, Estrazione, Scuoiatura, Sartoria, Conciatura, Pesca, Cucina, Primo Soccorso) | Campeggio 101: la cucina |
| Gyromatic Micro-Adjuster | Microavvitatore Giromatico (lo stesso oggetto dell'ufficiale Gyromatic Micro-Adjustor) | — |

Regole che accompagnano la tabella:

- **Cognomi dei PNG restano inglesi** (Thunderbrew, Proudmoore, Stonefield, Windrunner, Longshore, Bloodhoof come cognome di Cairne o Baine), anche quando un oggetto del glossario li traduce: «nonna Stonefield» e «Nota di Nonna Pietradura» convivono. Così Rend Blackhand (Testa di Rend Manonera), il barone Rivendare (Testa del Barone Fieramorte), Ras Frostwhisper (Testa Umana di Ras Soffiogelo), Mor Grayhoof, il signore della guerra Goretooth (Ordine del Signore della Guerra Zannatruce), Andre Firebeard, Edana Hatetalon: nel testo libero il cognome inglese, nel nome di un oggetto la forma ufficiale. Se il controllo dà errore, si lascia la forma che il controllo accetta; quando il controllo impone la forma ufficiale in un titolo (7761 «Lettera di Manonera», dall'oggetto Blackhand's Command), il testo libero di quella catena concorda («-Capoguerra Rend Manonera» nella lettera stessa). Se il controllo pretende la forma ufficiale di un cognome che è anche un luogo o una fazione, la frase non deve far leggere il luogo: il cognome va con il titolo («dai riposo allo spirito del thane Forgiamara», e «Faldrim Forgiamara» nella stessa catena), la fazione entra nella frase per quello che è («Il capo dei Corvolesto, lord Ravenholdt, …»), mai «lo spirito di Forgiamara» o «lord Ravenholdt dei Corvolesto».
- **`{class}` non prende prefissi**: `Arch$C` non diventa «l'arci{class}» (darebbe «arciMago»); si riscrive con una parola intera e il segnaposto altrove («L'arcimago Xylem attende il tuo arrivo, {class}.»).
- **Tribù, clan e gruppi** (non cognomi) prendono la forma ufficiale ricavabile dal glossario di zone, oggetti e fazioni: Razormane → Chiomaguzza, Bristleback → Mantotergo, Darkspear → Lanciascura, Frostmane → Mantogelido, Gnarlpine → Mordipigna, Winterhoof → Zoccolo Artico, Thunderhorn → Corno Tonante, Venomtail → Codavenefica, Bloodfeather → Piumarossa, Grimtotem → Totem Truce. Se non è ricavabile, resta inglese.
- **Nomi ricavati da oggetti ufficiali** sono ammessi allo stesso modo: `Darkmoon Cards` → `Carte di Lunacupa` (dagli oggetti `Carta di Lunacupa: …`). Senza una forma ufficiale resta il nome inglese dell'oggetto (`Darkmoon Faire Prize Ticket`); `Fiera di Lunacupa` solo dove si parla della fiera stessa.
- **Ravenholdt** persona resta inglese; `Corvolesto` solo per il maniero e la fazione. **Lord + nome** di un nobile: `lord` minuscolo, come gli altri titoli (lord Valthalak, lord Incendius); `Sire` solo dove è il nome ufficiale di un oggetto. **Anziano/anziana**: maschile salvo che l'inglese mostri una donna.
- **Un titolo prima di un nome è minuscolo** (il maresciallo McBride, l'esecutore Arren, la sacerdotessa Alathea, il sommo sacerdote), salvo una forma del glossario che il controllo pretende maiuscola.
- **I nomi composti di creature** che contengono un termine del glossario, di classe, di razza o di zona (Ice Claw Bear, Armored Scorpid, Redridge Mongrel, Stonesplinter Shaman) restano interi in inglese; il controllo dà solo un avviso. Mai costruzioni come «uno Scorpide, l'Armored Scorpid» o «Bruti di Crestarossa» aggiunte per il controllo.
- **Nomi di abilità** che il glossario non elenca (Lesser Heal) restano inglesi.
- **Feste e personaggi stagionali** prendono la forma della tabella, ricavata dagli oggetti ufficiali; una festa o un personaggio senza forma ufficiale ricavabile (Children's Week, Harvest Festival, Brewfest) resta inglese. Greatfather Winter è Babbo Inverno, Smokywood Pastures la Masseria Buongusto.
- **Un nome senza forma ufficiale verificabile resta inglese**, anche se una traduzione sembra ovvia: Gnomeregan Exiles, Apothecarium, Royal Apothecary Society, Shattered Hand, Cult of the Damned, Earthen Ring, Feathermoon Stronghold, Camp Taurajo, Brotherhood of the Light. Non inventarne una (`Saluto Infranto`, `Torre Orientale dei Lupi Bianchi`).
- **Il titolo concorda con il genere del personaggio** che lo porta: l'alta esecutrice Darthalia, la somma sacerdotessa. Se il genere non si conosce, un'apposizione senza articolo (`a Selgorm, vegliante dell'alba,`).
- **Un titolo coniato** (Tinkmaster, Dawnwatcher, Windwatcher) si traduce in una sola forma, quella della tabella, in ogni campo; una parola inventata senza senso italiano (Mekgineer) resta inglese come parte del nome.
- **Oggetti e creature negli obiettivi** (`quest_objectives`): un oggetto con una forma nel glossario ufficiale per quel nome esatto si scrive nella forma ufficiale, anche se la riga del lotto non la elenca in `glossary`, al singolare dopo il numero come nel tracker (`Porta 10 Ascia Usurata`, `Porta 3 Verga della Canalizzazione`); senza una forma ufficiale resta intero in inglese, come lo mostra il tracker (`Uccidi 10 Syndicate Rogue`): si toglie solo la -s del plurale regolare in fondo al nome; un plurale irregolare o dentro il nome resta come lo scrive l'inglese della riga (`Scarlet Magi`, `Syndicate Thieves`, `Diseased Wolves`, `Sons of Cenarius`, `Bottles of Whispering Elixir`). Le creature restano inglesi negli obiettivi anche quando il testo libero le traduce (`Uccidi Gobbler…`, ma «Glugot» nella descrizione). Il Lessico vale per il testo libero, non dentro un nome di creatura (`Venture Co. Patroller`, `Dragonmaw Grunt`). Un capo da uccidere resta inglese con il titolo e l'epiteto (`Uccidi High Inquisitor Whitemane, Scarlet Commander Mograine, Herod, the Scarlet Champion e Houndmaster Loksey`), e le due versioni di una missione gemella (Orda e Alleanza) dicono la stessa cosa. La regola vale per le missioni di ogni livello. Senza un numero davanti, l'oggetto ufficiale va al plurale che la frase chiede (`Raccogli i Collari Roventi`, `frantuma i Picconi da Prospettore`); un nome del glossario che copre solo una parte del nome inglese non conta (`Soft-shelled Clam Meat` resta intero, anche se `Clam Meat` è `Mollusco`).
- **Epiteti** («X the Y»): un epiteto di una parola comune si traduce, sempre nello stesso modo, con l'articolo minuscolo e l'epiteto maiuscolo come negli oggetti ufficiali (`Testa di Lathoric il Nero`, `Cuore di Taragaman il Famelico`): `Uthek la Saggia`, `Raleigh il Devoto`, `Hank il Martello`. L'articolo segue il genere del personaggio (Uthek è una donna). Un epiteto coniato o un gioco di parole resta inglese con il nome (`Gakin the Darkbinder`, `Shoni the Shilent`). Negli obiettivi una creatura da uccidere resta inglese intera, epiteto compreso, come la mostra il tracker (`Uccidi Balgaras the Foul`, ma «Balgaras il Lurido» nella descrizione); un personaggio da cercare, a cui parlare o portare qualcosa prende la forma tradotta (`Parla con Uthek la Saggia`).
- **Una coppia di genere** contiene parole singole, senza spazi né apostrofi (`<un/una> fier<o/a>`, non `<un eroe/un'eroina>`); se non si può, una forma neutra.

## Il giocatore si dà del "tu"

- Chi parla al giocatore gli dà del **tu**, come fa il client italiano (`Porta queste pelli a Marshal McBride.`, `Grazie, {name}, hai fatto molto per noi.`). Il **voi** solo quando l'inglese si rivolge chiaramente a un gruppo.
- Un nobile, un re o un essere antico può avere un tono solenne, ma continua a dare del tu (`Hai dimostrato il tuo valore, campione.`).

## Voce

Deduci chi parla dal testo (chi parla così, a chi) e mantieni la voce per tutta la riga.

| Chi parla | Voce |
|---|---|
| sacerdoti, druidi, guaritori, studiosi gentili | cortese, pacata |
| anziani, nobili, esseri antichi o regali | solenne, frasi ampie |
| soldati, orchi, Reietti, tipi duri o militari | secca, diretta, frasi brevi |
| allegri, informali, mercanti, goblin | colloquiale, vivace |
| poco chiaro | neutra, senza un carattere forte |

- Rivolgiti al giocatore come fa l'inglese (`{name}`, `{class}`, "friend" → `amico`).
- L'avanzamento è breve, un po' impaziente o speranzoso; il completamento è caloroso o pratico; il dialogo può avere colore, ma dice solo ciò che dice l'inglese.

## Genere del giocatore

- L'italiano concorda con il genere: dove il genere del giocatore conta, scrivi una coppia `<maschile/femminile>` e l'addon sceglie il ramo giusto (`Sei <stato/stata> <coraggioso/coraggiosa>.`, `<il/la>`, `<caro/cara>`).
- La coppia contiene solo le parole che cambiano, senza spazi ai bordi. Dove si può, preferisci una forma che vada bene per entrambi (`Hai dimostrato coraggio.`).
- `$G<maschile>:<femminile>;` nell'inglese significa che il testo cambia con il genere: rendilo con una coppia `<m/f>` o con una forma neutra, mai con il codice `$G`.

## Segnaposto, paragrafi e numeri

- `{name}`, `{class}` e `{race}` sono il nome, la classe e la razza del giocatore, inseriti dal gioco. Mantieni ogni segnaposto esattamente com'è, tante volte quante nell'inglese.
- `$` seguito da cifre e `w` (`$1997w`) è un numero che il gioco inserisce: mantienilo esattamente com'è, tutti.
- L'inglese separa i paragrafi con una riga vuota: l'italiano ha lo stesso numero di paragrafi, separati da una riga vuota.
- I numeri restano gli stessi valori. Scrivi una cifra solo per un numero che l'inglese scrive come cifra o come parola numerica.
- `...` resta `...` (o `…`); la punteggiatura segue l'italiano (virgolette `«»` o `"` come nel client, nessuno spazio prima di `!` e `?`).

## Dialoghi dei PNG (righe che un PNG dice, urla, sussurra o mima)

- `%s` è il nome del PNG che parla, inserito dal gioco (`%s goes into a frenzy!`). Mantieni ogni `%s`, tanti quanti nell'inglese, e costruisci la frase in modo che un nome ci stia: `%s va su tutte le furie!`. Non scrivere nessun altro `%`.
- Un urlo è breve e forte: mantieni i punti esclamativi dell'inglese. Un grido di battaglia resta un grido di battaglia (`For the Horde!` → `Per l'Orda!`).
- Una mimica descrive il PNG in terza persona, al presente (`%s laughs.` → `%s ride.`).
- **Opzioni di dialogo** (le righe brevi che il giocatore clicca: `Train me.`, `Inn`, `I would like to buy from you.`): parla il giocatore, in prima persona, breve quanto l'inglese, e lo stesso senso ha sempre la stessa resa (`Train me.` → `Addestrami.`, `I want to browse your goods.` → `Voglio vedere la tua merce.`, `Inn` → `Locanda`). Un'opzione che l'inglese scrive come un imperativo rivolto al giocatore resta all'imperativo, come un pulsante (`Press the yellow button…` → `Premi il pulsante giallo…`, `Access secret goblin engineering schemata!` → `Accedi agli schemi segreti di ingegneria goblin!`).
- **`{class}` è singolare**: il gioco inserisce il nome della classe al singolare, quindi mai `i {class}` né un accordo al plurale; si riscrive al singolare (`<un/una> {class} come te`). `<un/una> {class}` va bene anche davanti a vocale.
- **Il genere di chi parla** non si conosce: la stessa riga può dirla un PNG maschio o femmina. Dove il genere di chi parla si vedrebbe (`I am tired`, `I was sent`), usa una forma che vada bene per entrambi (`Sono sfinito` → `Non ne posso più`, `Mi hanno mandato qui`). Le coppie `<m/f>` restano solo per il genere del **giocatore**.
- **Saluti brevi** (`Greetings, $C.`, `Hello, $N.`): naturali e vari quanto l'inglese, con il tu (`Salute, {class}.`).

## Libri, lettere e targhe (`book`)

Una riga è una pagina: traducila così com'è, senza portare frasi da un'altra pagina e senza aggiungere titoli o numeri di pagina.

- Libri, cronache, guide e rapporti: prosa scritta, impersonale. Lettere, biglietti e diari: la voce di chi scrive; il saluto (`Dear Morgan,` → `Caro Morgan,`) e la chiusa (`Warm regards,` → `Cordiali saluti,`) diventano formule italiane naturali. Targhe ed epitaffi: formali e brevi.
- Mantieni ogni a capo dell'inglese (versi, elenchi, firma su una riga sua).
- Orari con am/pm (`6am`, `12:30pm`): il controllo non conta come numero una cifra attaccata a lettere, quindi l'orario si scrive in lettere (`alle sei del mattino`, `alle dodici e mezza`), mai in cifre a 24 ore.
- Niente coppie di genere `<m/f>` nei libri: chi scrive non sa chi leggerà; una forma neutra (`Buona fortuna, combattente.`).
- Una pagina che inizia con `<HTML>` è markup: mantieni ogni tag esattamente com'è, con i suoi attributi, nello stesso ordine e sulla stessa riga, e traduci solo il testo fra i tag.

## Tooltip (`item_description`, `spell_description`, `spell_aura`)

Queste righe **non** sono dialogo: sono ciò che il gioco stampa nel tooltip. Ignora **Voce**.

- **Registro.** Informativo, alla terza persona o impersonale, come il client italiano: `Rigenera $N1 salute.`, `Infligge $N1 danni da fuoco.` Una frase per ogni frase inglese.
- **Maiuscole come il client italiano.** Le caratteristiche maiuscole: Forza, Agilità, Tempra, Intelletto, Spirito, Armatura (la caratteristica). Risorse e scuole minuscole: salute, mana, rabbia, energia; danni fisici, da fuoco, da gelo, da arcano, da natura, da ombra, da sacro. Le classi maiuscole (il Guerriero, i Maghi). In un tooltip `health` è `salute` (la tabella dell'interfaccia vale per le etichette dell'interfaccia).
- **Nomi di abilità.** Un'abilità citata (`Charge`, `Rend`, `Sunder Armor`) prende il nome ufficiale italiano del client: il glossario non elenca i nomi di una parola, quindi si cercano nella tabella dei nomi ufficiali delle abilità (stesso id, client itIT). Senza forma ufficiale il nome resta inglese.
- **Unità scritte dall'inglese.** Quando l'inglese scrive un'unità per esteso (`5 seconds`, `$s1 secs`, `2 mins`) e la riga non conta una durata (`durations` assente), il controllo vuole `$N`: si scrive `$N1 s` / `$N1 min` come il client (`ogni $N3 s`). Un plurale `$l<sing>:<plur>;` si rende con la forma plurale italiana.
- **L'inglese è un modello, non il testo finito.** `Restores $o1 health over $d.` è ciò che contengono i dati; il giocatore vede `Restores 61 health over 18 sec.` I valori li inserisce il gioco, diversi per oggetto, grado, livello e talento, quindi l'italiano porta i segnaposto, mai i valori.

### `$N<k>`: un numero

`$N<k>` viene sostituito con il **k-esimo numero della riga che il giocatore vede**, contando ogni numero in ordine di lettura. `"slots"` dice quanti saranno.

```
EN   Restores $s1 health.                     slots 1
IT   Rigenera $N1 salute.
```

Un numero scritto per esteso (`61`) viene rifiutato (`numbers_changed`).

### `$D<k>`: una durata

La durata è l'unico valore di cui il gioco sceglie l'**unità** (secondi, minuti, ore, giorni). **Non scrivere mai un'unità.** `$D<k>` viene sostituito con l'intera durata (numero e unità) come la vede il giocatore; `$D` conta **solo le durate**.

```
EN   Restores $o1 health over $d.    slots 2
IT   Rigenera $N1 salute in $D1.
```

Un numero che l'inglese scrive davanti a un'unità è anch'esso una durata (`every 5 sec for $d`: `$D1` è `5 sec`, il `$d` è `$D2`). `$N2 sec` al posto di `$D2` viene rifiutato (`duration_as_value` / `duration_missing`).

### Contare gli slot

`"slots"` conta ogni numero che il client stamperà, in ordine di lettura: un codice di valore (`$s1`, `$o2`, `$d`) uno; un'espressione (`${$m1/60}`) uno; un letterale già scritto uno; un intervallo (`$s1 to $s2`, che il gioco stampa come `14-22`) uno, quindi `$N1 danni`, mai `$N1-$N2`; un plurale (`$lsecond:seconds;`) nessuno.

### Testo incluso, icone, rami e liste

- Il testo incluso da un'altra abilità (`$@spelldesc…`) è già mostrato nella riga: traducilo come un'unica riga.
- Un'icona `$I1`, `$I2`… va riportata **esattamente una volta**, dove sta l'icona nella frase italiana (`icon_missing` / `icon_index`).
- Una riga con `"branches"` contiene `$?<condizione>[A][B]`: mantieni il condizionale, **stessa condizione, stessi rami, stesso ordine**, e traduci ogni ramo perché la frase funzioni con uno qualsiasi al suo posto (un ramo vuoto resta `[]`). I valori di un ramo tengono il numero dell'intero modello e restano nello stesso ramo.
- Una riga con `"tail": true` finisce con una lista di nomi che il client scrive da sé: traduci solo la testa, mantieni i suoi a capo e termina con `$T`.
- `%` resta `%`. Una percentuale si scrive `$N1%`.

## Missioni (`quest_title`, `quest_objectives`, `quest_description`)

### `quest_description`: chi affida la missione parla

È il PNG che parla al giocatore: **Voce** vale per intero, con il tu.

### `quest_objectives`: un'istruzione al giocatore

La riga sotto "Obiettivi della missione". Come il client italiano, all'imperativo con il tu:

```
EN   Kill 6 Rockjaw Troggs.
IT   Uccidi 6 Rockjaw Trogg.
```

### `quest_title`: un titolo breve

Un sintagma nominale, non una frase, senza punto finale: `La Milizia del Popolo`, `L'equilibrio della natura`.

### Numeri nelle missioni

Un numero scritto nell'inglese (`Bring 10 Linen Cloth`) si scrive uguale. Un codice del server che sta per un numero inserito dal client (`$1oa`) prende `$N<k>` come nei tooltip. `k` conta i numeri della riga che il giocatore vede, non gli obiettivi: nella descrizione di un Craftsman's Writ, che stampa solo `$2oa`, quel numero è `$N1`. Niente `$D<k>` nelle missioni.

## Testo d'interfaccia (stringhe UI)

Le stringhe d'interfaccia sono etichette, pulsanti, intestazioni, finestre e messaggi del client: il dizionario dell'interfaccia, un italiano per chiave (`data/ui`). Una bozza sono righe `{"id", "field": "text", "it"}` scritte sull'inglese attuale della chiave. Il giocatore tiene premuto il tasto per vedere l'inglese, quindi un'etichetta non si spiega da sé. Sei regole:

### 1. Significato nel contesto

Traduci il senso che usa la schermata dove appare la stringa, non il primo senso del dizionario. Giudicalo dal nome della chiave, dalle finestre che la mostrano (`pipeline/ui_inventory.txt`) e dalle chiavi vicine.

### 2. Lunghezza che ci stia

Un'etichetta è breve quanto la sua inglese: `Accept` è `Accetta`, `Abandon Quest` è `Abbandona missione`. Per un'etichetta corta `ui_lint` avvisa oltre 1,25 volte la larghezza dell'inglese: l'avviso chiede una seconda occhiata, non una riscrittura.

### 3. Registro

Etichette, pulsanti, schede e intestazioni: un nome o un verbo all'imperativo/infinito come il client (`Chiudi`, `Opzioni`). Domande e messaggi: frasi complete, con il tu (`Vuoi abbandonare "%s"?`, `L'inventario è pieno.`).

### 4. Coerenza

Un inglese, un italiano: ogni chiave il cui inglese è già spedito da un'altra chiave prende lo stesso italiano, salvo che la chiave possieda il suo testo su una schermata (`UIStrings.OWN`). I termini seguono il client ufficiale itIT; alcuni termini fissati:

| Inglese | Italiano | Non |
|---|---|---|
| quest | missione | quest |
| achievement | impresa | achievement, obiettivo |
| profession | professione | mestiere |
| battleground | campo di battaglia | battleground |
| health | Salute | punti vita, health |
| stamina | Tempra | resistenza, stamina |
| intellect | Intelletto | intelligenza |
| armor | Armatura | armor |

### 5. Formato intatto

Mantieni ogni specificatore `%s` / `%d`, codice colore (`|cff…` … `|r`), texture (`|T…|t`), link e a capo. Quando l'ordine delle parole sposta gli argomenti, numerali (`%1$s`, `%2$s`). `Requires Level %d` è `Richiede livello %d`. Un link `|H…|h[etichetta]|h` si copia byte per byte; un gruppo plurale `|4singolare:plurale;` resta, con le forme italiane (`%d |4giorno:giorni;`).

### 6. Nomi ufficiali

Un nome di persona, luogo, oggetto, abilità, fazione o zona dentro una stringa d'interfaccia segue **Terminologia ufficiale**: la forma italiana del glossario, altrimenti l'inglese così com'è.
