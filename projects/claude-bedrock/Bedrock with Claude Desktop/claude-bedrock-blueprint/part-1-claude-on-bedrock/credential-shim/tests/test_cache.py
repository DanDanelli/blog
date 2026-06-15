"""Unit tests for the pure cache helpers (no I/O, platform-independent)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from credential_shim.cache import is_fresh, parse_profile

UTC = timezone.utc


def test_parse_profile_space_form():
    assert parse_profile(["--profile", "prod"]) == "prod"


def test_parse_profile_equals_form():
    assert parse_profile(["--profile=staging"]) == "staging"


def test_parse_profile_defaults():
    assert parse_profile([]) == "default"
    assert parse_profile(["--something", "else"]) == "default"


def test_is_fresh_true_when_well_in_future():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    creds = {"Expiration": (now + timedelta(hours=1)).isoformat()}
    assert is_fresh(creds, now=now) is True


def test_is_fresh_false_within_skew():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    creds = {"Expiration": (now + timedelta(minutes=2)).isoformat()}
    assert is_fresh(creds, now=now) is False


def test_is_fresh_false_when_expired():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    creds = {"Expiration": (now - timedelta(minutes=1)).isoformat()}
    assert is_fresh(creds, now=now) is False


def test_is_fresh_handles_z_suffix():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    creds = {"Expiration": "2026-01-01T02:00:00Z"}
    assert is_fresh(creds, now=now) is True


def test_is_fresh_naive_timestamp_assumed_utc():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    creds = {"Expiration": "2026-01-01T02:00:00"}
    assert is_fresh(creds, now=now) is True


def test_is_fresh_missing_or_bad_expiration():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert is_fresh({}, now=now) is False
    assert is_fresh({"Expiration": "not-a-date"}, now=now) is False
