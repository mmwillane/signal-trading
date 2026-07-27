"""Tests sécurité : caviardage des secrets et assainissement des entrées."""

from __future__ import annotations

import logging

from src.security.safe_logging import SecretRedactionFilter
from src.security import sanitize


def _redact(msg: str) -> str:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, msg, None, None)
    SecretRedactionFilter().filter(record)
    return record.getMessage()


def test_secret_is_redacted_in_logs():
    out = _redact("Connexion avec api_key=SΕCRET12345 établie")
    assert "SΕCRET12345" not in out
    assert "REDACTED" in out


def test_non_secret_message_untouched():
    out = _redact("Téléchargement de AAPL terminé")
    assert out == "Téléchargement de AAPL terminé"


def test_clean_symbol_strips_dangerous_chars():
    assert sanitize.clean_symbol(" aapl ") == "AAPL"
    assert sanitize.clean_symbol("btc-usd") == "BTC-USD"


def test_clean_symbol_rejects_empty():
    import pytest

    with pytest.raises(ValueError):
        sanitize.clean_symbol("@@@")


def test_safe_float_rejects_nan_inf():
    assert sanitize.safe_float("nan") is None
    assert sanitize.safe_float("inf") is None
    assert sanitize.safe_float("12.5") == 12.5


def test_safe_url_only_http():
    assert sanitize.safe_url("https://ex.com/a") == "https://ex.com/a"
    assert sanitize.safe_url("javascript:alert(1)") is None
    assert sanitize.safe_url("ftp://x") is None


def test_clean_text_removes_control_chars():
    assert sanitize.clean_text("hello\x00\x07world") == "helloworld"
