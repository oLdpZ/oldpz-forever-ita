## m05
- Ice Claw (abilità) falso positivo dentro "Ice Claw Bear"
- Venture Co. vs "S.P.R. & Co." (glossario solo dentro Documenti della S.P.R. & Co.)
- Plaguelands → probabilmente Terre Infette (derivato da Western/Eastern Plaguelands)
- Magic Quarter, Mass Graves forse con nome ufficiale
- Dama Oscura, Sogno di Smeraldo, speziale (Apothecary) usati senza glossario
## m01
- REGOLA: termini classe/razza dentro nomi composti (Mage Quarter) forzano "Quartiere del Mago" (ufficiale probabile "Quartiere dei Maghi") → lint troppo rigido; correggere: classe/razza obbligatorie solo se il termine non è parte di un nome proprio più lungo
- Buoni regalo con zona: nome oggetto inventato ("Buono Regalo della Contea del Nord")
- Greatfather Winter, Winter Veil, Emerald Dream, Barrens (Savane?), Trade District: forma ufficiale probabile, lasciati in inglese
- "the Den" → "la Tana" da verificare; Dark Iron → Ferroscuro (da oggetto glossario)
## m04
- Cognomi/famiglie con forma ufficiale solo in nomi composti: Thunderbrew→Birratuono, Barleybrew→Maltorzo, Proudmoore→Marefiero, Rumbleshot→Granzuffa (misto inglese/italiano nei testi) → decidere regola: cognomi famosi tradotti ufficialmente?
- Winterhoof→Zoccolo Artico, Thunderhorn→Corno Tonante derivati dal traduttore
- Stormwind Trade District, Royal Apothecary Society, Druids of the Talon, Council of the Forest, Siege Brigade: forma ufficiale probabile
- Sentinels→Sentinelle, Dark Lady→Dama Oscura non da glossario
## m00
- INCOERENZA: "The Den" → m00 "Antro del Tirocinio" (glossario ufficiale) vs m01 "la Tana"
- Silver Hand (Mano d'Argento?), Shattered Hand, Twilight's Hammer, SI:7 lasciati inglesi
- Earthmother→Madre Terra, Eternal Flame→Fiamma Eterna, Arcane Arts→Arti Arcane da verificare
- Glyphic Rune → "Runa con Glifi" inventato per analogia; Nether da solo lasciato
- lint rifiuta coppie <a b/c d> con spazi: dividere in coppie piccole (ok)
## m03
- $Tpunk; in quest di prova 1 → reso $N1 (riga di test, irrilevante)
- coppie con spazi/apostrofo rifiutate: <un eroe/un'eroina> → forme neutre (lint limitato)
- PERSONAGGI: oggetti tradotti ufficialmente (Nota di Nonna Pietradura) ma PNG inglesi (nonna Stonefield) → serve tabella nomi creature itIT
- Bloodhoof da solo, Lion's Pride Inn, Lesser Heal, Bristleback; titoli Mountaineer/Brave/Junior Apothecary inventati
## m02
- INCOERENZA: tribù/famiglie tradotte (Bristleback→Mantotergo, Frostmane→Mantogelido, Gnarlpine→Mordipigna, Proudmoore→Marefiero) mentre il lessico dice inglese → da uniformare nel giro di revisione
- Quilboar → Verrospino (razza: tradurre come parola comune "verrospino")
- Greatmother → Grande Madre; Lesser Heal (Cura Inferiore?) lasciato inglese; Battleboar inglese
- 5621 progress "Delor" probabile errore nell'originale
## m06
- People's Militia → Brigata del Popolo (dalla guida)
- Druids of the Talon, Circle of Ancients, Stonemason's Guild, Relics of Wakening inglesi
- Venomtail (Codavenefica da oggetto), Timberling, Arch Druid → Arcidruido; Mausolea genere?
## m09
- Druid of the Claw: lint impone Druido → "<Druido/Druida> dell'Artiglio" (contrasto brief/lint: classe dentro nome composto — risolto dal fix lint?)
- Hall of Mysteries, Valley of Spirits, War Quarter inglesi; Touch of Weakness, Great Bear Spirit (null); moonkin; pet → famiglio
## m08
- voidwalker (Ombra del Vuoto?), Temple of the Moon, Deathstalker, Slaughtered Lamb, Hall of Mysteries, Mystic Ward, Cleft of Shadow, Forlorn Cavern, Oracle Glade, Rogues' Quarter, Gallow's End Tavern, Hidden Circle inglesi
- snapdragons → dragolose; maiuscole titoli sacerdote (Sommo Sacerdote) vs minuscole altri titoli: INCOERENZA maiuscole titoli
## m10
- FORZATURA: "Armored Scorpid" → "uno Scorpide, l'Armored Scorpid" (glossario Scorpid obbligatorio dentro nome creatura) → rivedere: nomi creature composti dovrebbero esentare come per classi
- maestro delle viverne/grifoni...; furiere; Albero del Mondo
- luoghi inglesi: Hall of the Brave, Hall of Arms, Old Town, Trade Quarter, Valley of Strength, Skytower, Temple Gardens, Great Forge District, Deep Mountain Mining Guild; "a Mausolea" vs "la Mausolea"
## m11
- INCOERENZA: Deathstalker → "Inseguitori della Morte" (m11, da oggetto) vs inglese (m08); voidwalker → "ombra del Vuoto" (m11) vs inglese (m08)
- Explorers' League (Lega degli Esploratori), Great Forge (Grande Forgia), Dark Iron inglese qui vs Ferroscuro altrove; Steam Tank Brigade; epiteti draghi da verificare; "Ice Claw Bear" → "orso Artiglio di Ghiaccio" forzato
## m07
- tribù tradotte da glossario (Chiomaguzza, Mantotergo, Lanciascura...) → DECISIONE: tribù/clan → forma ufficiale; cognomi personali → inglese (lessico aggiornato)
- Magic Quarter → Quartiere della Magia; Eastvale Lumber Camp → Campo di Taglio di Vallevante; Hunter's Rise → Altura dei Cacciatori
## m16
- Royal Apothecary Society; Dwarven District, Cathedral Square, Pools of Vision, the Cleft, Lake Lordamere inglesi; Pyrewood → Rovonero; "Barile di Chen Vuoto" (glossario innaturale); "a Mausolea"
## m13
- Highborne → Alti Nobili; Shadow Council, Cathedral of Light, Shrine of Eternal Flame, Demon Seed inglesi; "alla Mausolea" (genere da decidere globalmente)
## m12
- LIMITE: $g con interi paragrafi alternativi (842 completion 004fff3197) → resa neutra mista; servirebbe supporto coppie con spazi
- "di Rivafosca" aggiunto accanto a Darkshore Thresher per il lint (zona dentro nome creatura) → estendere esenzione nomi composti a zona?
- Highborne inglese qui vs Alti Nobili (m13): INCOERENZA; Well of Eternity, War of the Ancients, Far Watch Outpost
## m17
- Gnomeregan Exiles, Trade Quarter, Dry Hills, Forgotten Pools, Lushwater Oasis inglesi; Silverwing → Alargentea; {name}ama refuso originale
## m15
- moonkin → lunagufi (m15) vs inglese (m09): INCOERENZA; Prospector → prospettore; Miners' League, Assembly of Explorers, Undermine, Mor'shan Rampart inglesi; Stormpike cognome inglese vs Piccatonante oggetti
## m14
- ERRORE GUIDA: People's Militia ufficiale = "Milizia del Popolo" (oggetti), non "Brigata del Popolo" (esempio guida sg1) → correggere guida e lotti m06/m12/m14
- Furbolg ufficiale = mezzorso (glossario); Samophlange = Samoflago; Rot Hide = Pellemarcia; Nightlash = Sferanotte; Dead Field = Agro dei Morti; Hall of the Dark Lady; ley → tellurica?
## m19
- Magic Quarter inglese (m19) vs Quartiere della Magia (m07/m16): INCOERENZA; Night Watch, Shrine of Aessina, Camp Taurajo, Ancient of Lore, shredder
## m20
- Sundering → la Frattura?; Valley of Honor → Valle dell'Onore; Warsong inglese (Cantaguerra?); Grimtotem → Totem Truce (da glossario); Pools of Vision, Raptor Grounds, Dark Strand, Camp Taurajo inglesi
## m23
- titoli abilità sacerdote (Chastise, Shadowguard, Dark Sacrifice, Elune's Grace, Arcane Feedback) null: verificare SpellName itIT (potrebbero esistere ma esclusi dal glossario perché di una parola o id diversi)
- Mystic Ward, War Quarter, Cathedral of Light inglesi; /lay emote; Kolkar, Resonite
## m21 / m18
- LINT: zona dentro nomi creatura composti (Redridge Mongrel/Brute/Poacher) forza "a Crestarossa"/"Bruti di Crestarossa" → estendere esenzione nomi composti anche a zona/fazione (solo avviso)
- Baron Longshore → "barone Rivalunga" forzato (cognome nel glossario come zona?)
- Warsong → Cantaguerra (da glossario Forra dei Cantaguerra) — m20 l'aveva inglese: INCOERENZA
- Well of Eternity → Pozzo dell'Eternità; Blackrock → Roccianera; Felguard → vilguardia; moonstalker → predaluna; Horde Warbringer
## m22
- SI:7 → IR:7 (da oggetto) vs inglese (m00): INCOERENZA; Rogues' Quarter → Quartiere dei Ladri; Cathedral of Light → Cattedrale della Luce; Bloodfeather clan → Piumarossa; Deepmoss → Muschiofondo; Heartswood → Cuordilegno; Wharfmaster → capomolo
## Dialoghi
- Erbe fiorpace / fiordifuoco (Peacebloom, Firebloom) scritte a memoria, non dal glossario: da verificare sul client itIT
- Maraudon: il client italiano dice Maraudine? Per ora resta Maraudon (nessuna zona nel glossario)
- Old Town (Città Vecchia?), Royal Quarter, Dwarven District, Hall of Arms, The Drag, Tinker Town e simili restano inglesi finché non c'è una forma ufficiale
- Genere degli anziani: anziano maschile salvo che l'inglese mostri una donna; alcune anziane potrebbero restare al maschile
- Righe con `$g` su frasi intere (622554b8c6, g10 riga 182): resta una sola frase neutra, il giocatore maschio perde una battuta di colore
- Lord + nome: `lord` minuscolo nei dialoghi, ma gli oggetti ufficiali dicono `Sire`; da allineare se il client usa Sire anche per i PNG
- Mailbox / Auction House: g41 usa le forme dell'interfaccia ufficiale (`Cassetta della posta`, `Casa d'aste`, minuscole), non `Cassetta delle lettere` / `Casa d'Aste`
- Opzioni dei menu: Lockpicking → Scassinare, Guild Master → Maestro di gilda, Weapons Trainer → Istruttore d'armi, Battlemaster → Maestro di guerra scritti senza una forma nel glossario: da verificare
