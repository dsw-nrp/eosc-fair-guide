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
  po rozbalení (úrovně L0–L3).
- **Průzkumník principů:** každý požadavek analýzy pod svým FAIR principem.
- **Sebehodnocení:** podmínky NRP a zralost FAIR zvlášť, bez celkového skóre.
- **Živá kontrola identifikátoru:** rychlá kontrola a na vyžádání hloubková kontrola nástrojem FAIR Champion.
- **Katalog zdrojů a repozitářů** se stavem služby a datem ověření.
- **Vrstvy a návaznosti FAIR implementace:** přehled modelu a souvislosti v katalogu propojují pokyny
  s odpovědnostmi a předáváním informací, včetně předání uvnitř jedné vrstvy.

## Jak průvodce spustit

Při prvním spuštění nainstalujte připnuté závislosti Node.js pro přibalenou dokumentaci API.
S Pythonem 3.11 nebo novějším pak sestavte web a otevřete `_site/index.html`:

```bash
npm ci
python scripts/build_site.py
```

Generátor používá standardní knihovnu Pythonu; upravené obrázky SVG jsou místní soubory.
Hotová stránka funguje i bez připojení; jen živé
kontroly potřebují internet. Stránku lze vložit do jiného webu (iframe) nebo zveřejnit samostatně.

Pro místní server, který některé prohlížeče potřebují pro práci se schránkou:

```bash
python scripts/serve.py --build
```

Průvodce ukazuje vlastní praxi pro výzkumný software. Výchozím bodem bude první oficiální předběžné
vydání; archivace veřejného kódu a případná sebecertifikace OpenSSF zatím čekají na provedení.

## Struktura repozitáře

| Cesta | Obsah |
| --- | --- |
| `content/` | Obsah v TOML: zastávky, rady, kontroly, zdroje, registr požadavků, slovníček, upozornění a provenience |
| `scripts/` | Generátor znalostní báze, sestavení API a kontroly obsahu (Python, jen standardní knihovna) |
| `tests/` | Testy skriptů s minimální ukázkou obsahu |
| `profile/` | Profil RO-Crate (SHACL) pro kontrolu struktury znalostní báze |
| `index.html` | Stránka průvodce s prázdnými bloky, které doplní sestavení |
| `_site/` | Sestavený web, který se necommituje: stránka s datovými skripty, znalostní báze jako RO-Crate 1.2 s náhledem a API |
| `assets/` | Styly, skripty, obrázky a vykreslené diagramy |
| `api/` | Stránka dokumentace API; samotné API vytvoří sestavení |
| `assets/diagrams/` | Dvojjazyčné úpravy schválených obrázků rukopisu |
| `docs/` | Návrh a rozhodnutí (`design.md`), model obsahu (`content-model.md`) |
| `.github/` | CI, šablony a odpovědní recenzenti |

[Příklad softwarové praxe](docs/software-practice.md) přiřazuje podklady aplikace a zbývající kroky k vydání
k příslušným softwarovým pokynům.

[Příklad použití modelu](docs/model-practice.md) sleduje skutečný požadavek, otázku, test a záznam revize.
Koncepční model odkazuje na rukopis v přípravě; požadavky kontrol si zachovávají své publikované zdroje.

## Jak upravovat obsah

Obsah se píše v souborech TOML ve složce `content/`, nikdy v tom, co vytvoří sestavení. Pravidla popisuje
[docs/content-model.md](docs/content-model.md):

- každý text pro uživatele existuje česky i anglicky;
- každá rada a otázka kontroly cituje alespoň jeden požadavek z registru a každý požadavek odkazuje na
  publikovaný zdroj;
- každá změna obsahu zaznamená autora, použitý nástroj (včetně modelu AI) a zdroje;
- stavy používají pětistupňový slovník a uvádějí datum ověření.

Po úpravě sestavte web a zkontrolujte jej; pak otevřete `_site/index.html`:

```bash
python scripts/build_site.py
python scripts/check_content.py
```

Všechny kontroly najednou spustí `python scripts/check_all.py` (po `npm ci` a instalaci
nástrojů z `requirements-dev.txt`).
Po spuštění najdete v `.cache/health/` přehled výsledků, JSON a shrnutí: stav kontrol a pokrytí otázek,
rad a požadavků původními texty. CI je připojí k běhu jako artefakt a shrnutí. Přepínač `--live`
přidá kontroly externích služeb; bez něj se jejich dostupnost neposuzuje.
Pro porovnání dvou uložených přehledů použijte `--previous-report path/to/health.json`.
Stejný přehled poskytuje API na `api/health.json`, zdokumentované v `api/openapi.json`;
samotné sestavení uvádí, že kontroly dosud neproběhly,
a jejich spouštěč poté zveřejní skutečný výsledek běhu.
Web zveřejňuje také přehled `health/index.html` v angličtině, dostupný z patičky
a ze stránky Data pro stroje. JSON i přehled se aktualizují stejným výsledkem běhu.

Průvodce i s jeho API, jak bude zveřejněn, si spustíte na svém počítači (dokumentace API potřebuje jednou
`npm ci`) a otevřete <http://127.0.0.1:8000/> a <http://127.0.0.1:8000/api/>:

```bash
python scripts/serve.py --build
```

Pravidla pro editaci s AI jsou v dovednosti `fair-guide-editor`
(`.agents/skills/fair-guide-editor/SKILL.md`) a v [AGENTS.md](AGENTS.md); provozní pokyny pro agenty
jsou v [README_en.md](README_en.md).

## Jak přispívat

Změny přicházejí jako pull request do `main`. CI kontroluje strukturu, obsah, funkčnost a přístupnost
stránek, odkazy, diagramy a čistotu repozitáře. Odpovědný recenzent kontroluje správnost a styl.
Podrobný postup je v [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Kód je pod licencí MIT, obsah pod licencí CC BY 4.0. Přiřazení licencí jednotlivým souborům je
v [REUSE.toml](REUSE.toml), plné texty ve složce [LICENSES/](LICENSES/).

## Autoři a citace

Průvodce připravil David Novák (Knihovna AV ČR a Archeologický ústav AV ČR, Praha; <https://orcid.org/0000-0001-6592-6291>). Odborným základem je analýza
autorů Ilona Trtíková, Petra Bártková, Lada Biedermannová, Jindřich Fejfar, Robert Pergl, David Novák a
Tomáš Čížek. Jak průvodce citovat, uvádí [CITATION.cff](CITATION.cff).

## Využití umělé inteligence

Na přípravě obsahu a kódu se podíleli AI asistenti Claude (Anthropic) a Codex (OpenAI).
Každá změna obsahu je zaznamenána
v paradatech znalostní báze, včetně použitého nástroje, a průvodce ji ukazuje u každé položky. Texty
kontrolují lidé.

## Poděkování

Tento výstup byl vytvořen s finanční podporou iniciativy EOSC CZ prostřednictvím projektu Národní
repozitářová platforma pro výzkumná data (CZ.02.01.01/00/23_014/0008787), financovaného z Operačního
programu Jan Amos Komenský (OP JAK) Ministerstva školství, mládeže a tělovýchovy České republiky (MŠMT).
