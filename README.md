# Průvodce FAIR daty (EOSC CZ)

Interaktivní průvodce, který provede výzkumníky, datové stewardy, správce repozitářů a oborové komunity
cestou k FAIR datům: od plánu projektu přes výběr repozitáře, popis a licenci až po publikaci, citaci a
kontrolu. Vychází z *Analýzy a návrhu postupů k naplňování FAIR principů v rámci NRP/NDI* (verze 1.2,
NRP KA 5.1, <https://doi.org/10.71495/5dv6-v116>) a doplňuje ji o současný stav národních služeb.

> **Stav:** rozpracovaná verze. Texty jsou pracovní a před zveřejněním je projde redakce týmu.

English version: [README_en.md](README_en.md).

## Co průvodce nabízí

- **Cesta v devíti zastávkách:** Plán → Práce → Repozitář → Popis → Licence a přístup → Publikace →
  Dohledatelnost → Citace a uznání → Kontrola. Začíná tam, kde se právě nacházíte.
- **Čtyři pohledy na stejnou cestu:** výzkumník, data steward, správce repozitáře či kurátor, komunita a FIP.
- **Podrobnosti na vyžádání:** nejdřív jedna věta a jeden konkrétní krok, postup, zdůvodnění a zdroje až
  po rozbalení.
- **Průzkumník principů:** každý požadavek analýzy pod svým FAIR principem.
- **Sebehodnocení:** brána NRP a zralost FAIR zvlášť, bez celkového skóre.
- **Živá kontrola identifikátoru:** rychlá kontrola a na vyžádání hloubková kontrola nástrojem FAIR Champion.
- **Katalog zdrojů a repozitářů** se stavem služby a datem ověření.

## Jak průvodce spustit

Otevřete soubor `index.html` v prohlížeči. Nic se neinstaluje a stránka funguje i bez připojení; jen živé
kontroly potřebují internet. Stránku lze vložit do jiného webu (iframe) nebo zveřejnit samostatně.

## Struktura repozitáře

| Cesta | Obsah |
| --- | --- |
| `content/` | Zdrojové texty a data průvodce v souborech TOML |
| `scripts/` | Generátor znalostní báze a kontroly obsahu (Python, jen standardní knihovna) |
| `tests/` | Testy skriptů s minimální ukázkou obsahu |
| `profile/` | Profil RO-Crate (SHACL) pro kontrolu struktury znalostní báze |
| `index.html` | Stránka průvodce s vloženou znalostní bází |
| `ro-crate-preview.html` | Generovaná kopie stránky: náhled RO-Crate |
| `ro-crate-metadata.json` | Znalostní báze jako RO-Crate 1.2 (generovaná) |
| `assets/` | Styly, skripty, obrázky a vykreslené diagramy |
| `diagrams/` | Zdroje diagramů v Mermaid |
| `docs/` | Návrh a rozhodnutí (`design.md`), model obsahu (`content-model.md`) |

## Jak upravovat obsah

Obsah se píše v souborech TOML ve složce `content/`, nikdy přímo v `index.html` ani
v `ro-crate-metadata.json`. Každý text je česky i anglicky, cituje publikovaný zdroj z registru požadavků
a každá změna zaznamená, kdo ji provedl a s jakým nástrojem. Po úpravě spusťte:

```bash
python scripts/build_crate.py
python scripts/check_content.py
```

Změny přicházejí jako pull request a před sloučením je zkontroluje CI i člověk. Podrobný postup je
v [CONTRIBUTING.md](CONTRIBUTING.md) a v [README_en.md](README_en.md).

## Licence

Kód je pod licencí MIT, obsah pod licencí CC BY 4.0. Přiřazení licencí jednotlivým souborům je
v [REUSE.toml](REUSE.toml), plné texty ve složce [LICENSES/](LICENSES/).

## Autoři a citace

Průvodce připravil David Novák (Knihovna AV ČR a Archeologický ústav AV ČR, Praha; <https://orcid.org/0000-0001-6592-6291>). Odborným základem je analýza
autorů Ilona Trtíková, Petra Bártková, Lada Biedermannová, Jindřich Fejfar, Robert Pergl, David Novák a
Tomáš Čížek. Jak průvodce citovat, uvádí [CITATION.cff](CITATION.cff).

## Využití umělé inteligence

Na přípravě obsahu a kódu se podílel AI asistent (Claude, Anthropic). Každá změna obsahu je zaznamenána
v paradatech znalostní báze, včetně použitého nástroje, a průvodce ji ukazuje u každé položky. Texty
kontrolují lidé.

## Poděkování

Tento výstup byl vytvořen s finanční podporou iniciativy EOSC CZ prostřednictvím projektu Národní
repozitářová platforma pro výzkumná data (CZ.02.01.01/00/23_014/0008787), financovaného z Operačního
programu Jan Amos Komenský (OP JAK) Ministerstva školství, mládeže a tělovýchovy České republiky (MŠMT).
