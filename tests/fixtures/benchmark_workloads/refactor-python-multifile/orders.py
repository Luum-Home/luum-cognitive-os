"""Order formatting fixture with duplicated normalization logic."""


def normalize_order_id(raw: str) -> str:
    cleaned = raw.strip().lower().replace(" ", "-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned
