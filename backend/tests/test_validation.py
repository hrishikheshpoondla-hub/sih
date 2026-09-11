import pytest
from app.utils.validation import (
    validate_ip, validate_port, validate_timestamp,
    validate_txid, validate_wallet_address, validate_record
)

def test_ip_validation():
    assert validate_ip("198.51.100.23")[0] is True
    assert validate_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")[0] is True
    assert validate_ip("999.999.999.999")[0] is False
    assert validate_ip("invalid-ip-string")[0] is False

def test_port_validation():
    assert validate_port(8333)[0] is True
    assert validate_port("80")[0] is True
    assert validate_port(0)[0] is False
    assert validate_port(70000)[0] is False

def test_timestamp_validation():
    assert validate_timestamp("2026-09-10T12:00:00Z")[0] is True
    assert validate_timestamp("invalid-date")[0] is False

def test_txid_validation():
    valid_txid = "a" * 64
    assert validate_txid(valid_txid)[0] is True
    assert validate_txid("short_hash")[0] is False
    assert validate_txid("g" * 64)[0] is False # non-hex char

def test_wallet_address_validation():
    assert validate_wallet_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")[0] is True
    assert validate_wallet_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy")[0] is True
    assert validate_wallet_address("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")[0] is True
    assert validate_wallet_address("invalid_btc_addr")[0] is False
