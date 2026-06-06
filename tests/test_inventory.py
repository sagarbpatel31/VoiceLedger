from pathlib import Path

from voiceledger.ledger.inventory import add_stock, get_inventory, remove_stock


def test_add_stock_creates_inventory_item(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    new_stock = add_stock("Mangoes", 50, db_path)
    inventory = get_inventory(db_path)

    assert new_stock == 50
    assert len(inventory) == 1
    assert inventory.iloc[0]["item"] == "mangoes"
    assert inventory.iloc[0]["current_stock"] == 50


def test_remove_stock_decreases_inventory_item(tmp_path: Path) -> None:
    db_path = tmp_path / "voiceledger.sqlite3"

    add_stock("mangoes", 50, db_path)
    new_stock = remove_stock("mangoes", 12, db_path)
    inventory = get_inventory(db_path)

    assert new_stock == 38
    assert inventory.iloc[0]["current_stock"] == 38
