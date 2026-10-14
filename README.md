# Průvodce FAIR daty (EOSC CZ)

Interaktivní průvodce, který provede výzkumníky, datové stewardy, správce repozitářů a oborové komunity
cestou k FAIR datům: od plánu projektu přes výběr repozitáře, popis a licenci až po publikaci, citaci a
kontrolu. Vychází z *Analýzy a návrhu postupů k naplňování FAIR principů v rámci NRP/NDI* (verze 1.2,
NRP KA 5.1, <https://doi.org/10.71495/5dv6-v116>) a doplňuje ji o současný stav národních služeb.

> **Stav:** rozpracovaná verze. Texty jsou pracovní a před zveřejněním je projde redakce týmu.

English version: [README_en.md](README_en.md).

## Co průvodce nabízí

- **Cesta po životním cyklu výzkumných dat:** zastávky sledují sedm fází životního cyklu podle RDMkit (plánování,
  vznik, zpracování a analýza dat, uchovávání, sdílení a opakované užití) a končí kontrolou. Začíná tam, kde se
  právě nacházíte.
- **Čtyři pohledy na stejnou cestu:** výzkumník, data steward, správce repozitáře či kurátor, komunita a FIP.
- **Podrobnosti na vyžádání:** nejdřív jedna věta a jeden konkrétní krok, postup, zdůvodnění a zdroje až
  po rozbalení (úrovně L0–L3).
- **Průzkumník principů:** každý požadavek analýzy pod svým FAIR principem.
- **Sebehodnocení:** podmínky NRP a zralost FAIR zvlášť, bez celkového skóre.
- **Hodnocení, která spouštíte sami:** rychlé vyhledání ve veřejných záznamech, vybrané testy FAIR Champion,
  metriky FAIR-Checkeru a zpráva F-UJI načtená přímo v prohlížeči, vždy s rozsahem, verzemi a pokrytím; vaše
  vlastní odpovědi zůstávají vaše.
- **Katalog zdrojů a repozitářů** se stavem služby a datem ověření.
- **Vrstvy a návaznosti FAIR implementace:** přehled modelu a souvislosti v katalogu propojují pokyny
  s odpovědnostmi a předáváním informací, včetně předání uvnitř jedné vrstvy.

### Průvodce a FIP Dashboard

[FIP Dashboard](https://fip-dashboard.dmp.eosc.cz/) je národní katalog zdrojů umožňujících FAIR a komunitních
profilů; jejich záznamy spravuje on a odpovídá na otázku „které zdroje a profily“. Průvodce odpovídá na otázku „co
udělat a proč“ a na záznamy dashboardu odkazuje jejich identifikátory, místo aby je kopíroval. Kontrolu úplnosti FIP
průvodce předvyplní z profilu v dashboardu, nebo z publikované nanopublikace FIP, pokud profil v dashboardu není.

API dashboardu zatím z prohlížeče nepřijímá požadavky z adresy průvodce, proto průvodce čte datovaný snímek jeho
profilů a zdrojů a všude, kde je používá, to uvádí i s upozorněním samotného dashboardu. Plánovaná úloha navrhne
obnovení snímku pull requestem, když se data dashboardu změní. Až API adresu průvodce přijme, nastavení konektoru
`browserAccess` umožní číst je živě a snímek ponechat jako zálohu. Podrobnosti jsou v `docs/design.md`
(rozhodnutí 18 a 19, *Snapshot refresh*).

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

Workflow kontrol pull requestu má pouze oprávnění ke čtení. Samostatný důvěryhodný workflow přidá
dvojjazyčný komentář s přehledem změn a odkazy na kontroly a náhledy. Čte jen omezené podklady z
dokončeného běhu, používá kód z výchozí větve a před zveřejněním ověřuje aktuální commit pull requestu.

[Záznam výběru testů Champion](docs/champion/selection.md) vysvětluje jejich rozsah a datované měření
dostupnosti. Po sestavení webu změříte všechny posouzené kandidáty i základní sadu příkazem
`node scripts/probe_champion.mjs --jobs 4 --output .cache/champion-health.json`. Výběr testů se tím nemění.

Připravené jsou dva plánované workflow, které poběží, až budou ve výchozí větvi. `source-refresh.yml`
každý týden obnoví snímky Hesláře, re3data, FIP Dashboardu a NKR, ponechá snímek beze změny, když odpověď neprojde
kontrolou, a každý změněný zdroj navrhne jako samostatný pull request přes GitHub App repozitáře.
`health-watch.yml` každý týden kontroluje odkazy, služby, zastaralá data a stránky EOSC CZ, na kterých průvodce
stojí, jednou měsíčně znovu změří testy FAIR Champion a pro každý trvající problém otevře jedno issue. Žádný z nich
necommituje ani neslučuje; nastavení aplikace popisuje [docs/design.md](docs/design.md).

První oficiální předběžné vydání bude označeno `v1.0.0-alpha.1`; metadata aplikace a citace uvádějí `1.0.0-alpha.1`.

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
