"""Resolve the Guide's own publication input without predicting a hostname or querying the network."""

from __future__ import annotations

import json
import re
from urllib.parse import urlsplit, urlunsplit


def base_url(value: str) -> str:
    """A public HTTPS site directory; a copied index-page URL may include a query or view fragment."""
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        valid = parsed.scheme == "https" and bool(parsed.hostname)
        _ = parsed.port  # Reject malformed or out-of-range ports, without choosing a host or port.
        valid = valid and not (parsed.username or parsed.password or "\\" in raw or any(c.isspace() for c in raw))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("the guide's address must use HTTPS and name its actual public site without credentials")
    path = parsed.path
    if path.endswith("/index.html"):
        path = path.removesuffix("index.html")
    return urlunsplit((parsed.scheme, parsed.netloc, path.rstrip("/") + "/", "", ""))


def config_values(text: str) -> dict:
    """Read generated configuration without executing JavaScript."""
    match = re.search(r"^window\.FairGuideData\.ui = (.*);\r?$", text, re.MULTILINE)
    if not match:
        raise ValueError("the page configuration carries no build identity")
    data = json.loads(match[1])
    config = data.get("config") if isinstance(data, dict) else None
    return config if isinstance(config, dict) else {}


def semantic_identity(crate: dict, config: dict | None = None) -> dict[str, str]:
    """The actual Guide namespace/profile in a crate, including historical unstamped releases."""
    try:
        extension = crate["@context"][1]
        vocabulary = extension["scope"].removesuffix("scope")
        semantic_base = vocabulary.removesuffix("terms#")
        if vocabulary != base_url(semantic_base) + "terms#":
            raise ValueError("invalid Guide vocabulary namespace")
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        conforms = graph["./"]["conformsTo"]
        conforms = conforms if isinstance(conforms, list) else [conforms]
        profiles = [
            item["@id"]
            for item in conforms
            if isinstance(item, dict) and str(item.get("@id", "")).startswith(semantic_base + "profile/")
        ]
        if len(profiles) != 1 or profiles[0] not in graph:
            raise ValueError("crate carries no unambiguous Guide profile")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,2}", profiles[0].removeprefix(semantic_base + "profile/")):
            raise ValueError("invalid Guide profile version address")
        for key, value in extension.items():
            if isinstance(value, str) and "terms#" in value and (value != vocabulary + key or value not in graph):
                raise ValueError("crate has contradictory or undefined Guide terms")
        if config is not None and config.get("vocab", {}).get("guide") != vocabulary:
            raise ValueError("page vocabulary differs from the crate")
        return {"vocabulary_base": vocabulary, "profile": profiles[0]}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("crate carries no complete Guide semantic identity") from error


def site_identity(files: dict[str, bytes]) -> dict[str, str]:
    """Publication and semantic inputs established from real files, without a manifest default."""
    try:
        config = config_values(files["assets/data/ui.js"].decode("utf-8"))
        crate = json.loads(files["ro-crate-metadata.json"])
        return {"publication_url": base_url(config["pageUrl"]), **semantic_identity(crate, config)}
    except KeyError as error:
        raise ValueError("site lacks publication/semantic evidence") from error


def verify_declaration(files: dict[str, bytes], manifest: dict) -> dict[str, str]:
    """Verify new stamps against bytes; legacy archives derive semantic values from the crate."""
    actual = site_identity(files)
    if "semantic" in manifest:
        if not isinstance(manifest["semantic"], dict) or set(manifest["semantic"]) != {"vocabulary_base", "profile"}:
            raise ValueError("invalid release semantic declaration")
        expected = {"publication_url": manifest.get("publication_url"), **manifest["semantic"]}
        if expected != actual:
            raise ValueError("release publication/semantic declaration differs from its contents")
    elif manifest.get("publication_url", actual["publication_url"]) != actual["publication_url"]:
        raise ValueError("release publication location differs from its contents")
    return actual


def preview_blocked(robots: str, paths: list[str]) -> bool:
    """Check our root-hosting policy for a noindex/crawl conflict; longest matching allow wins ties.

    Supports the REP group, prefix, wildcard and end-anchor forms a retained release may carry. The project-subpath
    case does not call this: that file has no authority over the origin's robots policy.
    """
    groups: list[tuple[list[str], list[tuple[str, bool]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, bool]] = []
    for raw in robots.splitlines():
        field, _, value = raw.split("#", 1)[0].partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif field in ("allow", "disallow") and value and agents:
            rules.append((value, field == "allow"))
    if agents:
        groups.append((agents, rules))
    for agent in {agent for agents, _ in groups for agent in agents}:
        applicable = [rules for agents, rules in groups if agent in agents]
        for path in paths:
            matches = []
            for group in applicable:
                for pattern, allow in group:
                    anchored = pattern.endswith("$")
                    literal = pattern[:-1] if anchored else pattern
                    expression = "^" + re.escape(literal).replace(r"\*", ".*") + ("$" if anchored else "")
                    if re.search(expression, path):
                        matches.append((len(pattern.encode("utf-8")), allow))
            if matches and not max(matches)[1]:
                return True
    return False
