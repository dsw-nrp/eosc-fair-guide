#!/usr/bin/env python3
"""Assemble Pages from an unchanged verified release archive and the checked default-branch preview.

    python scripts/assemble_pages.py --staging _site --staging-commit SHA --out .cache/pages
        [--production .cache/release --production-tag vX.Y.Z --production-commit SHA]

Production bytes come only from the digest-checked release artifact. Every preview HTML page gets noindex and a
bilingual notice; preview files are under next/, without adding them to production discovery documents. With no
release yet the root explains that only a preview exists. All inputs and output locations are checked before the
managed output is replaced. This command never fetches, builds, tags or publishes anything.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
import re
import tarfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import build_crate
import package_site
from publication_location import preview_blocked, site_identity, verify_declaration

ROOT = Path(__file__).resolve().parent.parent
SHA = re.compile(r"[0-9a-f]{40}")
TAG = re.compile(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")
MAX_BYTES = 512 * 1024 * 1024
NOTICE = (
    '<aside class="staging-notice" aria-label="Preview / Náhled">'
    '<span lang="cs">Náhled připravované verze.</span> '
    '<span lang="en">Preview of the next release.</span></aside>'
)
# Tag release always tags a commit the preview already serves, built before the tag existed: until the default branch
# moves on, the preview is the release, and says so instead of announcing a next one.
RELEASED_NOTICE = (
    '<aside class="staging-notice" aria-label="Preview / Náhled">'
    '<span lang="cs">Tento náhled je totožný s vydáním {tag} (commit {commit}).</span> '
    '<span lang="en">This preview is identical to release {tag} (commit {commit}).</span> '
    '<a href="{home}"><span lang="cs">Otevřít vydání</span> / <span lang="en">Open the release</span></a></aside>'
)


def release_notice(name: str, tag: str, commit: str) -> str:
    """The notice of preview page `name` when its commit is the published release's, linking the release root."""
    home = posixpath.relpath("index.html", str(PurePosixPath("next", name).parent))
    return RELEASED_NOTICE.format(tag=html.escape(tag), commit=commit[:7], home=html.escape(home, quote=True))


class AssemblyError(ValueError):
    """A deployment input cannot be verified or safely combined."""


class PreviewMarkup(HTMLParser):
    """Locate head/body and old robots declarations, preserving every other original byte of markup."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        self.offsets.extend(match.end() for match in re.finditer("\n", text))
        self.head: int | None = None
        self.body: int | None = None
        self.robots: list[tuple[int, int]] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, column = self.getpos()
        start = self.offsets[line - 1] + column
        end = start + len(self.get_starttag_text())
        if tag in {"head", "body"}:
            if getattr(self, tag) is not None:
                raise AssemblyError(f"multiple {tag} elements")
            setattr(self, tag, end)
        if tag == "meta" and str(dict(attrs).get("name", "")).lower() == "robots":
            self.robots.append((start, end))

    handle_startendtag = handle_starttag


def preview_html(data: bytes, name: str, notice: str = NOTICE) -> bytes:
    text = data.decode("utf-8")
    parsed = PreviewMarkup(text)
    if parsed.head is None or parsed.body is None:
        raise AssemblyError(f"{name}: HTML requires head and body")
    style = posixpath.relpath("assets/css/staging.css", str(PurePosixPath(name).parent))
    changes = [(start, end, "") for start, end in parsed.robots]
    changes.extend(
        [
            (
                parsed.head,
                parsed.head,
                '\n<meta name="robots" content="noindex">'
                f'\n<link rel="stylesheet" href="{html.escape(style, quote=True)}">',
            ),
            (parsed.body, parsed.body, "\n" + notice),
        ]
    )
    for start, end, value in sorted(changes, reverse=True):
        text = text[:start] + value + text[end:]
    return text.encode("utf-8")


def safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and str(path) == name
        and not any(
            part in {"", ".", ".."}
            or "\\" in part
            or ":" in part
            or part.rstrip(" .") != part
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
            for part in path.parts
        )
    )


def production_files(directory: Path, tag: str, commit: str) -> dict[str, bytes]:
    if not TAG.fullmatch(tag) or not SHA.fullmatch(commit):
        raise AssemblyError("production requires a release tag and full commit SHA")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    name = manifest.get("archive", "")
    if not safe_name(name) or "/" in name or not name.endswith(".tar.gz"):
        raise AssemblyError("unsafe release archive name")
    if manifest.get("commit") != commit or manifest.get("version") != tag[1:]:
        raise AssemblyError("release artifact commit/version does not match the selected tag")
    if manifest.get("health", {}).get("run") != "passed" or not manifest["health"].get("generated_at"):
        raise AssemblyError("release artifact has no passed check run")
    archive = directory / name
    if archive.stat().st_size > MAX_BYTES:
        raise AssemblyError("release archive is too large")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    declared = (directory / (name + ".sha256")).read_text(encoding="utf-8").split()[0]
    if digest != manifest.get("sha256") or digest != declared:
        raise AssemblyError("release archive digest mismatch")
    files: dict[str, bytes] = {}
    total = 0
    with tarfile.open(archive, "r:gz") as packed:
        for member in packed:
            if not member.isfile() or not safe_name(member.name) or member.name in files:
                raise AssemblyError("release archive contains unsafe or duplicate members")
            if PurePosixPath(member.name).parts[0] == "next":
                raise AssemblyError("a release archive must not contain the preview")
            total += member.size
            if total > MAX_BYTES or len(files) >= 10000:
                raise AssemblyError("release archive exceeds the assembly bounds")
            stream = packed.extractfile(member)
            if stream is None:
                raise AssemblyError("release archive member is unreadable")
            files[member.name] = stream.read()
    if "index.html" not in files or package_site.HEALTH not in files:
        raise AssemblyError("release archive lacks the Guide or health result")
    health = json.loads(files[package_site.HEALTH])
    if health.get("run", {}).get("status") != "passed" or health.get("revision") != commit:
        raise AssemblyError("release archive health does not name the checked commit")
    try:
        verify_declaration(files, manifest)
    except ValueError as error:
        raise AssemblyError(str(error)) from error
    return files


def validate_files(files: dict[str, bytes]) -> None:
    names = {name.casefold() for name in files}
    parents = {str(parent).casefold() for name in files for parent in PurePosixPath(name).parents if str(parent) != "."}
    if len(names) != len(files) or names & parents or not all(safe_name(name) for name in files):
        raise AssemblyError("deployment paths contain aliases or file/directory collisions")


def assemble(
    staging: Path,
    staging_commit: str,
    out: Path,
    *,
    production: Path | None = None,
    production_tag: str | None = None,
    production_commit: str | None = None,
    root: Path = ROOT,
) -> list[str]:
    """Assemble the release and the preview, returning the notices a maintainer should read in the summary."""
    notices: list[str] = []
    output = build_crate.site_directory(out, root)
    stage = build_crate.require_site(staging)
    inputs = [stage, *([production.resolve()] if production else [])]
    if any(output == path or output in path.parents or path in output.parents for path in inputs):
        raise AssemblyError("assembly output overlaps an input")
    if not SHA.fullmatch(staging_commit):
        raise AssemblyError("staging requires a full commit SHA")
    report = package_site.verified_health(stage)
    if report.get("revision") != staging_commit:
        raise AssemblyError("staging health does not name the checked commit")
    if production is None and (production_tag or production_commit):
        raise AssemblyError("production tag/commit require a release artifact")
    files = production_files(production, production_tag or "", production_commit or "") if production else {}
    if production:
        preview = built_for(stage)
        active = site_identity(files)
        manifest = json.loads((production / "manifest.json").read_text("utf-8"))
        # A stamped release names the root it was built for; an older archive's recorded address may be a predicted
        # host, so only stamped releases are compared.
        if "semantic" in manifest and active["publication_url"] != preview["publication_url"]:
            raise AssemblyError(
                "production and preview were built for different publication roots; rerun the deployment so that "
                "both are built for the current one"
            )
        # The namespace is a reviewed setting that changes before the release that carries it (decision 28).
        if (active["vocabulary_base"], active["profile"]) != (preview["vocabulary_base"], preview["profile"]):
            notices.append(
                f"The preview names the Guide vocabulary `{preview['vocabulary_base']}` and profile "
                f"`{preview['profile']}`; production keeps `{active['vocabulary_base']}` and `{active['profile']}` "
                "until the next release aligns them."
            )
        paths = ["/next/", *("/next/" + path.relative_to(stage).as_posix() for path in stage.rglob("*.html"))]
        if urlsplit(preview["publication_url"]).path == "/" and preview_blocked(
            files.get("robots.txt", b"").decode("utf-8"), paths
        ):
            raise AssemblyError("root robots policy blocks reading preview noindex; prepare a corrected release")
    released = production is not None and production_commit == staging_commit
    if not production:
        files["index.html"] = (
            '<!doctype html><html lang="cs"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width"><title>FAIR Guide</title></head>'
            "<body><main><h1>Průvodce FAIR daty / FAIR Data Guide</h1>"
            '<p>Průvodce dosud nemá publikovanou verzi.</p><p lang="en">The Guide has no published release yet.</p>'
            '<a href="next/">Vývojový náhled / Development preview</a></main></body></html>'
        ).encode()
    for path in sorted(stage.rglob("*")):
        if path.is_symlink():
            raise AssemblyError("staging contains a filesystem link")
        if not path.is_file() or path.name == build_crate.SITE_MARKER:
            continue
        name = path.relative_to(stage).as_posix()
        if name in build_crate.CRAWLER_FILES:
            # Crawlers read these only at the site root, where they are the release's own; a preview copy would
            # advertise preview documents.
            continue
        data = path.read_bytes()
        if name == "openapi.json":
            description = json.loads(data)
            description["servers"] = [{"url": ".", "description": "This preview's static API"}]
            data = (json.dumps(description, ensure_ascii=False, indent=2) + "\n").encode()
        if path.suffix.lower() == ".html":
            notice = release_notice(name, production_tag or "", staging_commit) if released else NOTICE
            data = preview_html(data, name, notice)
        files["next/" + name] = data
    if "next/assets/css/staging.css" not in files:
        raise AssemblyError("staging notice stylesheet is missing")
    validate_files(files)
    # All parsing, verification and overlap checks precede this single managed replacement.
    output = build_crate.replace_site(output, root)
    for name, data in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return notices


def built_for(site: Path) -> dict[str, str]:
    """The publication root and namespace a checked site was built for, read from its own files."""
    return site_identity({name: (site / name).read_bytes() for name in ("assets/data/ui.js", "ro-crate-metadata.json")})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--staging-commit", required=True)
    parser.add_argument("--production", type=Path)
    parser.add_argument("--production-tag")
    parser.add_argument("--production-commit")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--notes", type=Path, help="write the notices for the run summary as Markdown lines")
    parser.add_argument(
        "--root-out", type=Path, help="write the publication root the staging site was built for, for the last check"
    )
    args = parser.parse_args(argv)
    try:
        # Read before anything is written, so a site without its stamp fails without replacing the output.
        root = built_for(args.staging)["publication_url"] if args.root_out else ""
        notices = assemble(
            args.staging,
            args.staging_commit,
            args.out,
            production=args.production,
            production_tag=args.production_tag,
            production_commit=args.production_commit,
        )
    except (
        AssemblyError,
        build_crate.ContentError,
        package_site.PackageError,
        OSError,
        ValueError,
        tarfile.TarError,
    ) as error:
        print(f"assemble_pages: {error}")
        return 2
    for notice in notices:
        print(f"assemble_pages: {notice}")
    if args.notes:
        args.notes.parent.mkdir(parents=True, exist_ok=True)
        args.notes.write_text("".join(f"- {notice}\n" for notice in notices), encoding="utf-8", newline="\n")
    if args.root_out:
        args.root_out.parent.mkdir(parents=True, exist_ok=True)
        args.root_out.write_text(root + "\n", encoding="utf-8", newline="\n")
    print(f"assemble_pages: release and preview assembled in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
