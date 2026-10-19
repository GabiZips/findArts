"""Native credential storage boundary. No plaintext or automatic fallback.

Used by desktop startup and settings; legacy-file removal remains explicit.
"""

import sys
from typing import Protocol


class CredentialStoreError(RuntimeError):
    """Safe message suitable for UI/logging; never includes backend details."""


class CredentialBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...


def native_backend() -> CredentialBackend:
    """Select explicitly: do not trust third-party keyring autodiscovery."""
    try:
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring
            backend = WinVaultKeyring()
            backend.persist = "local machine"
        elif sys.platform == "linux":
            from keyring.backends.SecretService import Keyring
            backend = Keyring()
        elif sys.platform == "darwin":
            from keyring.backends.macOS import Keyring
            backend = Keyring()
        else:
            raise CredentialStoreError("Native credential storage is unavailable.")
        if backend.priority <= 0:
            raise CredentialStoreError("Native credential storage is unavailable.")
        return backend
    except Exception:
        raise CredentialStoreError("Native credential storage is unavailable.") from None


class CredentialStore:
    """One credential per allowlisted field; no secret repr, file or logging.

    The backend is injectable for synthetic tests. Production callers must use
    native_backend(), never silently replace it with an unencrypted backend.
    """

    def __init__(self, backend: CredentialBackend, allowed_keys: frozenset[str],
                 service: str = "io.github.gabizips.artfinder"):
        self._backend = backend
        self._allowed_keys = frozenset(allowed_keys)
        self._service = service

    def _validate(self, key: str) -> None:
        if key not in self._allowed_keys:
            raise CredentialStoreError("Unsupported credential field.")

    def read(self, key: str) -> str | None:
        self._validate(key)
        try:
            value = self._backend.get_password(self._service, key)
            if value is not None and not isinstance(value, str):
                raise TypeError
            return value
        except Exception:
            raise CredentialStoreError("Could not read the credential store.") from None

    def write(self, key: str, value: str) -> None:
        self._validate(key)
        if not isinstance(value, str) or not value or "\x00" in value:
            raise CredentialStoreError("Invalid credential value.")
        try:
            self._backend.set_password(self._service, key, value)
            if self._backend.get_password(self._service, key) != value:
                raise ValueError
        except Exception:
            # A failed write/readback may have changed the native store. Never
            # delete the legacy value or claim migration succeeded on failure.
            raise CredentialStoreError("Credential storage could not be verified.") from None

    def delete(self, key: str) -> None:
        self._validate(key)
        try:
            if self._backend.get_password(self._service, key) is not None:
                self._backend.delete_password(self._service, key)
            if self._backend.get_password(self._service, key) is not None:
                raise ValueError
        except Exception:
            raise CredentialStoreError("Credential removal could not be verified.") from None
