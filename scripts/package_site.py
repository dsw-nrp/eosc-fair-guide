#!/usr/bin/env python3
"""Package the exact site that passed the checks as one commit-labelled release artifact.

    python scripts/package_site.py --commit SHA --output DIR [--site _site]

Refuses a directory the build did not make and a site whose published health report is not a completed, passed
check run, so a release can only carry what the checks verified; nothing is rebuilt. Writes
``eosc-fair-guide-site-<version>-<commit>.tar.gz`` (deterministic: sorted entries, fixed times and owners), its
``.sha256`` and ``manifest.json`` naming the commit, the version, the health run and the archive's digest. The
deployment workflow uploads the same files; the release workflow attaches them without building again.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_crate  # noqa: E402
import build_identity  # noqa: E402
from publication_location import site_identity  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HEALTH = "api/health.json"


class PackageError(Exception):
    """The site cannot be released as it is."""


def verified_health(site: Path) -> dict[str, Any]:
    """The published health report of a site the build made, when it records a completed, passed run."""
    try:
        site = build_crate.require_site(site)
        report = json.loads((site / HEALTH).read_text(encoding="utf-8"))
    except (build_crate.UnsafeOutputError, OSError, ValueError) as error:
        raise PackageError(f"not a verified built site: {error}") from error
    if not report.get("generated_at"):
        raise PackageError("the site carries only the build's inventory; run the checks before packaging")
    if report.get("run", {}).get("status") != "passed":
        raise PackageError(f"the published check run is {report.get('run', {}).get('status')!r}, not passed")
    return report


def archive(site: Path) -> bytes:
    """The site as a reproducible gzip-compressed tar: the same files give the same bytes."""
    buffer = io.BytesIO()
    with (
        gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as tar,
    ):
        for path in sorted(site.rglob("*")):
            if not path.is_file() or path.name == build_crate.SITE_MARKER:
                continue
            info = tarfile.TarInfo(path.relative_to(site).as_posix())
            data = path.read_bytes()
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = (
                len(data),
                0,
                0o644,
                0,
                0,
                "",
                "",
            )
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def package(site: Path, commit: str, output: Path, root: Path = ROOT) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PackageError("the commit must be a full SHA-1")
    report = verified_health(site)
    try:
        config = (Path(site) / "assets/data/ui.js").read_text(encoding="utf-8")
        built = build_identity.config_identity(config)
        publication_url = build_identity.config_publication_url(config)
        inputs = site_identity(
            {name: (site / name).read_bytes() for name in ("assets/data/ui.js", "ro-crate-metadata.json")}
        )
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise PackageError(f"required page identity is unreadable: {error}") from error
    if report.get("build") != built or report.get("revision") != commit:
        raise PackageError("page/health identity or checked commit disagree")
    if built["commit"] and not commit.startswith(built["commit"]):
        raise PackageError("page build commit differs from the checked commit")
    version = tomllib.loads((root / "content" / "guide.toml").read_text(encoding="utf-8"))["guide"]["version"]
    name = f"eosc-fair-guide-site-{version}-{commit[:12]}"
    data = archive(Path(site))
    digest = hashlib.sha256(data).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{name}.tar.gz").write_bytes(data)
    (output / f"{name}.tar.gz.sha256").write_text(f"{digest}  {name}.tar.gz\n", encoding="utf-8")
    manifest = {
        "name": name,
        "version": version,
        "commit": commit,
        "build": built,
        "archive": f"{name}.tar.gz",
        "sha256": digest,
        "health": {
            "generated_at": report["generated_at"],
            "run": report["run"]["status"],
            "revision": report.get("revision"),
        },
    }
    if publication_url:
        manifest["publication_url"] = publication_url
    manifest["semantic"] = {key: inputs[key] for key in ("vocabulary_base", "profile")}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", type=Path, default=build_crate.ROOT / build_crate.DEFAULT_SITE)
    parser.add_argument("--commit", required=True, help="the full SHA of the checked commit")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = package(args.site, args.commit, args.output)
    except PackageError as error:
        print(f"package_site: {error}", file=sys.stderr)
        return 2
    print(f"package_site: {manifest['archive']} ({manifest['sha256']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
