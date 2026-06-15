"""Pluggable secure caches for credential JSON — stdlib only, no third-party deps.

A ``SecureStore`` persists the credential blob for a profile and gets it back. The point
of the abstraction is that the *encryption* is delegated to the operating system, so the
shim itself never ships or manages a key.

Backend by platform:

==========  =================================================================
 Platform    Backend
==========  =================================================================
 Windows     DPAPI-encrypted file (``CryptProtectData``). The blob is bound to
             the current user on the current machine — copying it elsewhere is
             useless.
 macOS       The login Keychain via the ``security`` CLI. Nothing on disk.
 Linux       libsecret via ``secret-tool`` when available; otherwise a
             ``0600`` file that is **not** encrypted at rest (with a warning).
==========  =================================================================

All ``save``/``delete`` failures are intentionally swallowed: a cache problem must never
break authentication — the shim just falls through to the real credential binary.
"""

from __future__ import annotations

import abc
import ctypes
import os
import shutil
import subprocess
import sys

SERVICE = "claude-code-credential-cache"


class SecureStore(abc.ABC):
    """Load / save / delete a profile's credential JSON, OS-protected where possible."""

    @abc.abstractmethod
    def load(self, profile: str) -> str | None:
        """Return the stored plaintext JSON for ``profile``, or ``None`` on miss."""

    @abc.abstractmethod
    def save(self, profile: str, plaintext: str) -> None:
        """Persist ``plaintext`` for ``profile``. Best-effort; never raises."""

    @abc.abstractmethod
    def delete(self, profile: str) -> None:
        """Remove any stored value for ``profile``. Best-effort; never raises."""


def _cache_dir() -> str:
    d = os.path.join(os.path.expanduser("~"), ".aws", SERVICE)
    os.makedirs(d, exist_ok=True)
    return d


# --------------------------------------------------------------------------------------
# Windows — DPAPI-encrypted file
# --------------------------------------------------------------------------------------
class WindowsDPAPIStore(SecureStore):
    class _Blob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_ulong),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    def _path(self, profile: str) -> str:
        return os.path.join(_cache_dir(), f"{profile}.bin")

    def _crypt(self, func_name: str, data: bytes) -> bytes:
        crypt32 = ctypes.WinDLL("Crypt32.dll")  # type: ignore[attr-defined]
        kernel32 = ctypes.WinDLL("Kernel32.dll")  # type: ignore[attr-defined]
        buf = ctypes.create_string_buffer(data, len(data))
        src = self._Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        dst = self._Blob()
        func = getattr(crypt32, func_name)
        # CryptProtectData / CryptUnprotectData share this 7-arg shape.
        if not func(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)):
            raise OSError(f"{func_name} failed (err={ctypes.GetLastError()})")  # type: ignore[attr-defined]
        out = bytes(ctypes.string_at(dst.pbData, dst.cbData))
        kernel32.LocalFree(dst.pbData)
        return out

    def load(self, profile: str) -> str | None:
        path = self._path(profile)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return self._crypt("CryptUnprotectData", f.read()).decode("utf-8")
        except Exception:
            # Wrong machine/user, corrupt, or DPAPI failure → treat as a miss.
            return None

    def save(self, profile: str, plaintext: str) -> None:
        try:
            enc = self._crypt("CryptProtectData", plaintext.encode("utf-8"))
            with open(self._path(profile), "wb") as f:
                f.write(enc)
        except Exception:
            pass

    def delete(self, profile: str) -> None:
        try:
            os.remove(self._path(profile))
        except OSError:
            pass


# --------------------------------------------------------------------------------------
# macOS — login Keychain via the `security` CLI
# --------------------------------------------------------------------------------------
class MacKeychainStore(SecureStore):
    def load(self, profile: str) -> str | None:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", SERVICE, "-a", profile, "-w"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip() or None

    def save(self, profile: str, plaintext: str) -> None:
        # -U updates in place if the item already exists.
        subprocess.run(
            ["security", "add-generic-password", "-U", "-s", SERVICE, "-a", profile, "-w", plaintext],
            capture_output=True,
            text=True,
        )

    def delete(self, profile: str) -> None:
        subprocess.run(
            ["security", "delete-generic-password", "-s", SERVICE, "-a", profile],
            capture_output=True,
            text=True,
        )


# --------------------------------------------------------------------------------------
# Linux — libsecret via `secret-tool`
# --------------------------------------------------------------------------------------
class LinuxSecretToolStore(SecureStore):
    def load(self, profile: str) -> str | None:
        r = subprocess.run(
            ["secret-tool", "lookup", "service", SERVICE, "profile", profile],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout:
            return None
        return r.stdout

    def save(self, profile: str, plaintext: str) -> None:
        subprocess.run(
            ["secret-tool", "store", "--label", SERVICE, "service", SERVICE, "profile", profile],
            input=plaintext,
            capture_output=True,
            text=True,
        )

    def delete(self, profile: str) -> None:
        subprocess.run(
            ["secret-tool", "clear", "service", SERVICE, "profile", profile],
            capture_output=True,
            text=True,
        )


# --------------------------------------------------------------------------------------
# Fallback — 0600 file, NOT encrypted at rest
# --------------------------------------------------------------------------------------
class PlaintextFileStore(SecureStore):
    """Last resort when no OS secret store is available.

    The file is mode ``0600`` (owner read/write only), but it is **not** encrypted. A
    one-time warning is emitted so this never happens silently.
    """

    _warned = False

    def _path(self, profile: str) -> str:
        return os.path.join(_cache_dir(), f"{profile}.json")

    def _warn(self) -> None:
        if not PlaintextFileStore._warned:
            sys.stderr.write(
                "credential-shim: WARNING — cache is NOT encrypted at rest. "
                "Install libsecret (`secret-tool`) for an encrypted store.\n"
            )
            PlaintextFileStore._warned = True

    def load(self, profile: str) -> str | None:
        path = self._path(profile)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return f.read() or None
        except OSError:
            return None

    def save(self, profile: str, plaintext: str) -> None:
        self._warn()
        try:
            fd = os.open(self._path(profile), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(plaintext)
        except OSError:
            pass

    def delete(self, profile: str) -> None:
        try:
            os.remove(self._path(profile))
        except OSError:
            pass


def get_store() -> SecureStore:
    """Pick the best available secure store for the current platform."""
    if sys.platform.startswith("win"):
        return WindowsDPAPIStore()
    if sys.platform == "darwin":
        return MacKeychainStore()
    if shutil.which("secret-tool"):
        return LinuxSecretToolStore()
    return PlaintextFileStore()
