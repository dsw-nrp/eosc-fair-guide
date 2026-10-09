#!/usr/bin/env python3
"""Serve the built guide on this computer over HTTP, with its API, as it will be published.

The built page works from a local file (``_site/index.html``), but the API and its documentation need a web server,
because browsers do not let a page fetch local files. This serves the site directory to this computer only:

    python scripts/serve.py [--build] [--port 8000]

``--build`` first builds the site (``build_site.py``; the API documentation needs ``npm ci`` once). Then open
http://127.0.0.1:8000/ for the guide and http://127.0.0.1:8000/api/ for the API documentation. Links that leave the
page, such as an exported result's references, then name this local address. Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import http.server
import sys
from pathlib import Path

import build_site


class Handler(http.server.SimpleHTTPRequestHandler):
    """Files of the built site; nothing is cached, so a rebuild shows at once."""

    extensions_map = http.server.SimpleHTTPRequestHandler.extensions_map | {
        ".js": "text/javascript",
        ".json": "application/json",
        ".jsonld": "application/ld+json",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(build_site.SITE), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", action="store_true", help="build the site first")
    parser.add_argument("--port", type=int, default=8000, help="the local port (default: 8000)")
    args = parser.parse_args(argv)
    if args.build and build_site.main([]):
        return 1
    if not (Path(build_site.SITE) / "index.html").is_file():
        print("serve: the site is not built yet; run with --build", file=sys.stderr)
        return 1
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"The guide: {address}  ·  the API documentation: {address}api/  ·  Ctrl+C stops")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
