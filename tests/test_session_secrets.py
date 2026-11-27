"""Session-only, write-only key entry, sealed with the user's own key (1 key = 1 user).

Values are encrypted at rest with AES-256-GCM under a key that identifies one user, never sent back out, and the
session file is private. The control-plane token is the development-mode key; a multi-user deployment injects a key
provider that returns each authenticated user's own key.
"""

from __future__ import annotations

import os
import stat

import pytest

from orama_system.session_secrets import (
    ControlPlaneKeyProvider,
    SessionSecrets,
    SessionSecretsError,
    StaticKeyProvider,
)

SECRET = "sk-test-value-0123456789"
KEY_A = bytes(range(32))
KEY_B = bytes(range(1, 33))


def _store(tmp_path, sid="abc123def456", user="user-a", key=KEY_A):
    return SessionSecrets(tmp_path / "state", StaticKeyProvider(user, key), session_id=sid)


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


# ---------------------------------------------------------------- at rest


def test_the_session_file_is_private_and_the_folders_too(tmp_path):
    store = _store(tmp_path)
    store.set("WANDB_API_KEY", SECRET)
    assert _mode(store.path) == 0o600
    assert _mode(store.path.parent) == 0o700


def test_the_value_is_not_readable_in_the_file_on_disk(tmp_path):
    store = _store(tmp_path)
    store.set("WANDB_API_KEY", SECRET)
    raw = store.path.read_bytes()
    assert SECRET.encode() not in raw
    assert b"WANDB_API_KEY" not in raw, "even the names are sealed"


def test_the_same_value_gives_different_bytes_each_time(tmp_path):
    a, b = _store(tmp_path, "aaaaaa111111"), _store(tmp_path, "bbbbbb222222")
    a.set("TOKEN_X", SECRET)
    b.set("TOKEN_X", SECRET)
    assert a.path.read_bytes() != b.path.read_bytes()


def test_each_user_gets_their_own_folder_named_without_the_user_id(tmp_path):
    a, b = _store(tmp_path, user="alice"), _store(tmp_path, user="bob", key=KEY_B)
    a.set("TOKEN_X", "v")
    b.set("TOKEN_X", "v")
    assert a.path.parent != b.path.parent
    assert "alice" not in str(a.path) and "bob" not in str(b.path)


# ---------------------------------------------------------------- 1 key = 1 user


def test_another_users_key_cannot_open_the_file(tmp_path):
    _store(tmp_path).set("TOKEN_X", SECRET)
    stranger = _store(tmp_path, user="user-a", key=KEY_B)
    with pytest.raises(SessionSecretsError) as err:
        stranger.environment()
    assert SECRET not in str(err.value)


def test_a_file_copied_to_another_users_folder_does_not_open_for_them(tmp_path):
    a = _store(tmp_path, user="alice")
    a.set("TOKEN_X", SECRET)
    b = _store(tmp_path, user="bob", key=KEY_A)  # even with the SAME key bytes, the user id is bound in
    b.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    b.path.write_bytes(a.path.read_bytes())
    with pytest.raises(SessionSecretsError):
        b.environment()


def test_a_file_copied_to_another_session_name_does_not_open(tmp_path):
    a = _store(tmp_path, "aaaaaa111111")
    a.set("TOKEN_X", SECRET)
    b = _store(tmp_path, "bbbbbb222222")
    b.path.write_bytes(a.path.read_bytes())
    with pytest.raises(SessionSecretsError):
        b.environment()


def test_a_tampered_file_is_refused(tmp_path):
    store = _store(tmp_path)
    store.set("TOKEN_X", SECRET)
    data = bytearray(store.path.read_bytes())
    data[-1] ^= 1
    store.path.write_bytes(bytes(data))
    with pytest.raises(SessionSecretsError):
        store.environment()


def test_a_truncated_or_foreign_file_is_refused(tmp_path):
    store = _store(tmp_path)
    store.set("TOKEN_X", SECRET)
    for junk in (b"", b"OSS1", b"not a session file at all, plain text"):
        store.path.write_bytes(junk)
        with pytest.raises(SessionSecretsError):
            store.environment()


def test_a_key_that_is_not_32_bytes_is_refused():
    with pytest.raises(SessionSecretsError):
        StaticKeyProvider("user-a", b"short").key()


# ---------------------------------------------------------------- the development key: the control plane


def test_the_control_plane_provider_derives_a_stable_32_byte_key_per_user():
    p1 = ControlPlaneKeyProvider(lambda: "token-one", "alice")
    assert len(p1.key()) == 32 and p1.key() == p1.key()
    assert p1.key() != ControlPlaneKeyProvider(lambda: "token-one", "bob").key()
    assert p1.key() != ControlPlaneKeyProvider(lambda: "token-two", "alice").key()


def test_the_control_plane_provider_never_returns_the_token_itself():
    assert b"token-one" not in ControlPlaneKeyProvider(lambda: "token-one", "alice").key()


def test_without_a_control_plane_token_it_refuses_instead_of_sealing_with_nothing():
    with pytest.raises(SessionSecretsError):
        ControlPlaneKeyProvider(lambda: "", "alice").key()


def test_rotating_the_control_plane_token_makes_old_session_files_unreadable_not_wrong(tmp_path):
    old = SessionSecrets(tmp_path / "s", ControlPlaneKeyProvider(lambda: "token-one", "alice"), session_id="abc123def456")
    old.set("TOKEN_X", SECRET)
    new = SessionSecrets(tmp_path / "s", ControlPlaneKeyProvider(lambda: "token-two", "alice"), session_id="abc123def456")
    with pytest.raises(SessionSecretsError):
        new.environment()


# ---------------------------------------------------------------- write-only behaviour


def test_names_are_listed_but_values_never_are(tmp_path):
    store = _store(tmp_path)
    store.set("WANDB_API_KEY", SECRET)
    store.set("OPENROUTER_API_KEY", "other-value")
    assert store.names() == ["OPENROUTER_API_KEY", "WANDB_API_KEY"]
    assert SECRET not in repr(store) and SECRET not in str(store.status())
    assert store.status() == {"OPENROUTER_API_KEY": "set", "WANDB_API_KEY": "set"}


@pytest.mark.parametrize("name", ["lower", "1ABC", "A", "HAS SPACE", "A-B", "X" * 70, "", "A=B"])
def test_bad_names_are_refused(tmp_path, name):
    with pytest.raises(SessionSecretsError):
        _store(tmp_path).set(name, "v")


@pytest.mark.parametrize("value", ["", "line1\nline2", "nul\x00byte", "x" * 9000, "cr\rvalue"])
def test_bad_values_are_refused_without_echoing_them(tmp_path, value):
    with pytest.raises(SessionSecretsError) as err:
        _store(tmp_path).set("WANDB_API_KEY", value)
    assert value[:8] not in str(err.value) or value == ""


def test_a_value_with_quotes_and_unicode_survives_a_round_trip(tmp_path):
    store = _store(tmp_path)
    store.set("TOKEN_X", "it's \"quoted\" $HOME `x` \u00e9\u20ac")
    assert store.environment()["TOKEN_X"] == "it's \"quoted\" $HOME `x` \u00e9\u20ac"


def test_setting_again_replaces_the_value(tmp_path):
    store = _store(tmp_path)
    store.set("TOKEN_X", "one")
    store.set("TOKEN_X", "two")
    assert store.environment() == {"TOKEN_X": "two"}


def test_purge_removes_the_file_and_forgets_everything(tmp_path):
    store = _store(tmp_path)
    store.set("TOKEN_X", "one")
    store.purge()
    assert not store.path.exists()
    assert store.names() == []


def test_a_bad_session_id_is_refused_so_it_cannot_escape_the_folder(tmp_path):
    for sid in ("../x", "a/b", "", "x" * 40, "has space"):
        with pytest.raises(SessionSecretsError):
            SessionSecrets(tmp_path / "state", StaticKeyProvider("u", KEY_A), session_id=sid)


def test_a_generated_session_id_is_random_and_safe(tmp_path):
    a = SessionSecrets(tmp_path / "state", StaticKeyProvider("u", KEY_A))
    b = SessionSecrets(tmp_path / "state", StaticKeyProvider("u", KEY_A))
    assert a.session_id != b.session_id and a.session_id.isalnum()


# ---------------------------------------------------------------- save to .env (explicit export, plain text by nature)


def test_save_goes_to_env_when_env_is_missing_and_follows_the_example(tmp_path):
    example = tmp_path / ".env.example"
    example.write_text("# keys\nWANDB_API_KEY=\nOPENROUTER_API_KEY=\n", encoding="utf-8")
    env = tmp_path / ".env"
    store = _store(tmp_path)
    store.set("WANDB_API_KEY", SECRET)
    path, kind = store.save(env, example)
    assert (path, kind) == (env, "env") and _mode(env) == 0o600
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# keys"
    assert "WANDB_API_KEY='%s'" % SECRET in lines and "OPENROUTER_API_KEY=" in lines


def test_save_goes_to_env_when_env_has_only_blank_values(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# empty\nWANDB_API_KEY=\n\n", encoding="utf-8")
    store = _store(tmp_path)
    store.set("WANDB_API_KEY", SECRET)
    assert store.save(env, None)[1] == "env"


def test_save_goes_to_a_session_env_when_env_is_already_populated_and_never_touches_it(tmp_path):
    env = tmp_path / ".env"
    env.write_text("WANDB_API_KEY=existing-secret\n", encoding="utf-8")
    store = _store(tmp_path, "sess1234abcd")
    store.set("WANDB_API_KEY", SECRET)
    path, kind = store.save(env, None)
    assert kind == "session-env" and path == tmp_path / ".env.sess1234abcd" and _mode(path) == 0o600
    assert env.read_text(encoding="utf-8") == "WANDB_API_KEY=existing-secret\n"


def test_save_never_overwrites_an_existing_target(tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\n", encoding="utf-8")
    (tmp_path / ".env.sess1234abcd").write_text("keep\n", encoding="utf-8")
    store = _store(tmp_path, "sess1234abcd")
    store.set("TOKEN_X", "v")
    with pytest.raises(SessionSecretsError):
        store.save(env, None)
    assert (tmp_path / ".env.sess1234abcd").read_text(encoding="utf-8") == "keep\n"


def test_save_refuses_when_nothing_was_entered(tmp_path):
    with pytest.raises(SessionSecretsError):
        _store(tmp_path).save(tmp_path / ".env", None)


# ---------------------------------------------------------------- which key a deployment may use


def test_a_new_install_has_no_default_key_and_is_told_what_to_do():
    from orama_system.session_secrets import key_provider_from_environment

    with pytest.raises(SessionSecretsError) as err:
        key_provider_from_environment({}, lambda: "token-one")
    assert "ORAMA_SESSION_KEY_MODE" in str(err.value) and "token-one" not in str(err.value)


def test_a_grandfathered_development_install_opts_in_explicitly_and_is_flagged_shared():
    from orama_system.session_secrets import key_provider_from_environment

    provider = key_provider_from_environment({"ORAMA_SESSION_KEY_MODE": "dev-control-plane"}, lambda: "token-one")
    assert isinstance(provider, ControlPlaneKeyProvider)
    assert provider.shared_stack_key is True


def test_an_unknown_mode_is_refused_rather_than_guessed():
    from orama_system.session_secrets import key_provider_from_environment

    with pytest.raises(SessionSecretsError):
        key_provider_from_environment({"ORAMA_SESSION_KEY_MODE": "per-user"}, lambda: "token-one")


# ---------------------------------------------------------------- fail closed on what counts as an empty .env (security review)


@pytest.mark.parametrize(
    "content",
    [
        "WANDB_API_KEY = real-secret\n",
        "WANDB_API_KEY =real-secret\n",
        "WANDB_API_KEY: real-secret\n",
        "export WANDB_API_KEY = 'real-secret'\n",
        '"WANDB_API_KEY"=real-secret\n',
        "WANDB_API_KEY\n",
        "some unparsed line the consumers might read\n",
    ],
)
def test_an_env_with_any_non_blank_non_comment_content_is_never_replaced(tmp_path, content):
    env = tmp_path / ".env"
    env.write_text(content, encoding="utf-8")
    store = _store(tmp_path, "sess1234abcd")
    store.set("WANDB_API_KEY", SECRET)
    path, kind = store.save(env, None)
    assert kind == "session-env" and path != env
    assert env.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("content", ["", "\n\n", "# only a comment\n", "WANDB_API_KEY=\nOTHER=''\nTHIRD=\"\"\n", "export A=\n"])
def test_an_env_that_is_strictly_empty_may_be_filled(tmp_path, content):
    env = tmp_path / ".env"
    env.write_text(content, encoding="utf-8")
    store = _store(tmp_path)
    store.set("WANDB_API_KEY", SECRET)
    assert store.save(env, None) == (env, "env")
