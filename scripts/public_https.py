"""Direct HTTPS for favicon acquisition, pinned to validated public destinations.

No environment proxy can delegate DNS or bypass the destination policy. Other Guide connectors and refresh
clients do not use this maintenance-only transport. Python 3.11 and the standard library are sufficient.
"""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
import urllib.parse
import urllib.request
from typing import Any


class DestinationRefusedError(ValueError):
    """A URL or resolved/connected address is outside the public HTTPS policy."""


# Refuse translation/tunnel ranges as well as the standard flags, including on the Python 3.11 floor.
TRANSITION = tuple(
    ipaddress.ip_network(value) for value in ("64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32")
)
SPECIAL_V4 = (ipaddress.ip_network("192.0.0.0/24"), ipaddress.ip_network("192.88.99.0/24"))


def public_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as error:
        raise DestinationRefusedError("destination is not a numeric public address") from error
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    flags = (
        "is_private",
        "is_loopback",
        "is_link_local",
        "is_multicast",
        "is_reserved",
        "is_unspecified",
        "is_site_local",
    )
    special = TRANSITION if address.version == 6 else SPECIAL_V4
    if (
        not address.is_global
        or any(getattr(address, flag, False) for flag in flags)
        or any(address in net for net in special)
    ):
        raise DestinationRefusedError("destination is not public unicast")
    return address


def canonical_host(value: str) -> str:
    if not value or any(character in value for character in "\\/%@#\r\n\t "):
        raise DestinationRefusedError("invalid HTTPS destination host")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        try:
            host = value.encode("idna").decode("ascii").lower().removesuffix(".")
        except UnicodeError as error:
            raise DestinationRefusedError("invalid HTTPS destination host") from error
        labels = host.split(".")
        if (
            len(host) > 253
            or len(labels) < 2
            or host.endswith((".localhost", ".local"))
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
        ):
            raise DestinationRefusedError("invalid or local HTTPS destination host") from None
        return host
    public_address(value)
    return value


def validate_url(value: str) -> str:
    """Validate and IDNA-normalise a URL without DNS or disclosure of credentials in diagnostics."""
    if re.search(r"[\x00-\x20\x7f]", value):
        raise DestinationRefusedError("invalid whitespace in HTTPS destination")
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError as error:
        raise DestinationRefusedError("invalid HTTPS destination") from error
    if parts.scheme != "https":
        raise ValueError("redirected away from HTTPS")
    try:
        if parts.username is not None or parts.password is not None or not parts.hostname:
            raise DestinationRefusedError("HTTPS destination must have a host and no credentials")
        host = canonical_host(parts.hostname)
        port = parts.port
        if port is not None and not 1 <= port <= 65535:
            raise DestinationRefusedError("invalid HTTPS destination port")
    except DestinationRefusedError:
        raise
    except ValueError as error:
        raise DestinationRefusedError("invalid HTTPS destination") from error
    netloc = ("[" + host + "]") if ":" in host else host
    if port is not None:
        netloc += ":" + str(port)
    return urllib.parse.urlunsplit(("https", netloc, parts.path, parts.query, ""))


def resolved_addresses(host: str, port: int) -> list[tuple[Any, ...]]:
    host = canonical_host(host)
    answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not answers:
        raise DestinationRefusedError("destination has no public address")
    for family, kind, _protocol, _name, sockaddr in answers:
        if family not in (socket.AF_INET, socket.AF_INET6) or kind != socket.SOCK_STREAM or sockaddr[1] != port:
            raise DestinationRefusedError("invalid destination address")
        public_address(sockaddr[0])
    return answers


def pinned_connection(address: tuple[str, int], timeout: Any, source_address: Any = None) -> socket.socket:
    """Connect a numeric sockaddr from one vetted DNS result; never resolve it a second time."""
    host, port = address
    answers = resolved_addresses(host, port)
    last_error = None
    for family, kind, protocol, _name, sockaddr in answers:
        connection = socket.socket(family, kind, protocol)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                connection.settimeout(timeout)
            if source_address:
                connection.bind(source_address)
            connection.connect(sockaddr)
            peer = connection.getpeername()
            if public_address(peer[0]) != public_address(sockaddr[0]) or peer[1] != sockaddr[1]:
                raise DestinationRefusedError("connected peer differs from the validated destination")
            return connection
        except OSError as error:
            last_error = error
            connection.close()
        except BaseException:
            connection.close()
            raise
    raise last_error or OSError("no destination address could be reached")


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int | None = None, **kwargs: Any):
        if kwargs.pop("check_hostname", None) is False:
            raise DestinationRefusedError("HTTPS hostname verification is required")
        context = kwargs.pop("context", None) or ssl.create_default_context()
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise DestinationRefusedError("HTTPS certificate and hostname verification are required")
        context.set_alpn_protocols(["http/1.1"])
        super().__init__(host, port=port, context=context, **kwargs)
        # HTTPSConnection retains TLS/SNI handling; only its TCP connection factory is replaced.
        self._create_connection = pinned_connection

    def connect(self) -> None:
        if self._tunnel_host:
            raise DestinationRefusedError("proxy tunnels are not used for favicon acquisition")
        super().connect()


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request: urllib.request.Request):
        return self.do_open(PublicHTTPSConnection, request, context=self._context)


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # noqa: PLR0917 - stdlib handler signature
        try:
            target = validate_url(newurl)
        except ValueError:
            if fp is not None:
                fp.close()
            raise
        return super().redirect_request(request, fp, code, msg, headers, target)


def opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicHTTPSHandler(), HTTPSRedirectHandler())


def fetch(url: str, limit: int, *, timeout: int, headers: dict[str, str]) -> tuple[str, bytes]:
    request = urllib.request.Request(validate_url(url), headers=headers)
    with opener().open(request, timeout=timeout) as response:
        return validate_url(response.geturl()), response.read(limit + 1)
