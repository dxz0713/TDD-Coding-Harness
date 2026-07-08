"""Tests for CredentialManager."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from harness.credential_manager import CredentialManager


class TestCredentialManager:
    """Test keyring-based credential storage."""

    def test_has_api_key_false_when_empty(self) -> None:
        """钥匙串为空时 has_api_key() 返回 False。"""
        with patch("harness.credential_manager._keyring.get_password", return_value=None):
            assert not CredentialManager.has_api_key()

    def test_has_api_key_true_when_set(self) -> None:
        """钥匙串有 Key 时 has_api_key() 返回 True。"""
        with patch("harness.credential_manager._keyring.get_password", return_value="sk-test123"):
            assert CredentialManager.has_api_key()

    def test_get_api_key_from_env_fallback(self) -> None:
        """钥匙串为空时回退到环境变量。"""
        with patch("harness.credential_manager._keyring.get_password", return_value=None):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-test"}, clear=False):
                key = CredentialManager.get_api_key()
                assert key == "sk-env-test"

    def test_set_and_clear(self) -> None:
        """set_api_key → has_api_key=True → clear → has_api_key=False。"""
        with patch("harness.credential_manager._keyring.set_password") as mock_set:
            with patch("harness.credential_manager._keyring.delete_password") as mock_del:
                with patch("harness.credential_manager._keyring.get_password", side_effect=["sk-test", None]):
                    CredentialManager.set_api_key("sk-test")
                    mock_set.assert_called_once()
                    assert CredentialManager.has_api_key()

                    CredentialManager.clear_api_key()
                    mock_del.assert_called_once()
                    assert not CredentialManager.has_api_key()