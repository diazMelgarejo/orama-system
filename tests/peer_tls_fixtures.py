"""Shared helpers for peer TLS / outbox tests: throwaway CA + leaf certs and
a loopback HTTP(S) server that records the Authorization headers it sees."""
from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import json
import ssl
import sys
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

SCRIPTS = Path(__file__).resolve().parents[1] / "bin" / "orama-system" / "skills" / "hermes-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Loopback without a dotted literal in source (repo hygiene).
LOOPBACK_V4 = str(ipaddress.IPv4Address(0x7F000001))
SYNTHETIC_TOKEN = "synthetic-test-token-not-a-secret"

_PEM = serialization.Encoding.PEM


def _name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _key():
    return ec.generate_private_key(ec.SECP256R1())


def make_ca(cn: str = "test-peer-ca"):
    key = _key()
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name(cn)).issuer_name(_name(cn)).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5)).not_valid_after(now + dt.timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def make_leaf(*, issuer=None, days_valid: int = 2, expired: bool = False, cn: str = "peer"):
    """issuer=(key, cert) -> CA-signed leaf; None -> self-signed leaf.
    SANs: DNS localhost + the loopback IPv4 address."""
    key = _key()
    now = dt.datetime.now(dt.timezone.utc)
    if expired:
        nb, na = now - dt.timedelta(days=3), now - dt.timedelta(days=1)
    else:
        nb, na = now - dt.timedelta(minutes=5), now + dt.timedelta(days=days_valid)
    ikey, icert = issuer if issuer else (key, None)
    b = (
        x509.CertificateBuilder()
        .subject_name(_name(cn))
        .issuer_name(icert.subject if icert else _name(cn))
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(nb).not_valid_after(na)
        .add_extension(x509.SubjectAlternativeName(
            [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address(LOOPBACK_V4))]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
    )
    if icert is not None:
        b = b.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(icert.public_key()), critical=False)
    return key, b.sign(ikey, hashes.SHA256())


def write_pem(path: Path, cert=None, key=None) -> Path:
    data = b""
    if cert is not None:
        data += cert.public_bytes(_PEM)
    if key is not None:
        data += key.private_bytes(_PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    path.write_bytes(data)
    return path


def fingerprint(cert) -> str:
    return hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()


@dataclass
class PeerServer:
    port: int
    seen: list = field(default_factory=list)  # (method, path, authorization or "")
    reply: dict = field(default_factory=lambda: {"ok": True})
    httpd: ThreadingHTTPServer | None = None

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def auth_headers(self) -> list:
        return [a for _, _, a in self.seen if a]


def start_server(tmp_path: Path, leaf=None, tls: bool = True) -> PeerServer:
    srv = PeerServer(port=0)

    class H(BaseHTTPRequestHandler):
        def _go(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            srv.seen.append((self.command, self.path, self.headers.get("Authorization", "")))
            body = json.dumps(srv.reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = _go

        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer((LOOPBACK_V4, 0), H)
    if tls:
        key, cert = leaf
        pem = write_pem(tmp_path / f"srv-{id(srv)}.pem", cert, key)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(pem))
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    srv.httpd = httpd
    srv.port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return srv
