"""Public destination, redirect and pinned-TLS boundaries, without contacting any service."""

import io
import os
import socket
import ssl
import sys
import unittest
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import public_https as transport  # noqa: E402
import vendor_favicons as vf  # noqa: E402


def answer(ip="8.8.8.8", port=443):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
    return family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr


class DestinationTests(unittest.TestCase):
    def test_non_public_and_transition_addresses_are_refused_on_all_supported_pythons(self):
        for ip in (
            "0.0.0.0",
            "0.1.2.3",
            "10.0.0.1",
            "100.64.0.1",
            "127.0.0.1",
            "169.254.169.254",
            "172.16.0.1",
            "192.168.1.1",
            "192.0.0.8",
            "192.0.2.1",
            "198.18.0.1",
            "224.0.0.1",
            "240.0.0.1",
            "::",
            "::1",
            "fe80::1",
            "fec0::1",
            "fd00::1",
            "ff02::1",
            "2001:db8::1",
            "::ffff:127.0.0.1",
            "::ffff:10.0.0.1",
            "64:ff9b::a00:1",
            "64:ff9b:1::1",
            "2002:a00:1::",
        ):
            with self.subTest(ip=ip), self.assertRaises(transport.DestinationRefusedError):
                transport.public_address(ip)
        for ip in ("8.8.8.8", "1.1.1.1", "2606:4700:4700::1111", "::ffff:8.8.8.8"):
            self.assertTrue(transport.public_address(ip).is_global)

    def test_invalid_urls_and_literal_private_hosts_are_refused_without_dns(self):
        for url in (
            "http://public.example/",
            "ftp://public.example/",
            "https://user:secret@public.example/",
            "https://localhost/",
            "https://machine.local/",
            "https://intranet/",
            "https://127.0.0.1/",
            "https://[::1]/",
            "https://public.example:0/",
            "https://public.example:99999/",
            "https://public.example:bad/",
            "https://bad\\host.example/",
            "https://public.example/\nheader",
        ):
            with (
                self.subTest(url=url),
                mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS")),
                self.assertRaises(ValueError),
            ):
                transport.validate_url(url)
        self.assertEqual(
            transport.validate_url("HTTPS://PUBLIC.EXAMPLE:8443/icon?q=1#fragment"),
            "https://public.example:8443/icon?q=1",
        )

    def test_mixed_dns_answers_fail_before_connecting(self):
        with (
            mock.patch.object(socket, "getaddrinfo", return_value=[answer(), answer("10.0.0.1")]),
            mock.patch.object(socket, "socket") as connect,
            self.assertRaises(transport.DestinationRefusedError),
        ):
            transport.pinned_connection(("public.example", 443), 10)
        connect.assert_not_called()

    def test_numeric_hostname_alias_is_checked_after_resolution(self):
        with (
            mock.patch.object(socket, "getaddrinfo", return_value=[answer("127.0.0.1")]),
            mock.patch.object(socket, "socket") as connect,
            self.assertRaises(transport.DestinationRefusedError),
        ):
            transport.pinned_connection(("127.1", 443), 7)
        connect.assert_not_called()

    def test_unresolved_and_non_numeric_dns_answers_fail_closed(self):
        for answers in ([], [answer("not-an-address")], [answer(port=8443)]):
            with (
                self.subTest(answers=answers),
                mock.patch.object(socket, "getaddrinfo", return_value=answers),
                self.assertRaises(transport.DestinationRefusedError),
            ):
                transport.resolved_addresses("public.example", 443)


class ConnectionTests(unittest.TestCase):
    def test_dns_is_not_repeated_and_the_connection_uses_the_vetted_sockaddr(self):
        for ip in ("8.8.8.8", "2606:4700:4700::1111"):
            info = answer(ip)
            sock = mock.Mock()
            sock.getpeername.return_value = info[4]
            with (
                mock.patch.object(socket, "getaddrinfo", side_effect=[[info], [answer("127.0.0.1")]]) as dns,
                mock.patch.object(socket, "socket", return_value=sock),
            ):
                self.assertIs(transport.pinned_connection(("public.example", 443), 7), sock)
            dns.assert_called_once()
            sock.connect.assert_called_once_with(info[4])
            sock.settimeout.assert_called_once_with(7)

    def test_unexpected_peer_is_closed_before_tls_or_http(self):
        for peer in (("127.0.0.1", 443), ("1.1.1.1", 443), ("8.8.8.8", 8443)):
            sock = mock.Mock()
            sock.getpeername.return_value = peer
            with (
                self.subTest(peer=peer),
                mock.patch.object(socket, "getaddrinfo", return_value=[answer()]),
                mock.patch.object(socket, "socket", return_value=sock),
                self.assertRaises(transport.DestinationRefusedError),
            ):
                transport.pinned_connection(("public.example", 443), 7)
            sock.close.assert_called_once()

    def test_tls_keeps_the_hostname_and_requires_certificate_validation(self):
        context = mock.Mock(check_hostname=True, verify_mode=ssl.CERT_REQUIRED)
        sock = mock.Mock()
        with mock.patch.object(transport, "pinned_connection", return_value=sock):
            connection = transport.PublicHTTPSConnection("public.example", context=context, timeout=7)
            connection.connect()
        context.wrap_socket.assert_called_once_with(sock, server_hostname="public.example")
        actual = transport.PublicHTTPSConnection("public.example")
        self.assertTrue(actual._context.check_hostname)
        self.assertEqual(actual._context.verify_mode, ssl.CERT_REQUIRED)
        for check_hostname, verify_mode in ((False, ssl.CERT_REQUIRED), (True, ssl.CERT_NONE)):
            with self.assertRaises(transport.DestinationRefusedError):
                transport.PublicHTTPSConnection(
                    "public.example", context=mock.Mock(check_hostname=check_hostname, verify_mode=verify_mode)
                )

    def test_failed_public_address_can_fall_back_without_another_dns_lookup(self):
        first, second = mock.Mock(), mock.Mock()
        first.connect.side_effect = TimeoutError("first address unavailable")
        second.getpeername.return_value = ("1.1.1.1", 443)
        with (
            mock.patch.object(socket, "getaddrinfo", return_value=[answer(), answer("1.1.1.1")]) as dns,
            mock.patch.object(socket, "socket", side_effect=[first, second]),
        ):
            self.assertIs(transport.pinned_connection(("public.example", 443), 7), second)
        dns.assert_called_once()
        first.close.assert_called_once()


class FixtureTransport(urllib.request.HTTPSHandler, urllib.request.HTTPHandler):
    def __init__(self, responses):
        super().__init__()
        self.responses = responses
        self.requests = []
        self.returned = []

    def https_open(self, request):
        self.requests.append(request.full_url)
        if request.host not in ("start.example", "cdn.example") or request._tunnel_host:
            raise AssertionError("unexpected host or environment proxy")
        location, body = self.responses[request.full_url]
        headers = Message()
        if location:
            headers["Location"] = location
        response = urllib.response.addinfourl(io.BytesIO(body), headers, request.full_url, 302 if location else 200)
        response.msg = "Found" if location else "OK"
        self.returned.append(response)
        return response

    def http_open(self, request):
        raise AssertionError("an HTTP redirect must be refused before requesting it")


class RedirectTests(unittest.TestCase):
    def test_https_downgrade_is_refused_before_the_intermediate_request(self):
        fixture = FixtureTransport({"https://start.example/": ("http://cdn.example/", b"")})
        with (
            mock.patch.object(transport, "PublicHTTPSHandler", return_value=fixture),
            self.assertRaisesRegex(ValueError, "HTTPS"),
        ):
            vf.network_fetch("https://start.example/", 8)
        self.assertEqual(fixture.requests, ["https://start.example/"])
        self.assertTrue(all(response.closed for response in fixture.returned))

    def test_private_redirect_literal_is_refused_without_requesting_it(self):
        fixture = FixtureTransport({"https://start.example/": ("https://127.0.0.1/icon", b"")})
        with (
            mock.patch.object(transport, "PublicHTTPSHandler", return_value=fixture),
            self.assertRaises(transport.DestinationRefusedError),
        ):
            vf.network_fetch("https://start.example/", 8)
        self.assertEqual(fixture.requests, ["https://start.example/"])
        self.assertTrue(all(response.closed for response in fixture.returned))

    def test_public_https_cdn_redirect_and_read_limit_work_without_ambient_proxy(self):
        fixture = FixtureTransport(
            {
                "https://start.example/": ("https://cdn.example/icon", b""),
                "https://cdn.example/icon": (None, b"abcdefgh"),
            }
        )
        with (
            mock.patch.dict(
                os.environ, {"HTTPS_PROXY": "http://127.0.0.1:8080", "https_proxy": "http://127.0.0.1:8080"}
            ),
            mock.patch.object(transport, "PublicHTTPSHandler", return_value=fixture),
        ):
            final, body = vf.network_fetch("https://start.example/", 3)
        self.assertEqual((final, body), ("https://cdn.example/icon", b"abcd"))
        self.assertEqual(fixture.requests, ["https://start.example/", "https://cdn.example/icon"])

    def test_real_redirect_pipeline_checks_the_next_hosts_dns_before_another_request(self):
        sock = mock.Mock()
        sock.getpeername.return_value = ("8.8.8.8", 443)
        sock.makefile.return_value = io.BytesIO(
            b"HTTP/1.1 302 Found\r\nLocation: https://private.example/icon\r\n"
            b"Content-Length: 0\r\nConnection: close\r\n\r\n"
        )
        context = mock.Mock(check_hostname=True, verify_mode=ssl.CERT_REQUIRED)
        context.wrap_socket.return_value = sock
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            transport.PublicHTTPSHandler(context=context),
            transport.HTTPSRedirectHandler(),
        )

        def resolve(host, port, **kwargs):
            return [answer("8.8.8.8" if host == "start.example" else "10.0.0.1", port)]

        with (
            mock.patch.object(socket, "getaddrinfo", side_effect=resolve) as dns,
            mock.patch.object(socket, "socket", return_value=sock) as connect,
            mock.patch.object(transport, "opener", return_value=opener),
            self.assertRaises(transport.DestinationRefusedError),
        ):
            vf.network_fetch("https://start.example/", 100)
        self.assertEqual([call.args[0] for call in dns.call_args_list], ["start.example", "private.example"])
        connect.assert_called_once()
        sock.sendall.assert_called_once()
        context.wrap_socket.assert_called_once_with(sock, server_hostname="start.example")

    def test_destination_refusal_is_a_failed_observation(self):
        self.assertEqual(vf.failure_reason(transport.DestinationRefusedError("blocked")), "destination-refused")


if __name__ == "__main__":
    unittest.main()
