from pathlib import Path

from voiceledger.ledger.database import add_transaction
from voiceledger.parser.rules import parse_transaction
from voiceledger.reports.whatsapp_summary import generate_whatsapp_summary


def test_generate_whatsapp_summary_includes_business_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_transaction(parse_transaction("Bought 50 mangoes for 900"), db_path)
    add_transaction(parse_transaction("Sold 12 mangoes, 200 each"), db_path)
    add_transaction(parse_transaction("Amit owes 350"), db_path)
    add_transaction(parse_transaction("Bought 2 onions"), db_path)

    summary = generate_whatsapp_summary(db_path=db_path, low_stock_threshold=5)

    assert "VoiceLedger Daily Summary" in summary
    assert "Sales: ₹2400" in summary
    assert "Expenses: ₹900" in summary
    assert "Profit: ₹1500" in summary
    assert "Outstanding Credit: ₹350" in summary
    assert "Top Product: Mangoes" in summary
    assert "Low Stock: Onions" in summary


def test_generate_whatsapp_summary_handles_empty_data(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    summary = generate_whatsapp_summary(db_path=db_path)

    assert "Sales: ₹0" in summary
    assert "Expenses: ₹0" in summary
    assert "Profit: ₹0" in summary
    assert "Outstanding Credit: ₹0" in summary
    assert "Top Product: None" in summary
    assert "Low Stock: None" in summary


def test_generate_whatsapp_summary_supports_language_labels(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"
    add_transaction(parse_transaction("Vendí 12 mangos, 20 cada uno"), db_path)

    spanish = generate_whatsapp_summary(db_path=db_path, language="Spanish", currency_symbol="$")
    french = generate_whatsapp_summary(db_path=db_path, language="French", currency_symbol="€")
    portuguese = generate_whatsapp_summary(db_path=db_path, language="Portuguese", currency_symbol="R$")

    assert "Resumen Diario" in spanish
    assert "Ventas: $240" in spanish
    assert "Resume Quotidien" in french
    assert "Ventes: €240" in french
    assert "Resumo Diario" in portuguese
    assert "Vendas: R$240" in portuguese
