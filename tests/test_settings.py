from pathlib import Path

from voiceledger.ledger.settings import get_business_settings, get_low_stock_threshold, update_business_settings


def test_business_settings_defaults_load_when_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    settings = get_business_settings(db_path)

    assert settings["business_name"] == "VoiceLedger Seller"
    assert settings["currency_symbol"] == "₹"
    assert get_low_stock_threshold(db_path) == 5


def test_business_settings_update_values(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    settings = update_business_settings(
        business_name="Mango Cart",
        currency_symbol="Rs ",
        low_stock_threshold=8,
        language_style="English + Hinglish",
        db_path=db_path,
    )

    assert settings["business_name"] == "Mango Cart"
    assert settings["currency_symbol"] == "Rs"
    assert settings["low_stock_threshold"] == "8.0"
    assert get_low_stock_threshold(db_path) == 8
