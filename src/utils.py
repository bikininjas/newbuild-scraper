import logging
import requests
from fake_useragent import UserAgent
from datetime import datetime


# French month abbreviations for date formatting
MONTHS_FR = [
    "janv",
    "févr",
    "mars",
    "avr",
    "mai",
    "juin",
    "juil",
    "août",
    "sept",
    "oct",
    "nov",
    "déc",
]

# French full month names for date formatting
MONTHS_FR_FULL = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def format_french_date(dtstr):
    """Format timestamp to French date style with abbreviated months."""
    try:
        if "T" in dtstr:
            dt = datetime.fromisoformat(dtstr.split(".")[0])
        else:
            dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S")
        month = MONTHS_FR[dt.month - 1]
        return f"{dt.day:02d} {month} {dt.year} - {dt.hour:02d}:{dt.minute:02d}"
    except (ValueError, TypeError, IndexError):
        return dtstr


def format_french_date_full(dtstr):
    """Format timestamp to French date style with full month names."""
    try:
        if "T" in dtstr:
            dt = datetime.fromisoformat(dtstr.split(".")[0])
        else:
            dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S")
        month = MONTHS_FR_FULL[dt.month - 1]
        return f"{dt.day} {month} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"
    except (ValueError, TypeError, IndexError):
        return dtstr


def get_user_agent():
    try:
        return UserAgent().random
    except (ImportError, AttributeError, requests.exceptions.RequestException, TimeoutError):
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"


def clean_price(raw):
    if raw is None:
        return None
    price = raw.replace("€", "").replace(",", ".").replace(" ", "").strip()
    try:
        return float(price)
    except (ValueError, TypeError):
        return None


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
