from src.cleaning.entity_names import merchant_group_key, primary_entity_name


def test_primary_entity_name_strips_description():
    raw = "BrightPath Marketing — Social media graphics -- March"
    assert primary_entity_name(raw) == "BrightPath Marketing"


def test_merchant_group_key_collapses_invoice_lines():
    a = "GreenLoop Technologies — Q1 branding package"
    b = "GreenLoop Technologies — Invoice #2 follow-up"
    assert merchant_group_key(a) == merchant_group_key(b) == "GreenLoop Technologies"
