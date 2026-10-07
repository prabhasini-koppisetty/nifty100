import re
import pandas as pd


def normalize_ticker(value):
    """
    Normalize ticker / company ID values into uppercase stripped string.
    Returns None for invalid/null/empty values.
    """
    if pd.isna(value):
        return None

    value = str(value).strip().upper()
    return value if value else None


def normalize_year(value):
    """
    Convert financial year labels into YYYY-MM format.

    Examples:
        Mar 2024      -> 2024-03
        Mar-24        -> 2024-03
        Mar 2023 15   -> 2023-03
        Mar 2016 9m   -> 2016-03
        2024-03       -> 2024-03
        TTM           -> TTM

    TTM is deliberately NOT converted into a fake year.
    Returns None for unparseable or null inputs.
    """
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    # TTM is not an annual YYYY-MM value.
    if text.upper() == "TTM":
        return "TTM"

    # Already normalized YYYY-MM format.
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text

    # Handle plain 4-digit year format (e.g., 2019 -> 2019-03 as standard fiscal end)
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-03"

    # Match month-year combinations:
    # Mar 2024, Mar-24, Mar 2023 15, Mar 2016 9m, Dec 2012
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[-\s]+"
        r"(\d{2,4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    month_name = match.group(1).title()
    year = int(match.group(2))

    if year < 100:
        year += 2000

    month_number = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }[month_name]

    return f"{year:04d}-{month_number:02d}"
