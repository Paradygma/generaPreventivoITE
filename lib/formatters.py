from datetime import datetime


def as_text(value):
    if value is None:
        return ""
    return str(value)


def as_date_it(value):
    """ISO date/datetime string -> gg/mm/aaaa. Empty string if missing."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return as_text(value)
    return dt.strftime("%d/%m/%Y")


def as_euro(value):
    """Number -> '1.234,56 €' (Italian thousands/decimal separators)."""
    if value is None:
        return ""
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{formatted} €"


def as_number(value):
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value)
