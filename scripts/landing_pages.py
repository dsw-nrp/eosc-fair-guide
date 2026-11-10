"""Static, bilingual HTML landing pages for the Guide's API records.

Every page reads the same record JSON that its API document publishes. Text is escaped, never interpreted as HTML.
The only assets are the Guide's existing stylesheets. Record identity and related-record addresses come from their
persistent IRI, not from the serving host.
"""

from __future__ import annotations

import html
import posixpath
import re
from typing import Any
from urllib.parse import urlsplit

import build_crate as kb

LABELS = {
    "kind": {"cs": "Druh", "en": "Kind"},
    "identifier": {"cs": "Identifikátor Průvodce", "en": "Guide identifier"},
    "address": {"cs": "Trvalé IRI", "en": "Persistent IRI"},
    "external": {"cs": "Externí identifikátory", "en": "External identifiers"},
    "status": {"cs": "Stav", "en": "Status"},
    "as-of": {"cs": "k datu", "en": "as of"},
    "related": {"cs": "Související záznamy", "en": "Related records"},
    "parts": {"cs": "Části záznamu", "en": "Parts of this record"},
    "guide": {"cs": "Otevřít v Průvodci", "en": "Open in the Guide"},
    "source": {"cs": "Vychází z", "en": "Based on"},
    "license": {"cs": "Licence", "en": "Licence"},
}
COMPACT_PREFIXES = {prefix.removesuffix(":"): base for base, prefix in kb.CLASS_PREFIXES if prefix}
IDENTITY_PROPERTIES = {
    "@context",
    "@id",
    "@type",
    "identifier",
    "sameAs",
    "url",
    "name",
    "headline",
    "description",
    "text",
}
STATUS_PROPERTIES = tuple(prop for prop, shape in kb.GUIDE_TERM_SHAPES.items() if shape[0] == kb.ADMS + "status")


class RecordPages:
    def __init__(self, api: Any, documents: dict[str, dict[str, Any]]) -> None:
        self.api = api
        self.base = api.base
        self.records: dict[str, dict[str, Any]] = {}
        self.parts: dict[tuple[str, str], dict[str, Any]] = {}
        for path, record in documents.items():
            if not (path.startswith("api/v1/") and path.endswith(".json")):
                continue
            self.records[path] = record
            for part in self.walk(record):
                local = self.resolve(path, part)
                if local and local[1]:
                    self.parts[local] = part

    @staticmethod
    def items(value: Any) -> list[Any]:
        return value if isinstance(value, list) else [value]

    @staticmethod
    def walk(value: Any):
        """Every nested object, in document order, so the same part set drives labels, links and anchored sections."""
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from RecordPages.walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from RecordPages.walk(child)

    def text(self, value: Any, language: str, here: str = "api/v1/index.json") -> str:
        """Localized text from an API value, without inventing a translation."""
        if not isinstance(value, dict):
            if isinstance(value, bool):
                return "false"
            return str(value) if isinstance(value, (str, int, float)) else ""
        if "@id" in value and "termCode" in value:
            local = self.resolve(here, value["@id"])
            return self.text(self.parts.get(local, value).get("name", value["termCode"]), language)
        other = "en" if language == "cs" else "cs"
        for key in (language, other, "@value", "name", "headline", "identifier", "value", "@id"):
            if value.get(key) is not None:
                return self.text(value[key], language)
        return ""

    def value(self, value: Any, language: str, here: str | None = None) -> str:
        items = [self.text(item, language, here) for item in self.items(value)]
        return ", ".join(item for item in items if item)

    @staticmethod
    def api_location(path: str) -> str:
        return "api/v1/" + path.removeprefix("id/").removesuffix(".html") + ".json" if path.startswith("id/") else path

    def resolve(self, here: str, reference: Any) -> tuple[str, str] | None:
        """A record path plus fragment, for a local link or a compact vocabulary/part reference."""
        here = self.api_location(here)
        if isinstance(reference, dict) and "@id" not in reference:
            return None
        target = str(reference.get("@id", reference) if isinstance(reference, dict) else reference)
        if target.startswith(self.base):
            address = target[len(self.base) :]
            path = "api/v1/" + address.split("#", 1)[0]
            fragment = address.split("#", 1)[1] if "#" in address else ""
        elif target.startswith("#"):
            path, fragment = here, target[1:]
        elif re.match(r"^[a-z]+:", target, re.I):
            return None
        else:
            route, _, fragment = target.partition("#")
            path = posixpath.normpath(posixpath.join(posixpath.dirname(here), route))
        path = path.removeprefix("./")
        return (path, fragment) if path in self.records else None

    def relative(self, here: str, target: str) -> str:
        if re.match(r"^https?://", target, re.I):
            return target
        return posixpath.relpath(target, posixpath.dirname(here))

    def link(self, here: str, target: str, label: str, rel: str | None = None, type_name: str | None = None) -> str:
        attrs = "".join(f' rel="{rel}"' if rel else "") + (f' type="{type_name}"' if type_name else "")
        return f'<a href="{html.escape(self.relative(here, target), quote=True)}"{attrs}>{html.escape(label)}</a>'

    def head_link(self, target: str, rel: str, type_name: str | None = None) -> str:
        """Signposting belongs in link elements, not anchors that an HTML parser moves out of head."""
        attrs = f' type="{html.escape(type_name, quote=True)}"' if type_name else ""
        return f'<link rel="{rel}" href="{html.escape(target, quote=True)}"{attrs}>'

    def reference_link(self, here: str, reference: Any, language: str) -> str:
        local = self.resolve(here, reference)
        if not local:
            return ""
        target, fragment = local
        address = target.removeprefix("api/v1/").removesuffix(".json")
        page = "id/" + address + ".html"
        part = self.parts.get((target, fragment), self.records[target])
        label = self.text(
            {key: part[key] for key in ("name", "headline", "text", "description", "identifier") if key in part},
            language,
        )
        label = label or self.text(part.get("termCode"), language) or posixpath.basename(address)
        return self.link(here, page + (("#" + fragment) if fragment else ""), label, type_name="text/html")

    def kind(self, path: str) -> str:
        return self.api_location(path).removeprefix("api/v1/").split("/", 1)[0]

    def type_iri(self, value: str) -> str:
        if "://" in value:
            return value
        if ":" in value:
            prefix, _, local = value.partition(":")
            if prefix == "guide":
                return self.api.content["guide"]["guide"]["vocabularyBase"] + local
            if prefix in COMPACT_PREFIXES:
                return COMPACT_PREFIXES[prefix] + local
            context = self.api.crate["@context"][1]
            if prefix in context:
                return context[prefix] + local
        own = self.api.crate["@context"][1].get(value)
        return own or ("http://schema.org/" + value)

    def paragraphs(self, value: str) -> str:
        return "".join("<p>" + html.escape(part) + "</p>" for part in re.split(r"\n\s*\n", value) if part)

    def part_section(self, here: str, part: dict[str, Any], fragment: str, language: str) -> str:
        title = self.text(
            {key: part[key] for key in ("name", "headline", "text", "description", "identifier") if key in part},
            language,
        )
        title = title or fragment
        fields = []
        for key, value in part.items():
            if key.startswith("@") or key in IDENTITY_PROPERTIES:
                continue
            if key in ("license", "isBasedOn", "citation"):
                linked = self.reference_link(here, value, language) if not isinstance(value, str) else ""
                content = linked or f'<a href="{html.escape(str(value), quote=True)}">{html.escape(str(value))}</a>'
                label = LABELS["license" if key == "license" else "source"][language]
            elif key in ("publisher", "creditText", "author"):
                content = html.escape(self.value(value, language, here))
                label = key
            else:
                content = html.escape(self.value(value, language, here))
                label = key
            if content:
                fields.append(f'<dt>{html.escape(label)}</dt><dd data-field="{html.escape(key)}">{content}</dd>')
        relations = []
        for key, value in part.items():
            for candidate in self.items(value):
                # Own @id and primaryTopic point back to this page, not to another record.
                local = self.resolve(here, candidate)
                if not local or local[0] == self.api_location(here):
                    continue
                linked = self.reference_link(here, candidate, language)
                if linked:
                    relations.append(f'<li data-field="{html.escape(key)}">{linked}</li>')
        return (
            f'<div class="detail-record part" lang="{language}"><h3>'
            + html.escape(title)
            + "</h3>"
            + ("<dl>" + "".join(fields) + "</dl>" if fields else "")
            + (
                f"<p><strong>{html.escape(LABELS['related'][language])}</strong></p><ul>" + "".join(relations) + "</ul>"
                if relations
                else ""
            )
            + "</div>"
        )

    def render_parts(self, here: str, record: dict[str, Any]) -> str:
        """One anchored section per issued direct or nested fragment; the shared languages share no duplicate ID."""
        groups: dict[str, dict[str, Any]] = {}
        for part in self.walk(record):
            local = self.resolve(here, part)
            if local and local[1] and local[0] == self.api_location(here):
                groups.setdefault(local[1], part)
        return "".join(
            f'<section class="detail-record part" id="{html.escape(fragment, quote=True)}">'
            + "".join(self.part_section(here, part, fragment, language) for language in kb.LANGS)
            + "</section>"
            for fragment, part in groups.items()
        )

    def language_record(self, here: str, record: dict[str, Any], address: str, language: str) -> str:
        kind = self.kind(here)
        strings = self.api.strings.get("collection", {}).get(kind, {})
        kind_name = strings.get("name", {"cs": kind, "en": kind}).get(language, kind)
        name = self.value({key: record[key] for key in ("name", "headline") if key in record}, language)
        identifier = self.text(record.get("identifier"), language) or address.rsplit("/", 1)[-1]
        name = name or identifier
        heading = html.escape(name)
        if isinstance(record.get("url"), str) and record["url"].startswith("https://"):
            heading = f'<a href="{html.escape(record["url"], quote=True)}">{heading}</a>'
        prose = record.get("text", record.get("description", record.get("abstract", record.get("headline"))))
        body = self.paragraphs(self.value(prose, language, here)) if prose is not None else ""
        persistent_iri = html.escape(self.base + address, quote=True)
        fields = [
            f"<dt>{html.escape(LABELS['kind'][language])}</dt><dd>{html.escape(kind_name)}</dd>",
            f"<dt>{html.escape(LABELS['identifier'][language])}</dt>"
            f'<dd data-field="identifier"><code>{html.escape(identifier)}</code></dd>',
            f"<dt>{html.escape(LABELS['address'][language])}</dt>"
            f'<dd data-field="sameAs"><a href="{persistent_iri}">{persistent_iri}</a></dd>',
        ]
        external = [
            candidate for candidate in self.items(record.get("sameAs")) if str(candidate) != self.base + address
        ]
        if external:
            links = [
                self.link(here, str(candidate), str(candidate))
                if str(candidate).startswith("https://")
                else html.escape(str(candidate))
                for candidate in external
            ]
            fields.append(
                f"<dt>{html.escape(LABELS['external'][language])}</dt>"
                f"<dd><ul>{''.join('<li>' + link + '</li>' for link in links)}</ul></dd>"
            )
        for key in STATUS_PROPERTIES:
            if key in record:
                value = record[key]
                date = record.get("statusAsOf") or record.get("nodeStateSince") or record.get("reviewedDate")
                content = self.value(value, language, here) + (f" ({LABELS['as-of'][language]} {date})" if date else "")
                fields.append(
                    f"<dt>{html.escape(LABELS['status'][language])}</dt>"
                    f'<dd data-field="{key}">{html.escape(content)}</dd>'
                )
        if "acceptsDeposits" in record:
            fields.append('<dt>acceptsDeposits</dt><dd data-field="acceptsDeposits">false</dd>')
        relations = []
        for key, value in record.items():
            if key in IDENTITY_PROPERTIES or key == "@context":
                continue
            for candidate in self.items(value):
                local = self.resolve(here, candidate)
                if not local or local[0] == self.api_location(here):
                    continue
                linked = self.reference_link(here, candidate, language)
                if linked:
                    relations.append(f'<li data-field="{html.escape(key)}">{linked}</li>')
        return (
            f'<section class="landing-record" lang="{language}" id="{language}">'
            f'<h1 data-field="name">{heading}</h1>{body}<dl class="record-facts">{"".join(fields)}</dl>'
            + (
                f"<p><strong>{html.escape(LABELS['related'][language])}</strong></p><ul>{''.join(relations)}</ul>"
                if relations
                else ""
            )
            + "</section>"
        )

    def render(self, here: str) -> str:
        """Render one API record as a static bilingual HTML document."""
        if here not in self.records:
            raise ValueError(f"no API record for landing page {here}")
        record = self.records[here]
        address = here.removeprefix("api/v1/").removesuffix(".json")
        title = self.value({key: record[key] for key in ("name", "headline", "identifier") if key in record}, "cs")
        page = "id/" + address + ".html"
        guide = self.link(page, "index.html#/id/" + address, LABELS["guide"]["en"])
        guide = guide.replace(LABELS["guide"]["en"], f"{LABELS['guide']['cs']} / {LABELS['guide']['en']}")
        license = self.items(record.get("license") or self.api.entities["./"]["license"])[0]
        if isinstance(license, dict):
            license = license["@id"]
        parts = self.render_parts(page, record)
        if parts:
            parts = f'<h2 lang="cs">{LABELS["parts"]["cs"]}</h2><h2 lang="en">{LABELS["parts"]["en"]}</h2>' + parts
        links = [
            self.head_link(self.base + address, "cite-as"),
            self.head_link(self.relative(page, here), "describedby", "application/ld+json"),
            self.head_link(license, "license"),
            self.head_link(self.relative(page, "index.html"), "collection"),
        ]
        for kind in self.items(record.get("@type")):
            links.append(self.head_link(self.type_iri(kind), "type"))
        return (
            '<!doctype html>\n<html lang="cs">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta http-equiv="Content-Security-Policy" content='
            "\"default-src 'self'; style-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'\">\n"
            f"<title>{html.escape(title)}</title>\n{''.join(links)}"
            '<link rel="stylesheet" href="'
            + html.escape(self.relative(page, "assets/css/tokens.css"), quote=True)
            + '">\n'
            '<link rel="stylesheet" href="'
            + html.escape(self.relative(page, "assets/css/app.css"), quote=True)
            + '">\n'
            '</head>\n<body>\n<main class="wrap">\n'
            + "".join(self.language_record(page, record, address, language) for language in kb.LANGS)
            + parts
            + f'<nav aria-label="Guide"><p>{guide}</p></nav>\n</main>\n</body>\n</html>\n'
        )


def error_page(api: Any) -> str:
    """The channel-neutral not-found page. Its catalogue link and assets use the publication's actual root."""
    root = urlsplit(api.content["guide"]["guide"]["pageUrl"]).path
    catalogue = api.content["guide"]["guide"]["pageUrl"] + "index.html#/cs/V/catalogue"
    stylesheets = "".join(
        f'<link rel="stylesheet" href="{html.escape(root + path, quote=True)}">'
        for path in ("assets/css/tokens.css", "assets/css/app.css")
    )
    return (
        '<!doctype html>\n<html lang="cs"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex">'
        '<meta http-equiv="Content-Security-Policy" content='
        "\"default-src 'self'; style-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'\">"
        "<title>404 — Nenalezeno / Not found</title>"
        + stylesheets
        + '</head><body><main class="wrap"><h1>404 — Nenalezeno / Not found</h1>'
        '<p lang="cs">Zadaná adresa nevede k žádnému záznamu v katalogu Průvodce.</p>'
        '<p lang="en">This address does not identify an entry in the Guide’s catalogue.</p>'
        f'<p><a href="{html.escape(catalogue, quote=True)}">Hledat v katalogu / Search the catalogue</a></p>'
        "</main></body></html>\n"
    )


def pages(api: Any, documents: dict[str, dict[str, Any]]) -> dict[str, str]:
    """One static page for every API record at `<kind>/<id>` or the scoped form of that address."""
    builder = RecordPages(api, documents)
    return {
        "404.html": error_page(api),
        **{
            "id/" + path.removeprefix("api/v1/").removesuffix(".json") + ".html": builder.render(path)
            for _, members in api.records.items()
            for _, entity_id in members
            if (path := api.paths[entity_id])
        },
    }
