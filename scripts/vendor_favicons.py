"""Vendor the favicons of the tools and services the guide names into assets/favicons/, normalised.

Usage: python scripts/vendor_favicons.py [--check | --infrastructures] [--prune] [--input DIR] [--date YYYY-MM-DD]

A tool or service is shown beside its name with its own favicon wherever one can be obtained. The page
requests nothing from other sites when it loads, so each favicon is taken from its site here and normalised once to a
square PNG of SIZE pixels (scripts/normalise_favicons.mjs, in the Playwright Chromium the page checks use); the
original is not kept. `assets/favicons/sources.toml` records, for each host, the file, the address the icon was taken
from and the file's SHA-256. One favicon stands for one host. A host that serves many tools (a code-hosting platform,
a DOI resolver) stands only for itself: a tool found only there keeps its monogram, and so does a site whose favicon
cannot be obtained or does not draw.

Without `--check` the script asks every host for its favicon and writes what it obtains; a host it does not obtain
again keeps the favicon already recorded, so a refresh drops nothing it already has. `--prune` removes recorded
favicons that were not obtained again, the only way a refresh deletes one. With `--check` it changes nothing and exits
1 when a recorded file is missing, changed, not a SIZE-pixel PNG or unrecorded. `--input DIR` reads responses from
files named by `response_name()` instead of the network (for tests). Fetching uses only the standard library; on a
machine whose certificate store refuses sites that verify elsewhere, point SSL_CERT_FILE at a current CA bundle.
Normalising needs Node and the Playwright browser (`npm ci`, `npx playwright install chromium`).

Infrastructure marks use their reviewed `website` and, where a generic site favicon is unsuitable, an explicit
`logo` from that official site. They are keyed by infrastructure, so a faculty's favicon is never inferred from a
portal page. `--infrastructures` refreshes only those marks, retaining verified service files and their retrieval
dates. Identical normalised marks share one file. A full refresh includes both services and infrastructures.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import build_crate as kb
import public_https
from refresh_snapshots import identity_content

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path("assets") / "favicons"
MANIFEST = TARGET / "sources.toml"
WORK = Path(".cache") / "favicons"
NORMALISER = Path("scripts") / "normalise_favicons.mjs"
# The favicon's side in pixels: the badge shows it at 24 CSS pixels, sharp up to a device pixel ratio of two.
SIZE = 48
MAX_SOURCE_BYTES = 256 * 1024
MAX_FILE_BYTES = 16 * 1024
MAX_PAGE_BYTES = 512 * 1024
# Icons tried per host, in the order of candidates(): the first that shows on a badge is kept.
TRIES = 3
TIMEOUT = 15
USER_AGENT = "eosc-fair-guide-favicons/1.0 (+https://github.com/dsw-nrp/eosc-fair-guide)"
ACCEPT = "text/html,image/*;q=0.9,*/*;q=0.8"
# Hosts that serve many tools or records: their favicon stands only for an entry at the host's own home page.
PLATFORMS = {
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "codeberg.org",
    "sourceforge.net",
    "pypi.org",
    "cran.r-project.org",
    "doi.org",
    "hdl.handle.net",
    "w3id.org",
    "purl.org",
    "zenodo.org",
    # A repository whose home page is not served over HTTPS is linked by its re3data record.
    "re3data.org",
    "repo.cz",
    "figshare.com",
    "osf.io",
    "sites.google.com",
    "docs.google.com",
    "vyzkumne-infrastruktury.cz",
}
# Image types by their first bytes, and the extension an original is kept under while it is normalised.
SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\x00\x00\x01\x00", "ico"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"\xff\xd8\xff", "jpg"),
)
# What an SVG icon may not contain: scripts, event handlers, embedded documents or a reference outside itself.
SVG_REFUSED = re.compile(rb"<script|javascript:|<foreignobject|\son[a-z]+\s*=|href\s*=\s*[\"'](?!#|data:image/)")

Fetch = Callable[[str, int], tuple[str, bytes]]
Normalise = Callable[[Path, Path], list[str]]


def host_of(url: str) -> str | None:
    """The host a favicon stands for: lower case, without "www."; none for an address that is not HTTPS."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        return None
    return parts.hostname.lower().removeprefix("www.")


def stands_for(url: str) -> str | None:
    """The host whose favicon may stand for the entry at this address, or none (a tool on a platform)."""
    host = host_of(url)
    if host is None:
        return None
    if host in PLATFORMS and urllib.parse.urlsplit(url).path.strip("/"):
        return None
    return host


def _toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def service_urls(root: Path = ROOT, excluded: list[str] | None = None) -> dict[str, str]:
    """Every tool or service address the guide shows with a badge, by the host whose favicon stands for it; the first
    address of a host is the page asked when its home page cannot be read."""
    content = identity_content(root)
    eligible = set(kb.favicon_types(content["guide"]))
    graph, addresses = kb.catalogue_identity_graph(content)
    rows = kb.catalogue_records(content)
    sources = {kb.source_key(row): row for row in content["sources"]}
    rows.update(sources)
    crosswalk = kb.type_crosswalk(content["guide"])
    hosts: dict[str, str] = {}
    for key, address in addresses.items():
        if address.split("/")[0] not in ("resources", "repositories"):
            continue
        row, entity = rows.get(key, {}), graph.entities[key]
        if key.startswith("#knav-"):
            kind = "tool"
        elif key.startswith("#fer-"):
            kind = crosswalk.get("fd:" + row.get("type", ""))
        elif key in sources:
            kind = crosswalk.get("form:" + row.get("type", ""))
        else:
            kind = row.get("type")
        if address.startswith("repositories/") or kind in eligible or row.get("type") == "repository":
            url = str(entity.get(kb.PRECEDENCE, {}).get("url") or entity.get("url") or "")
            if host := stands_for(url):
                hosts.setdefault(host, url)
            elif url and excluded is not None:
                excluded.append(url)
    return dict(sorted(hosts.items()))


class _Icons(HTMLParser):
    """The icon links of a page, in document order: (rel, href, type, sizes)."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str, str, str]] = []
        self.base: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        if tag == "base" and values.get("href") and self.base is None:
            self.base = values["href"]
        if tag == "link" and values.get("href"):
            rel = values.get("rel", "").lower().split()
            if "icon" in rel or "apple-touch-icon" in rel:
                kind = "apple-touch-icon" if "apple-touch-icon" in rel else "icon"
                self.links.append(
                    (kind, values["href"], values.get("type", "").lower(), values.get("sizes", "").lower())
                )


def _size(sizes: str) -> int:
    found = [int(match) for match in re.findall(r"(\d+)x\d+", sizes)]
    return min(found) if found else 0


def candidates(page_url: str, html: str) -> list[str]:
    """The icon addresses to try, best for a SIZE-pixel image first: an SVG icon, the smallest raster icon of at least
    SIZE pixels, then of at least 32, an icon of unstated size, the touch icon, a smaller icon, and the site's
    /favicon.ico."""
    parser = _Icons()
    parser.feed(html)
    base = urllib.parse.urljoin(page_url, parser.base) if parser.base else page_url

    def rank(link: tuple[str, str, str, str]) -> tuple[int, int]:
        kind, href, mime, sizes = link
        size = _size(sizes)
        if kind == "icon" and (mime == "image/svg+xml" or href.lower().split("?")[0].endswith(".svg")):
            return (0, 0)
        if kind == "icon" and size >= SIZE:
            return (1, size)
        if kind == "icon" and size >= 32:
            return (2, size)
        if kind == "icon" and not size:
            return (3, 0)
        if kind == "apple-touch-icon":
            return (4, size)
        return (5, -size)

    ordered = [urllib.parse.urljoin(base, link[1]) for link in sorted(parser.links, key=rank)]
    ordered.append(urllib.parse.urljoin(page_url, "/favicon.ico"))
    return list(dict.fromkeys(url for url in ordered if url.startswith("https://")))


def image_kind(data: bytes) -> str | None:
    """The extension an original is kept under while it is normalised, from its bytes; none for anything that is not
    a plain image. An SVG with scripts, event handlers, embedded documents or outside references is refused."""
    for signature, extension in SIGNATURES:
        if data.startswith(signature):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    head = data[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith((b"<svg", b"<?xml", b"<!--")) and b"<svg" in data[:4096].lower():
        return None if SVG_REFUSED.search(data.lower()) else "svg"
    return None


def network_fetch(url: str, limit: int) -> tuple[str, bytes]:
    """The final address and the first `limit` + 1 bytes of a response, so a caller can tell a larger body; raises on
    an error status or a redirect away from HTTPS."""
    return public_https.fetch(url, limit, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})


def response_name(url: str) -> str:
    """The file a recorded response for an address is read from (`--input`)."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def file_fetch(folder: Path) -> Fetch:
    def fetch(url: str, limit: int) -> tuple[str, bytes]:
        path = folder / response_name(url)
        if not path.is_file():
            raise FileNotFoundError(url)
        return url, path.read_bytes()[: limit + 1]

    return fetch


@dataclass
class Found:
    host: str
    source: str
    data: bytes
    kind: str
    key: str | None = None
    retrieved: str | None = None
    file: str | None = None

    @property
    def stem(self) -> str:
        """A safe local identity, distinct from the website when an infrastructure shares its host."""
        return self.key or self.host


@dataclass
class Acquisition:
    host: str
    found: list[Found] = field(default_factory=list)
    failure: str | None = None
    attempted: bool = True


REASONS = {
    "available": {"acquired"},
    "unavailable": {"no-usable-image", "not-renderable"},
    "failed": {
        "timeout",
        "rate-limited",
        "service-error",
        "network-error",
        "redirect-refused",
        "destination-refused",
        "response-too-large",
    },
}


def failure_reason(error: Exception) -> str | None:
    """A definitive missing response is negative evidence; transport and service errors are retryable."""
    if isinstance(error, public_https.DestinationRefusedError):
        return "destination-refused"
    if isinstance(error, urllib.error.HTTPError):
        code = error.code
        error.close()
        return None if code in (404, 410) else "rate-limited" if code == 429 else "service-error"
    if isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError):
        return "timeout"
    return "redirect-refused" if isinstance(error, ValueError) else "network-error"


def infrastructure_marks(root: Path, fetch: Fetch) -> tuple[dict[str, Acquisition], list[str]]:
    """Reviewed official sites, using an explicit own logo where the site's favicon is generic or absent."""
    items = _toml(root / "content" / "infrastructures.toml").get("infrastructure", [])

    def find(item: dict[str, Any]) -> tuple[str, Acquisition]:
        if not re.fullmatch(r"[a-z0-9-]+", item["id"]):
            raise ValueError("an infrastructure ID must be a lowercase slug")
        key = "infrastructure-" + item["id"]
        url = item.get("website", "")
        host = host_of(url)
        if not host:
            return key, Acquisition("", attempted=False)
        if item.get("logo") is False:
            # A reviewed site has no distinct usable infrastructure mark; do not substitute its institution's icon.
            return key, Acquisition(host, attempted=False)
        if item.get("logo"):
            if not str(item["logo"]).startswith("https://"):
                raise ValueError(f"{key}: logo must use HTTPS")
            try:
                final, data = fetch(item["logo"], MAX_SOURCE_BYTES)
                if not final.startswith("https://"):
                    raise ValueError("redirected away from HTTPS")
                kind = image_kind(data) if len(data) <= MAX_SOURCE_BYTES else None
                attempt = Acquisition(host, [Found(host, item["logo"], data, kind)] if kind else [])
            except (OSError, ValueError) as error:
                attempt = Acquisition(host, failure=failure_reason(error))
        else:
            attempt = acquire(host, url, fetch)
        for mark in attempt.found:
            mark.key = key
        return key, attempt

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        found = dict(pool.map(find, items))
    return found, list(found)


def acquire(host: str, url: str, fetch: Fetch) -> Acquisition:
    """A host's favicons, best first and at most TRIES of them: from its home page's icon links, or the entry's own
    page when the home page cannot be read."""
    attempt = Acquisition(host)
    found = attempt.found
    for page in dict.fromkeys([f"https://{host}/", url]):
        try:
            final, body = fetch(page, MAX_PAGE_BYTES)
        except (OSError, ValueError) as error:
            attempt.failure = failure_reason(error) or attempt.failure
            continue
        if host_of(final) != host:
            # A home page that sends the reader to another site does not speak for this one.
            attempt.failure = "redirect-refused"
            continue
        if len(body) > MAX_PAGE_BYTES:
            attempt.failure = "response-too-large"
        # The icon links are in the head; a long page is read only that far.
        for source in candidates(final, body[:MAX_PAGE_BYTES].decode("utf-8", errors="replace")):
            try:
                final_source, data = fetch(source, MAX_SOURCE_BYTES)
                if not final_source.startswith("https://"):
                    raise ValueError("redirected away from HTTPS")
            except (OSError, ValueError) as error:
                attempt.failure = failure_reason(error) or attempt.failure
                continue
            kind = image_kind(data) if len(data) <= MAX_SOURCE_BYTES else None
            if kind and all(item.data != data for item in found):
                found.append(Found(host, source, data, kind))
            if len(found) == TRIES:
                return attempt
        if found:
            return attempt
    return attempt


def node_normalise(originals: Path, output: Path) -> list[str]:
    """Normalise the originals with the browser; the hosts whose image did not draw."""
    node = shutil.which("node")
    if not node:
        raise SystemExit("vendor_favicons: Node is needed to normalise favicons; run npm ci")
    result = subprocess.run(  # noqa: S603 - fixed script and folders
        [node, str(ROOT / NORMALISER), str(originals), str(output), str(SIZE)],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])["failed"]


def png_size(data: bytes) -> tuple[int, int] | None:
    """A PNG's width and height from its header, or none for anything else."""
    if len(data) < 24 or not data.startswith(SIGNATURES[0][0]) or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def manifest_text(entries: list[tuple[Found, bytes]], retrieved: str, observations: list[dict[str, Any]]) -> str:
    lines = [
        "# The favicons in this folder, as scripts/vendor_favicons.py took and normalised them: the host each",
        f"# stands for, the file (a {SIZE}-pixel PNG), the address the icon was taken from and the file's SHA-256.",
        "# Generated; do not edit by hand.",
        "",
        "[favicons]",
        f"retrieved = {retrieved}",
        f"size = {SIZE}",
    ]
    for item, data in entries:
        lines += [
            "",
            "[[favicon]]",
            f"host = {json.dumps(item.host)}",
            f"file = {json.dumps(item.file or item.stem + '.png')}",
            f"source = {json.dumps(item.source)}",
            f'sha256 = "{hashlib.sha256(data).hexdigest()}"',
            f"retrieved = {item.retrieved or retrieved}",
        ]
        if item.key:
            lines.append(f"key = {json.dumps(item.key)}")
        if item.host in PLATFORMS:
            lines.append("homeOnly = true")
    for observation in sorted(observations, key=lambda item: item.get("key") or item["host"]):
        lines += ["", "[[observation]]"]
        lines += [
            f"{key} = {value}" if key == "checked" else f"{key} = {json.dumps(value)}"
            for key, value in observation.items()
        ]
    return "\n".join(lines) + "\n"


def carried_entries(root: Path, previous: dict[str, Any], refreshed: set[str]) -> list[tuple[Found, bytes]]:
    """The recorded favicons a refresh did not obtain again, kept exactly as recorded: the file, the address it was
    taken from and its date, so a run that cannot reach a site drops nothing. `--prune` is the only way a refresh
    removes one."""
    fallback = str((previous.get("favicons") or {}).get("retrieved", ""))
    kept: list[tuple[Found, bytes]] = []
    for row in previous.get("favicon", []):
        identity = row.get("key") or row.get("host")
        path = root / TARGET / row["file"]
        if identity in refreshed or not path.is_file():
            continue
        item = Found(
            row["host"],
            row["source"],
            path.read_bytes(),
            "png",
            key=row.get("key"),
            retrieved=str(row.get("retrieved") or fallback),
            file=row["file"],
        )
        kept.append((item, item.data))
    return kept


def is_link_or_reparse(path: Path) -> bool:
    """Inspect links and Windows reparse points without requiring Python 3.12 Path helpers."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def owned_folder(root: Path, folder: Path) -> None:
    """Refuse filesystem operations outside this run's literal assets directory or through directory links."""
    parent = root.resolve() / "assets"
    if (
        folder.parent.resolve() != parent
        or folder.name in {"", ".", ".."}
        or is_link_or_reparse(parent)
        or is_link_or_reparse(folder)
    ):
        raise ValueError(f"unsafe favicon directory: {folder}")


def working_path(folder: Path, item: Found, index: int, extension: str) -> Path:
    """An image filename derived only from a validated identity inside its owned work folder."""
    names = (item.host, item.stem)
    if any(
        not isinstance(name, str) or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", name) or ".." in name
        for name in names
    ):
        raise ValueError("invalid favicon working identity")
    if extension not in {"png", "ico", "svg", "gif", "jpeg", "jpg", "webp"}:
        raise ValueError("invalid favicon working identity image format")
    path = folder / f"{item.stem}~{index}.{extension}"
    if path.resolve().parent != folder.resolve() or is_link_or_reparse(path):
        raise ValueError("favicon working identity escapes its directory")
    return path


def recover_publication(root: Path) -> None:
    """Recover a process stop between renames before the usual existing-set integrity guard."""
    target, backup = root / TARGET, root / "assets/.favicons-backup"
    for folder in (target, backup):
        owned_folder(root, folder)
    if backup.exists():
        # A complete installed set also permits cleanup after an interrupted backup removal.
        verified = target if target.exists() else backup
        if not (verified / MANIFEST.name).is_file() or check(root, folder=verified):
            raise ValueError(f"cannot recover favicon publication: verify {verified}")
        if target.exists():
            shutil.rmtree(backup)
        else:
            backup.replace(target)
    for stage in target.parent.glob(".favicons-stage-*"):
        owned_folder(root, stage)
        if stage.is_dir():
            shutil.rmtree(stage)


def publish(root: Path, entries: list[tuple[Found, bytes]], manifest: str) -> None:
    """Validate a complete sibling set, then install it while keeping the prior set recoverable."""
    target, backup = root / TARGET, root / "assets/.favicons-backup"
    for folder in (target, backup):
        owned_folder(root, folder)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".favicons-stage-", dir=target.parent))
    owned_folder(root, stage)
    try:
        for item, data in entries:
            if not item.file or not re.fullmatch(r"[a-z0-9.-]+\.png", item.file):
                raise ValueError(f"invalid local filename: {item.file}")
            (stage / item.file).write_bytes(data)
        (stage / MANIFEST.name).write_text(manifest, encoding="utf-8", newline="\n")
        if problems := check(root, folder=stage):
            raise ValueError("staged favicons failed verification: " + "; ".join(problems))
        if backup.exists():
            raise ValueError("favicon backup must be recovered before publication")
        if target.exists():
            target.replace(backup)
        try:
            stage.replace(target)
        except BaseException:
            if backup.exists() and not target.exists():
                backup.replace(target)
            raise
        if backup.exists():
            owned_folder(root, backup)
            shutil.rmtree(backup)
    finally:
        if stage.exists():
            owned_folder(root, stage)
            shutil.rmtree(stage)


def vendor(
    root: Path,
    fetch: Fetch,
    retrieved: str,
    normalise: Normalise = node_normalise,
    *,
    infrastructures_only: bool = False,
    prune: bool = False,
) -> tuple[int, list[str]]:
    """Ask every host for its favicon and write what is obtained; a recorded favicon the run does not obtain again is
    kept as it was, so a refresh that cannot reach a site drops nothing. `prune` removes the recorded favicons not
    obtained again, the only deletion a refresh makes. The originals live only in the work folder, which is removed."""
    if date.fromisoformat(retrieved).isoformat() != retrieved or date.fromisoformat(retrieved) > date.today():
        raise ValueError("retrieved must be a real, non-future ISO date")
    recover_publication(root)
    hosts = {} if infrastructures_only else service_urls(root)
    previous = _toml(root / MANIFEST)
    # Acquisition alone may create the first set; the read-only checker always requires a recorded one.
    if (root / TARGET).exists() and (problems := check(root)):
        raise ValueError("existing favicon files must pass --check before refresh: " + "; ".join(problems))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        attempts = dict(zip(hosts, pool.map(lambda item: acquire(item[0], item[1], fetch), hosts.items()), strict=True))
    marks, mark_keys = infrastructure_marks(root, fetch)
    attempts.update(marks)
    found = {key: attempt.found for key, attempt in attempts.items()}
    work = root / WORK
    if (
        work.parent.resolve() != root.resolve() / WORK.parent
        or is_link_or_reparse(work.parent)
        or is_link_or_reparse(work)
    ):
        raise ValueError("unsafe favicon working directory")
    shutil.rmtree(work, ignore_errors=True)
    originals, normalised = work / "originals", work / "normalised"
    originals.mkdir(parents=True)
    normalised.mkdir()
    try:
        prepared = [
            (working_path(originals, item, index, item.kind), item.data)
            for items in found.values()
            for index, item in enumerate(items)
        ]
        for path, data in prepared:
            path.write_bytes(data)
        normalise(originals, normalised)
        entries: list[tuple[Found, bytes]] = []
        for _host, items in sorted(found.items()):
            for index, item in enumerate(items):
                path = working_path(normalised, item, index, "png")
                data = path.read_bytes() if path.is_file() else b""
                if png_size(data) == (SIZE, SIZE) and len(data) <= MAX_FILE_BYTES:
                    entries.append((item, data))
                    break
        refreshed = {item.key or item.host for item, _ in entries}
        observations = {row.get("key") or row["host"]: row for row in previous.get("observation", [])}
        for identity, attempt in attempts.items():
            if not attempt.attempted:
                continue
            outcome = "available" if identity in refreshed else "failed" if attempt.failure else "unavailable"
            reason = (
                "acquired"
                if outcome == "available"
                else attempt.failure or ("not-renderable" if attempt.found else "no-usable-image")
            )
            observations[identity] = {"host": attempt.host, "checked": retrieved, "outcome": outcome, "reason": reason}
            if identity != attempt.host:
                observations[identity]["key"] = identity
        if not prune:
            entries += carried_entries(root, previous, refreshed)
        else:
            # A deliberately pruned positive acquisition no longer claims an available local asset.
            observations = {
                key: row for key, row in observations.items() if row["outcome"] != "available" or key in refreshed
            }
        entries.sort(key=lambda pair: pair[0].key or pair[0].host)
        # A carried favicon keeps its own file, so a mark that shares one still does; a new one takes the first name.
        shared: dict[str, str] = {}
        for item, data in entries:
            if item.file:
                shared.setdefault(hashlib.sha256(data).hexdigest(), item.file)
        for item, data in entries:
            if item.file is None:
                digest = hashlib.sha256(data).hexdigest()
                if item.key:
                    item.file = shared.setdefault(digest, item.stem + ".png")
                else:
                    item.file = item.host + ".png"
                    shared.setdefault(digest, item.file)
        publish(root, entries, manifest_text(entries, retrieved, list(observations.values())))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    kept = {item.stem for item, _ in entries}
    return len(entries), [key for key in [*hosts, *mark_keys] if key not in kept]


def check(root: Path = ROOT, *, folder: Path | None = None) -> list[str]:
    """Problems with the vendored favicons: a recorded file missing, changed or not a SIZE-pixel PNG within the size
    limit, a record without its source, or a file not recorded."""
    problems = []
    folder = folder if folder is not None else root / TARGET
    if not folder.is_dir():
        return ["favicon asset directory is missing"]
    if not (folder / MANIFEST.name).is_file():
        return ["favicon manifest is missing"]
    try:
        manifest = _toml(folder / MANIFEST.name)
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"favicon manifest is unreadable: {error}"]
    metadata = manifest.get("favicons", {})
    if (
        not isinstance(metadata, dict)
        or type(metadata.get("size")) is not int
        or metadata.get("size") != SIZE
        or type(metadata.get("retrieved")) is not date
        or metadata["retrieved"] > date.today()
    ):
        problems.append("favicon set metadata must record its size and valid retrieval date")
    records = manifest.get("favicon", [])
    recorded = {item["file"] for item in records}
    identities = set()
    for item in records:
        name = item["file"]
        identity = item.get("key", item.get("host"))
        if identity in identities:
            problems.append(f"{identity}: duplicate favicon identity")
        identities.add(identity)
        if not re.fullmatch(r"[a-z0-9.-]+\.png", name) or (not item.get("key") and name != f"{item.get('host')}.png"):
            problems.append(f"{name}: invalid local filename")
            continue
        path = folder / name
        if not path.is_file():
            problems.append(f"{name}: recorded but missing")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item.get("sha256"):
            problems.append(f"{name}: differs from the recorded file")
        if png_size(data) != (SIZE, SIZE) or len(data) > MAX_FILE_BYTES:
            problems.append(f"{name}: not a {SIZE}-pixel PNG within {MAX_FILE_BYTES // 1024} KB")
        if not str(item.get("source", "")).startswith("https://") or not re.fullmatch(r"[a-z0-9.-]+\.png", name):
            problems.append(f"{name}: its source or host is not recorded")
        if type(item.get("retrieved")) is not date or item["retrieved"] > date.today():
            problems.append(f"{identity}: invalid asset retrieval date")
        if item.get("host") in PLATFORMS and item.get("homeOnly") is not True:
            problems.append(f"{identity}: guarded platform requires homeOnly")
    observed = set()
    for row in manifest.get("observation", []):
        if not isinstance(row, dict):
            problems.append("observation: expected a table")
            continue
        host, key = row.get("host"), row.get("key")
        identity = key or host
        if not isinstance(identity, str):
            problems.append(f"{identity!r}: invalid observation identity")
            continue
        if identity in observed:
            problems.append(f"{identity}: duplicate observation identity")
        observed.add(identity)
        if (
            not isinstance(host, str)
            or not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", host)
            or (key is not None and (not isinstance(key, str) or not re.fullmatch(r"infrastructure-[a-z0-9-]+", key)))
        ):
            problems.append(f"{identity}: invalid observation identity")
        if type(row.get("checked")) is not date or row["checked"] > date.today():
            problems.append(f"{identity}: invalid checked date")
        outcome = row.get("outcome")
        if (
            not isinstance(outcome, str)
            or outcome not in REASONS
            or not isinstance(row.get("reason"), str)
            or row["reason"] not in REASONS.get(outcome, set())
        ):
            problems.append(f"{identity}: invalid outcome/reason")
        if outcome == "available":
            asset = next((item for item in records if (item.get("key") or item.get("host")) == identity), None)
            if not asset or asset.get("host") != host or asset.get("retrieved") != row.get("checked"):
                problems.append(f"{identity}: available observation has no matching acquisition")
        if set(row) - {"host", "key", "checked", "outcome", "reason"}:
            problems.append(f"{identity}: unknown observation field")
    if folder.is_dir():
        for path in folder.iterdir():
            if path.is_file() and path.name != MANIFEST.name and path.name not in recorded:
                problems.append(f"{path.name}: not recorded in {MANIFEST.as_posix()}")
    return problems


def coverage(root: Path = ROOT) -> dict[str, list[str]]:
    """Asset availability and latest attempts are separate axes; retained icons can have failed new attempts."""
    excluded: list[str] = []
    hosts = service_urls(root, excluded)
    active = set(hosts)
    for item in _toml(root / "content/infrastructures.toml").get("infrastructure", []):
        key = "infrastructure-" + item["id"]
        if item.get("logo") is False or not host_of(item.get("website", "")):
            excluded.append(key)
        else:
            active.add(key)
    manifest = _toml(root / MANIFEST)
    assets = {item.get("key") or item["host"] for item in manifest.get("favicon", [])}
    observations = {item.get("key") or item["host"]: item for item in manifest.get("observation", [])}
    attempted = active & set(observations)
    return {
        "eligible": sorted(active),
        "availableAssets": sorted(active & assets),
        "attempted": sorted(attempted),
        "acquired": sorted(key for key in attempted if observations[key]["outcome"] == "available"),
        "unavailable": sorted(key for key in attempted if observations[key]["outcome"] == "unavailable"),
        "failed": sorted(key for key in attempted if observations[key]["outcome"] == "failed"),
        "unattempted": sorted(active - attempted),
        "excluded": sorted(set(excluded)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report problems instead of fetching; exit 1 on any")
    parser.add_argument(
        "--infrastructures",
        action="store_true",
        help="refresh only infrastructure marks, keeping verified service files",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="drop recorded favicons not obtained again; the only way a refresh deletes one",
    )
    parser.add_argument("--input", type=Path, help="read responses from this folder instead of the network")
    parser.add_argument("--date", default=date.today().isoformat(), help="retrieval date to record (YYYY-MM-DD)")
    args = parser.parse_args(argv)
    if args.prune and args.infrastructures:
        parser.error("--prune cannot be combined with --infrastructures, which keeps every verified service file")
    if args.check:
        problems = check(ROOT)
        for problem in problems:
            print(f"vendor_favicons: {problem}", file=sys.stderr)
        count = len(_toml(ROOT / MANIFEST).get("favicon", []))
        print(f"vendor_favicons: {count} favicons recorded, {len(problems)} problem(s)")
        print("coverage: " + ", ".join(f"{key}={len(values)}" for key, values in coverage(ROOT).items()))
        return 1 if problems else 0
    fetch = file_fetch(args.input) if args.input else network_fetch
    count, missing = vendor(ROOT, fetch, args.date, infrastructures_only=args.infrastructures, prune=args.prune)
    print(f"vendor_favicons: {count} favicons, {len(missing)} hosts keep their monogram")
    for host in missing:
        print(f"  monogram: {host}")
    for category, identities in coverage(ROOT).items():
        print(f"{category} ({len(identities)}): " + ", ".join(identities))
    return 0


if __name__ == "__main__":
    sys.exit(main())
