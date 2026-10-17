"""Prepare an image context from verified release bytes and verify the served identity; never push or rebuild."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import assemble_pages
import build_crate
import build_identity
import package_site

ROOT = Path(__file__).resolve().parents[1]


def prepare(artifact: Path, output: Path, tag: str, commit: str, root: Path = ROOT) -> dict:
    """Validate every input before replacing a managed context; no tar member is extracted by the shell."""
    target = build_crate.site_directory(output, root)
    source = artifact.resolve()
    if target == source or target in source.parents or source in target.parents:
        raise ValueError("image context overlaps the release artifact")
    files = assemble_pages.production_files(artifact, tag, commit)
    assemble_pages.validate_files(files)
    built = build_identity.config_identity(files["assets/data/ui.js"].decode("utf-8"))
    manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    health = json.loads(files[package_site.HEALTH])
    if manifest.get("build") != built or health.get("build") != built:
        raise ValueError("release page, health and manifest build identities disagree")
    if (
        built["channel"] != "release"
        or built["version"] != tag
        or not built["commit"]
        or not commit.startswith(built["commit"])
    ):
        raise ValueError("release build identity does not match the tag and commit")
    crate = json.loads(files[build_crate.CRATE_FILE])
    nodes = {entity["@id"]: entity for entity in crate["@graph"]}
    if any(nodes.get(key, {}).get("creativeWorkStatus") != built["status"] for key in ("./", "#guide-software")):
        raise ValueError("crate status differs from release identity")
    templates = {name: (root / "docker" / name).read_bytes() for name in ("Dockerfile", "nginx.conf")}
    target = build_crate.replace_site(target, root)
    for name, data in files.items():
        path = target / "site" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, data in templates.items():
        (target / name).write_bytes(data)
    (target / "identity.json").write_text(json.dumps(built, indent=2) + "\n", encoding="utf-8")
    return built


def verify(health: dict, built: dict, commit: str, config: str) -> None:
    """A served health/config pair must describe precisely the validated artifact."""
    if (
        health.get("revision") != commit
        or health.get("build") != built
        or build_identity.config_identity(config) != built
    ):
        raise ValueError("served image identity differs from the verified artifact")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("prepare")
    command.add_argument("--artifact", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--tag", required=True)
    command.add_argument("--commit", required=True)
    command = commands.add_parser("verify")
    command.add_argument("--health", type=Path, required=True)
    command.add_argument("--identity", type=Path, required=True)
    command.add_argument("--config", type=Path, required=True)
    command.add_argument("--commit", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.artifact, args.output, args.tag, args.commit)))
    else:
        verify(
            json.loads(args.health.read_text(encoding="utf-8")),
            json.loads(args.identity.read_text(encoding="utf-8")),
            args.commit,
            args.config.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    main()
