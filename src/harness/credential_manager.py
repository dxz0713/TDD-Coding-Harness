"""Credential manager — OS keyring integration (keyring).

Provides secure storage and guided first-run setup for API keys,
backed by the operating system credential manager (Windows Credential
Manager, macOS Keychain, Linux Secret Service).

Usage::

    cm = CredentialManager()
    api_key = cm.get_api_key()       # auto-prompt on first call
"""

from __future__ import annotations

import getpass
import logging
import sys
from typing import ClassVar

logger = logging.getLogger(__name__)

# keyring is an optional dependency — degrade gracefully when not installed.
try:
    import keyring
except ModuleNotFoundError:
    keyring = None  # type: ignore[assignment]


class _NoKeyringBackend:
    """Stand-in when the keyring package is not installed."""

    @staticmethod
    def get_password(service: str, username: str) -> None:
        return None

    @staticmethod
    def set_password(service: str, username: str, password: str) -> None:
        raise RuntimeError("keyring package not installed — cannot store credential")

    @staticmethod
    def delete_password(service: str, username: str) -> None:
        raise RuntimeError("keyring package not installed — cannot delete credential")

    class errors:
        class PasswordDeleteError(RuntimeError):
            pass


_keyring: object = keyring if keyring is not None else _NoKeyringBackend


class CredentialManager:
    """System keyring-backed credential storage.

    Attributes:
        SERVICE_NAME: The keyring service name used for all credentials.
    """

    SERVICE_NAME: ClassVar[str] = "tdd-harness"

    # ── Public API ──────────────────────────────────────────────────

    @staticmethod
    def get_api_key(env_var: str = "OPENAI_API_KEY") -> str:
        """Retrieve the API key from the system keyring.

        Falls back to the environment variable if the keyring is empty.
        If neither is available, prompts the user for interactive input.

        Args:
            env_var: Environment variable name to fall back to.

        Returns:
            The API key as a string.
        """
        # 1. Try keyring
        key = _keyring.get_password(CredentialManager.SERVICE_NAME, "openai_api_key")
        if key:
            logger.debug("API key loaded from system keyring")
            return key

        # 2. Try environment variable
        import os

        key = os.getenv(env_var)
        if key:
            logger.info("API key loaded from environment variable %s", env_var)
            return key

        # 3. Interactive prompt
        print("No API key found. Please enter your OpenAI-compatible API key.")
        print("(Input will be hidden for security.)")
        key = getpass.getpass("API Key: ")
        if key:
            CredentialManager.set_api_key(key)
            return key

        logger.error("No API key provided.")
        sys.exit(1)

    @staticmethod
    def set_api_key(key: str) -> None:
        """Store an API key in the system keyring.

        Args:
            key: The API key to store.
        """
        _keyring.set_password(CredentialManager.SERVICE_NAME, "openai_api_key", key)
        logger.info("API key saved to system keyring")

    @staticmethod
    def has_api_key() -> bool:
        """Check whether an API key is available in the keyring.

        Returns:
            True if a key exists in the keyring.
        """
        return _keyring.get_password(CredentialManager.SERVICE_NAME, "openai_api_key") is not None

    @staticmethod
    def clear_api_key() -> None:
        """Remove the API key from the system keyring."""
        try:
            _keyring.delete_password(CredentialManager.SERVICE_NAME, "openai_api_key")
            logger.info("API key cleared from system keyring")
        except Exception:
            logger.info("No API key to clear from system keyring")