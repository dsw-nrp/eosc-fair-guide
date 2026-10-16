"""Vendor the favicons of the tools and services the guide names into assets/favicons/, normalised.

Usage: python scripts/vendor_favicons.py [--check | --infrastructures] [--prune] [--input DIR] [--date YYYY-MM-DD]

A tool or service is shown beside its name with its own favicon wherever one can be obtained (D-183). The page
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
import struct
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

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
# Resource types whose entries are tools or services and carry a badge; the FIP Dashboard types map to them.
SERVICE_TYPES = {"service", "tool", "registry"}
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


def service_urls(root: Path = ROOT) -> dict[str, str]:
    """Every tool or service address the guide shows with a badge, by the host whose favicon stands for it; the first
    address of a host is the page asked when its home page cannot be read."""
    content = root / "content"
    guide = _toml(content / "guide.toml")
    dashboard_types = {
        value
        for item in guide.get("resourceType", [])
        if item.get("id") in SERVICE_TYPES
        for value in item.get("fipDashboard", [])
    }
    urls = [
        str(resource.get("url", ""))
        for resource in _toml(content / "resources.toml").get("resource", [])
        if resource.get("type") in SERVICE_TYPES or resource.get("repository")
    ]
    urls += [str(item.get("url", "")) for item in _toml(content / "repositories.toml").get("repository", [])]
    # A record annotation may correct a repository's own address from its site; the guide shows that one, so ask it.
    urls += [str(item.get("url", "")) for item in _toml(content / "repositories.toml").get("record", [])]
    snapshots = content / "snapshots"
    urls += [str(item.get("url", "")) for item in _toml(snapshots / "re3data.toml").get("repository", [])]
    urls += [str(item.get("url", "")) for item in _toml(snapshots / "knav-tools.toml").get("tool", [])]
    urls += [
        str(record.get("url", ""))
        for record in _toml(snapshots / "fip-dashboard.toml").get("resource", [])
        if record.get("type") in dashboard_types
    ]
    hosts: dict[str, str] = {}
    for url in urls:
        host = stands_for(url)
        if host:
            hosts.setdefault(host, url)
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
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - HTTPS addresses only
        final = response.geturl()
        if not final.startswith("https://"):
            raise ValueError("redirected away from HTTPS")
        return final, response.read(limit + 1)


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


def infrastructure_marks(root: Path, fetch: Fetch) -> tuple[dict[str, list[Found]], list[str]]:
    """Reviewed official sites, using an explicit own logo where the site's favicon is generic or absent."""
    items = _toml(root / "content" / "infrastructures.toml").get("infrastructure", [])

    def find(item: dict[str, Any]) -> tuple[str, list[Found]]:
        if not re.fullmatch(r"[a-z0-9-]+", item["id"]):
            raise ValueError("an infrastructure ID must be a lowercase slug")
        key = "infrastructure-" + item["id"]
        url = item.get("website", "")
        host = host_of(url)
        if not host:
            return key, []
        if item.get("logo") is False:
            # A reviewed site has no distinct usable infrastructure mark; do not substitute its institution's icon.
            return key, []
        if item.get("logo"):
            if not str(item["logo"]).startswith("https://"):
                raise ValueError(f"{key}: logo must use HTTPS")
            try:
                _, data = fetch(item["logo"], MAX_SOURCE_BYTES)
                kind = image_kind(data) if len(data) <= MAX_SOURCE_BYTES else None
                found = [Found(host, item["logo"], data, kind)] if kind else []
            except (OSError, ValueError):
                found = []
        else:
            found = favicons(host, url, fetch)
        for mark in found:
            mark.key = key
        return key, found

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        found = dict(pool.map(find, items))
    return found, list(found)


def favicons(host: str, url: str, fetch: Fetch) -> list[Found]:
    """A host's favicons, best first and at most TRIES of them: from its home page's icon links, or the entry's own
    page when the home page cannot be read."""
    found: list[Found] = []
    for page in dict.fromkeys([f"https://{host}/", url]):
        try:
            final, body = fetch(page, MAX_PAGE_BYTES)
        except (OSError, ValueError):
            continue
        if host_of(final) != host:
            # A home page that sends the reader to another site does not speak for this one.
            continue
        # The icon links are in the head; a long page is read only that far.
        for source in candidates(final, body[:MAX_PAGE_BYTES].decode("utf-8", errors="replace")):
            try:
                _, data = fetch(source, MAX_SOURCE_BYTES)
            except (OSError, ValueError):
                continue
            kind = image_kind(data) if len(data) <= MAX_SOURCE_BYTES else None
            if kind and all(item.data != data for item in found):
                found.append(Found(host, source, data, kind))
            if len(found) == TRIES:
                return found
        if found:
            return found
    return found


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
    if not data.startswith(SIGNATURES[0][0]) or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def manifest_text(entries: list[tuple[Found, bytes]], retrieved: str) -> str:
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
            f'host = "{item.host}"',
            f'file = "{item.file or item.stem + ".png"}"',
            f"source = {json.dumps(item.source)}",
            f'sha256 = "{hashlib.sha256(data).hexdigest()}"',
            f"retrieved = {item.retrieved or retrieved}",
        ]
        if item.key:
            lines.append(f'key = "{item.key}"')
        if item.host in PLATFORMS:
            lines.append("homeOnly = true")
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
    hosts = {} if infrastructures_only else service_urls(root)
    previous = _toml(root / MANIFEST)
    if infrastructures_only and (problems := check(root)):
        raise ValueError("existing favicon files must pass --check before a partial refresh: " + "; ".join(problems))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        found = dict(zip(hosts, pool.map(lambda item: favicons(item[0], item[1], fetch), hosts.items()), strict=True))
    marks, mark_keys = infrastructure_marks(root, fetch)
    found.update(marks)
    work = root / WORK
    shutil.rmtree(work, ignore_errors=True)
    originals, normalised = work / "originals", work / "normalised"
    originals.mkdir(parents=True)
    normalised.mkdir()
    try:
        for items in found.values():
            for index, item in enumerate(items):
                (originals / f"{item.stem}~{index}.{item.kind}").write_bytes(item.data)
        normalise(originals, normalised)
        entries: list[tuple[Found, bytes]] = []
        for _host, items in sorted(found.items()):
            for index, item in enumerate(items):
                path = normalised / f"{item.stem}~{index}.png"
                data = path.read_bytes() if path.is_file() else b""
                if png_size(data) == (SIZE, SIZE) and len(data) <= MAX_FILE_BYTES:
                    entries.append((item, data))
                    break
        refreshed = {item.key or item.host for item, _ in entries}
        if not prune:
            entries += carried_entries(root, previous, refreshed)
        entries.sort(key=lambda pair: pair[0].key or pair[0].host)
        # A carried favicon keeps its own file, so a mark that shares one still does; a new one takes the first name.
        shared: dict[str, str] = {}
        for item, data in entries:
            if item.file:
                shared.setdefault(hashlib.sha256(data).hexdigest(), item.file)
        target = root / TARGET
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True)
        for item, data in entries:
            if item.file is None:
                digest = hashlib.sha256(data).hexdigest()
                if item.key:
                    item.file = shared.setdefault(digest, item.stem + ".png")
                else:
                    item.file = item.host + ".png"
                    shared.setdefault(digest, item.file)
            (target / item.file).write_bytes(data)
        (root / MANIFEST).write_text(manifest_text(entries, retrieved), encoding="utf-8", newline="\n")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    kept = {item.stem for item, _ in entries}
    return len(entries), [key for key in [*hosts, *mark_keys] if key not in kept]


def check(root: Path = ROOT) -> list[str]:
    """Problems with the vendored favicons: a recorded file missing, changed or not a SIZE-pixel PNG within the size
    limit, a record without its source, or a file not recorded."""
    problems = []
    records = _toml(root / MANIFEST).get("favicon", [])
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
        path = root / TARGET / name
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
    folder = root / TARGET
    if folder.is_dir():
        for path in folder.iterdir():
            if path.is_file() and path.name != MANIFEST.name and path.name not in recorded:
                problems.append(f"{path.name}: not recorded in {MANIFEST.as_posix()}")
    return problems


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
        return 1 if problems else 0
    fetch = file_fetch(args.input) if args.input else network_fetch
    count, missing = vendor(ROOT, fetch, args.date, infrastructures_only=args.infrastructures, prune=args.prune)
    print(f"vendor_favicons: {count} favicons, {len(missing)} hosts keep their monogram")
    for host in missing:
        print(f"  monogram: {host}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
