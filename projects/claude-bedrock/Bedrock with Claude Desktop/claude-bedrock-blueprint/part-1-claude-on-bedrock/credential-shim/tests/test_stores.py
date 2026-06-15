"""Round-trip tests for the file fallback store and end-to-end shim behavior.

These run on any platform: we force the plaintext file store and point ``$HOME`` at a
temp dir so nothing touches the developer's real ``~/.aws``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from credential_shim import __main__ as shim
from credential_shim.stores import PlaintextFileStore


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # On Windows expanduser uses USERPROFILE; set both so the test is portable.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


def test_file_store_round_trip(home):
    store = PlaintextFileStore()
    assert store.load("p") is None
    store.save("p", '{"hello":"world"}')
    assert json.loads(store.load("p")) == {"hello": "world"}
    store.delete("p")
    assert store.load("p") is None


def test_file_store_is_owner_only(home):
    import os
    import stat

    store = PlaintextFileStore()
    store.save("p", "{}")
    mode = stat.S_IMODE(os.stat(store._path("p")).st_mode)
    # No group/other permission bits.
    assert mode & 0o077 == 0


def _creds(expires_in_minutes: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return json.dumps(
        {
            "Version": 1,
            "AccessKeyId": "AKIAEXAMPLE",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
            "Expiration": exp.isoformat(),
        }
    )


def test_fast_path_serves_fresh_cache_without_calling_binary(home, monkeypatch, capsys):
    store = PlaintextFileStore()
    monkeypatch.setattr(shim, "get_store", lambda: store)
    store.save("default", _creds(60))

    def _boom(*a, **k):  # the real binary must NOT be invoked on a fast-path hit
        raise AssertionError("credential-process should not be called on a cache hit")

    monkeypatch.setattr(shim.subprocess, "run", _boom)

    rc = shim.main([])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["AccessKeyId"] == "AKIAEXAMPLE"


def test_slow_path_calls_binary_and_repopulates(home, monkeypatch, capsys):
    store = PlaintextFileStore()
    monkeypatch.setattr(shim, "get_store", lambda: store)
    monkeypatch.setattr(shim, "credential_process_path", lambda: "/fake/credential-process")
    fresh = _creds(60)

    class _Result:
        returncode = 0
        stdout = fresh + "\n"
        stderr = ""

    monkeypatch.setattr(shim.subprocess, "run", lambda *a, **k: _Result())

    rc = shim.main([])
    assert rc == 0
    # stdout matches the binary's output, and the cache now holds it.
    assert json.loads(capsys.readouterr().out)["SessionToken"] == "token"
    assert store.load("default") is not None


def test_auth_failure_invalidates_cache(home, monkeypatch, capsys):
    store = PlaintextFileStore()
    monkeypatch.setattr(shim, "get_store", lambda: store)
    monkeypatch.setattr(shim, "credential_process_path", lambda: "/fake/credential-process")
    store.save("default", _creds(-5))  # a stale entry that should be cleared

    class _Result:
        returncode = 255
        stdout = ""
        stderr = "auth revoked\n"

    monkeypatch.setattr(shim.subprocess, "run", lambda *a, **k: _Result())

    rc = shim.main([])
    assert rc == 255
    assert store.load("default") is None  # stale cache was dropped
