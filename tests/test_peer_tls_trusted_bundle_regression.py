"""Exercise trusted-PEM smuggling against the actual Python/OpenSSL loader."""
from __future__ import annotations

import hashlib
from pathlib import Path
import ssl
import sys

import pytest

pytest.importorskip("cryptography", reason="throwaway certificates require cryptography")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "bin/orama-system/skills/hermes-harness/scripts"))

import peer_tls  # noqa: E402
import peer_tls_fixtures as fx  # noqa: E402


def test_real_openssl_trusted_bundle_cannot_expand_pinned_ca_trust(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An extra CA accepted by OpenSSL must be rejected by the pinned peer loader."""
    approved = fx.make_ca("approved-peer-ca")[1]
    extra = fx.make_ca("unapproved-extra-ca")[1]
    bundle = tmp_path / "bundle.pem"
    bundle.write_bytes(
        approved.public_bytes(fx._PEM) +
        extra.public_bytes(fx._PEM).replace(b"CERTIFICATE", b"TRUSTED CERTIFICATE")
    )
    raw_context = ssl.create_default_context(cafile=str(bundle))
    anchors = {
        hashlib.sha256(der).hexdigest()
        for der in raw_context.get_ca_certs(binary_form=True)
    }
    assert anchors == {fx.fingerprint(approved), fx.fingerprint(extra)}

    monkeypatch.setenv("PEER_CA_SHA256", fx.fingerprint(approved))
    with pytest.raises(peer_tls.PeerTrustError, match="exactly one CERTIFICATE block"):
        peer_tls._ca_context(str(bundle))
