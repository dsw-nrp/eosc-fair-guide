<!-- type: landing -->
# Průvodce FAIR daty (EOSC CZ)

[![DOI](https://zenodo.org/badge/1409358632.svg)](https://zenodo.org/badge/latestdoi/1409358632) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/dsw-nrp/eosc-fair-guide)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/dsw-nrp/eosc-fair-guide) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Interaktivní průvodce pro výzkumníky, datové stewardy, správce repozitářů a výzkumné komunity: od plánování dat přes
výběr repozitáře, popis a licencování až po zveřejnění, citování a kontrolu. Vychází z *Analýzy a návrhu postupů k
naplňování FAIR principů v rámci NRP/NDI* (verze 1.2, NRP KA 5.1, <https://doi.org/10.71495/5dv6-v116>).

[English](README_en.md) · **[Otevřít Průvodce](https://dsw-nrp.github.io/eosc-fair-guide/)**

Příspěvky s AI začínají u [nástrojů pro agenty](docs/agent-tooling.md); [AGENTS.md](AGENTS.md) je vstupní soubor
s instrukcemi pro běh asistenta.

## Co Průvodce nabízí

- Cestu sedmi fázemi životního cyklu RDMkit a závěrečnou kontrolu, pohledem čtyř rolí.
- Nejdřív jednu akci, kroky, důvody a zdroje až na vyžádání (L0–L3).
- Prohlížeč principů FAIR, přehled zdrojů a repozitářů s datovanými stavy a model vrstev a návazností.
- Oddělenou sebekontrolu podmínek NRP a vyspělosti FAIR, bez celkového skóre.
- Volitelné dohledání záznamů, FAIR Champion, FAIR-Checker a místní zprávy F-UJI s verzí, rozsahem a pokrytím;
  vaše vlastní odpovědi zůstávají vaše.

[FIP Dashboard](https://fip-dashboard.dmp.eosc.cz/) spravuje profily komunit a záznamy podpůrných zdrojů;
Průvodce vysvětluje, co dělat a proč. Přístup z prohlížeče a použití datovaných snímků popisuje
[vysvětlení Průvodce](docs/about.md#the-guide-and-the-fip-dashboard).

Týdenní návrhy obnovy snímků pokrývají Heslář, re3data, FIP Dashboard, NKR, KNAV, FAIRsharing a DataCite;
každá změna zdroje prochází kontrolou v pull requestu.

## Použití a příspěvky

| Cíl | Kde začít |
| --- | --- |
| Otevřít místní kopii nebo spustit kontroly | [Sestavení a kontroly](docs/how-to/build-and-check.md) |
| Vložit Průvodce na jiný web | [Vložení Průvodce](docs/embedding.md) |
| Vylepšit obsah nebo kód | [Přispívání](CONTRIBUTING.md) |
| Sloučit změnu, vydat verzi nebo provést údržbu | [Úkoly správce](docs/ci.md) |
| Porozumět datům a aplikaci | [Obsahový model](docs/content-model.md), [návrh](docs/design.md) a [struktura repozitáře](docs/repository-reference.md) |
| Posoudit praxi samotného Průvodce | [Softwarové doklady](docs/software-practice.md) a [příklad modelu](docs/model-practice.md) |

Sestavená stránka funguje offline, z místního souboru, v iframe i na statickém hostingu. Internet potřebují jen
živé kontroly spuštěné uživatelem. Zdrojem obsahu je TOML; sestavení vytvoří crate, stránku a statické API ve `_site/`.
Produkce vychází z ověřených vydání; `/next/` je ověřený náhled výchozí větve.

## Licence

Kód je pod licencí MIT, obsah pod licencí CC BY 4.0. Přiřazení licencí jednotlivým souborům je
v [REUSE.toml](REUSE.toml), plné texty ve složce [LICENSES/](LICENSES/).

## Autoři a citace

Průvodce připravil David Novák (Knihovna AV ČR a Archeologický ústav AV ČR, Praha; <https://orcid.org/0000-0001-6592-6291>). Odborným základem je analýza
autorů Ilona Trtíková, Petra Bártková, Lada Biedermannová, Jindřich Fejfar, Robert Pergl, David Novák a
Tomáš Čížek. Průvodce citujte podle odkazu „Jak citovat Průvodce“ v jeho patičce; [CITATION.cff](CITATION.cff)
uvádí autorství softwaru.

## Využití umělé inteligence

Příspěvky připravené s pomocí umělé inteligence jsou vítány pod lidským dohledem.
Za jejich správnost odpovídají lidé; repozitář je pro takovou spolupráci uzpůsoben.
Konkrétní nástroje, modely, konzultované zdroje a změny obsahu zaznamenávají
[paradata znalostní báze](docs/content-model.md#paradata).

## Poděkování

Tento výstup byl vytvořen s finanční podporou iniciativy EOSC CZ prostřednictvím projektu Národní
repozitářová platforma pro výzkumná data (CZ.02.01.01/00/23_014/0008787), financovaného z Operačního
programu Jan Amos Komenský (OP JAK) Ministerstva školství, mládeže a tělovýchovy České republiky (MŠMT).
