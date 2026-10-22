# Attribution

## Upstream code

oLd_pZ Forever - Traduzione Italiana is a fork of **WoW Forever Japanese** by **Zyaga**
(https://github.com/zyaga/wow-forever-japanese), released under GPL-2.0-or-later, taken at commit
`1578af4b5bffffbe3d89d729ef769e068511d425` (1578af4b). Its addon architecture, data pipeline, tests and
documentation are reused and modified here under the same license. Its Japanese translations are not part of
this project: no Japanese text ships. This credit claims no support from the upstream author.

## Translators (0 tags, as recorded in data/)

No hand-written Italian translation ships yet.

## Lineage

WoW Forever Japanese's addon code descends, as its own credits state, from these earlier addons (GPLv2,
CurseForge):

1. **WoWpoPolsku-Quests** (Platine, wowpopolsku.pl): the addon architecture the later forks used.
2. **Classic Quest Chinese Translator** (luckycat_tv) and **Tooltips Translator - Chinese** (qqytqqyt).
3. **Classic Quest Japanese Translator** (Crynok / Zyaga) and **Classic Tooltip Japanese Translator** (Zyaga):
   addons for WoW Classic.

## English source text

The English text in `data/english/` is Blizzard Entertainment's. It is kept to align and hash the
translations and is never shipped in the addon. It was read from the Forever client's own tables and quest
cache, the Classic Era quest cache, wago.tools DB2 exports (`ItemSparse`, `SpellName`), and:

- pfQuest (`db/enUS/quests.lua`, https://github.com/shagu/pfQuest), under the MIT License (below);
- the VMaNGOS world database (https://github.com/vmangos/core, release `db_latest`, snapshot `db-13b49dc`),
  GPL-2.0: quest progress and completion text, gossip and book pages.
- forever-vo (https://github.com/quinn-dougherty/forever-vo), under the MIT License (below): quest progress
  and turn-in text and NPC greetings that players of the Forever client recorded with its addon and sent in.

## pfQuest license

> MIT License
>
> Copyright (c) 2017-2021 Eric Mauser (Shagu)
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
> following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial
> portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
> LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
> EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
> AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
> OR OTHER DEALINGS IN THE SOFTWARE.

## forever-vo license

> MIT License
>
> Copyright (c) 2026 Quinn Dougherty
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
> following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial
> portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
> LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
> EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
> AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
> OR OTHER DEALINGS IN THE SOFTWARE.

## Blizzard's Italian text

Most of the Italian this addon ships is not a translation of ours. It is the work of
Blizzard Entertainment (testi ufficiali itIT): the Italian of the retail World of Warcraft client,
read from its client tables (GlobalStrings, Faction, ItemSparse, Spell, ChrClasses, ChrRaces) through
wago.tools DB2 exports, and kept only where the retail English is the English Forever shows
(`wfj import official`). Its lines carry the provenance class `official`. Retail builds read: `12.1.5.70448`.

## This project

oLd_pZ Forever - Traduzione Italiana ships its own code and translations under GPL-2.0-or-later (see
`LICENSE`); every translated line keeps its provenance in `data/` (`provenance.translator`, or the model that
drafted it). The English text in `data/english/` is Blizzard Entertainment's and is not licensed by this
project. Details: `docs/legal/licensing.md`.
