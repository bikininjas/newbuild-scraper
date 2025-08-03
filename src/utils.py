import logging
from fake_useragent import UserAgent


def get_user_agent():
    try:
        return UserAgent().random
    except Exception:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"


def clean_price(raw):
    if raw is None:
        return None
    price = raw.replace("€", "").replace(",", ".").replace(" ", "").strip()
    try:
        return float(price)
    except Exception:
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
