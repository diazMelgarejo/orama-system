"""Session-only, write-only key entry for the portal, sealed with the user's own key (operator ruling D5, 2026-11-27).

Keys typed into the portal never go back to the page, the logs or a repository:

* the session file is AES-256-GCM sealed under a key that identifies ONE user (1 key = 1 user), inside a mode-700
  folder that is named by a hash of the user id, and the file itself is mode 600;
* the user id and the session id are bound into the seal, so a file copied to another user or another session name
  does not open, and a changed byte is refused;
* the page can learn only which names are set (``status``), never a value;
* ``save`` is the one deliberate plain-text export: ``.env`` only when it is missing or has no filled value, following
  ``.env.example``; if ``.env`` is already populated the only target is ``.env.<session-id>``; an existing file is
  never overwritten;
* ``purge`` removes the session file.

Key source. Development mode uses the control-plane token (``ControlPlaneKeyProvider``): the key is derived from the
token and the user id with HKDF-SHA256, never the token itself, and a missing token refuses instead of sealing with
nothing. A multi-user deployment injects its own ``KeyProvider`` that returns each authenticated user's key.
Rotating the token makes older session files unreadable (a clean refusal, never a wrong answer): they are
session-only by design.

Values are never put in an exception message, ``repr`` or log line. A same-user local process can still read an
exported ``.env``, as it can today.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from typing import Callable, Mapping, Protocol

NAME_RE = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
SESSION_ID_RE = re.compile(r"[A-Za-z0-9]{6,32}")
MAX_VALUE_LENGTH = 8192
KEY_LENGTH = 32
MAGIC = b"OSS1"
NONCE_LENGTH = 12
_KDF_INFO = b"orama-session-secrets-v1"
_FORBIDDEN_VALUE_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_ASSIGNMENT = re.compile(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)")


class SessionSecretsError(ValueError):
    """A name, value, session id, key or file was refused. The message never contains a secret value."""


class KeyProvider(Protocol):
    """One user, one key. ``key()`` returns exactly 32 bytes that identify that user."""

    user_id: str

    def key(self) -> bytes: ...


class StaticKeyProvider:
    """A fixed key for one user (tests, or a deployment that already holds the user's key)."""

    def __init__(self, user_id: str, key: bytes) -> None:
        self.user_id = user_id
        self._key = key

    def key(self) -> bytes:
        if not isinstance(self._key, (bytes, bytearray)) or len(self._key) != KEY_LENGTH:
            raise SessionSecretsError("the user key must be exactly 32 bytes")
        return bytes(self._key)

    def __repr__(self) -> str:
        return "StaticKeyProvider(user_id=%r)" % self.user_id


class ControlPlaneKeyProvider:
    """Development-mode key: derived from the control-plane token and the user id (HKDF-SHA256)."""

    #: The token is shared by the whole local stack: this key identifies the stack, not one person, and any local
    #: process that can read the token can open the files. The page should say "private", not "secret".
    shared_stack_key = True

    def __init__(self, token_source: Callable[[], str], user_id: str = "local-operator") -> None:
        self._token_source = token_source
        self.user_id = user_id

    def key(self) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        token = self._token_source()
        if not token:
            raise SessionSecretsError("no control-plane token: refusing to seal session keys with nothing")
        salt = hashlib.sha256(self.user_id.encode("utf-8")).digest()
        return HKDF(algorithm=hashes.SHA256(), length=KEY_LENGTH, salt=salt, info=_KDF_INFO).derive(token.encode("utf-8"))

    def __repr__(self) -> str:
        return "ControlPlaneKeyProvider(user_id=%r)" % self.user_id


DEV_MODE = "dev-control-plane"


def key_provider_from_environment(env: Mapping[str, str], token_source: Callable[[], str]) -> KeyProvider:
    """Choose the key source for this installation; there is no silent default.

    A new installation has no key until a per-user provider is configured (for example one bound to the signed-in
    person's WebAuthn credential) and injected by the deployment. A grandfathered development installation opts in
    to the shared control-plane key explicitly with ``ORAMA_SESSION_KEY_MODE=dev-control-plane``.
    """
    mode = (env.get("ORAMA_SESSION_KEY_MODE") or "").strip()
    if mode == DEV_MODE:
        return ControlPlaneKeyProvider(token_source)
    if not mode:
        raise SessionSecretsError(
            "no session key source configured: inject a per-user key provider, or on a grandfathered development "
            "install set ORAMA_SESSION_KEY_MODE=%s" % DEV_MODE
        )
    raise SessionSecretsError("unknown ORAMA_SESSION_KEY_MODE; the only built-in mode is %s" % DEV_MODE)


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _unquote(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
        return raw[1:-1].replace("'\\''", "'")
    return raw


def _write_private(path: Path, data: bytes, *, exclusive: bool) -> None:
    """Write ``data`` with mode 600. ``exclusive`` refuses to replace an existing file; otherwise replace atomically."""
    if exclusive:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise SessionSecretsError("refusing to overwrite an existing file: %s" % path.name) from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(path, 0o600)
        return
    tmp = path.with_name(path.name + ".tmp-%d" % os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _has_filled_value(text: str) -> bool:
    for line in text.splitlines():
        match = _ASSIGNMENT.match(line)
        if match and not line.lstrip().startswith("#") and _unquote(match.group(2)):
            return True
    return False


class SessionSecrets:
    """Write-only, sealed key store for one user's portal session."""

    def __init__(self, state_dir: Path, key_provider: KeyProvider, session_id: str | None = None) -> None:
        sid = session_id if session_id is not None else secrets.token_hex(6)
        if not SESSION_ID_RE.fullmatch(sid):
            raise SessionSecretsError("the session id must be 6 to 32 letters or digits")
        self.session_id = sid
        self._keys = key_provider
        user_folder = hashlib.sha256(key_provider.user_id.encode("utf-8")).hexdigest()[:16]
        self._dir = Path(state_dir) / user_folder
        self.path = self._dir / ("session-%s.enc" % sid)

    def __repr__(self) -> str:
        return "SessionSecrets(session_id=%r, user=%r)" % (self.session_id, self._keys.user_id)

    def _aad(self) -> bytes:
        return b"v1|" + self._keys.user_id.encode("utf-8") + b"|" + self.session_id.encode("ascii")

    def _seal(self, values: dict[str, str]) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(NONCE_LENGTH)
        payload = json.dumps(values, sort_keys=True).encode("utf-8")
        return MAGIC + nonce + AESGCM(self._keys.key()).encrypt(nonce, payload, self._aad())

    def _open(self, blob: bytes) -> dict[str, str]:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if len(blob) < len(MAGIC) + NONCE_LENGTH + 16 or not blob.startswith(MAGIC):
            raise SessionSecretsError("not a session secrets file")
        nonce = blob[len(MAGIC) : len(MAGIC) + NONCE_LENGTH]
        try:
            payload = AESGCM(self._keys.key()).decrypt(nonce, blob[len(MAGIC) + NONCE_LENGTH :], self._aad())
            data = json.loads(payload.decode("utf-8"))
        except (InvalidTag, ValueError) as exc:
            raise SessionSecretsError("cannot open the session file: wrong user key, other session, or changed file") from exc
        if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
            raise SessionSecretsError("the session file has an unexpected shape")
        return data

    def environment(self) -> dict[str, str]:
        """The stored name-to-value map, for the launcher process only; never send this to the page."""
        if not self.path.is_file():
            return {}
        return self._open(self.path.read_bytes())

    def names(self) -> list[str]:
        return sorted(self.environment())

    def status(self) -> dict[str, str]:
        return {name: "set" for name in self.names()}

    def set(self, name: str, value: str) -> None:
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise SessionSecretsError("the name must be 2 to 64 characters: capital letters, digits, underscore")
        if not isinstance(value, str) or not value or len(value) > MAX_VALUE_LENGTH or _FORBIDDEN_VALUE_CHARS.search(value):
            raise SessionSecretsError("the value is empty, too long or contains a control character")
        current = self.environment()
        current[name] = value
        self._dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._dir, 0o700)
        _write_private(self.path, self._seal(current), exclusive=False)

    def purge(self) -> None:
        self.path.unlink(missing_ok=True)

    def save(self, env_path: Path, example_path: Path | None) -> tuple[Path, str]:
        """Save to ``.env`` if it is missing or has no filled value, else to ``.env.<session-id>``.

        Returns ``(path, "env" | "session-env")``. This is the one plain-text export, and only on the operator's
        explicit request. The new file follows ``.env.example`` (its comments and keys, filled where this session has
        a value), then appends any other session names. An existing target is never overwritten.
        """
        env_path = Path(env_path)
        values = self.environment()
        if not values:
            raise SessionSecretsError("nothing to save: no key was entered in this session")
        populated = env_path.is_file() and _has_filled_value(env_path.read_text(encoding="utf-8"))
        if populated or (env_path.exists() and not env_path.is_file()):
            target, kind = env_path.with_name("%s.%s" % (env_path.name, self.session_id)), "session-env"
        else:
            target, kind = env_path, "env"
        lines: list[str] = []
        used: set[str] = set()
        template = Path(example_path) if example_path else None
        if template is not None and template.is_file():
            for line in template.read_text(encoding="utf-8").splitlines():
                match = _ASSIGNMENT.match(line)
                if match and not line.lstrip().startswith("#"):
                    key = match.group(1)
                    used.add(key)
                    lines.append("%s=%s" % (key, _quote(values[key])) if key in values else "%s=" % key)
                else:
                    lines.append(line)
        lines.extend("%s=%s" % (key, _quote(val)) for key, val in sorted(values.items()) if key not in used)
        # A .env with no filled value may be replaced; a session-env target must be new.
        _write_private(target, ("\n".join(lines) + "\n").encode("utf-8"), exclusive=kind == "session-env")
        return target, kind
