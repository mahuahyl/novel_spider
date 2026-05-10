import requests

from config import Config
from utils import retry


class ScraperError(Exception):
    """Raised on unrecoverable HTTP or network errors."""


def create_session(config=None):
    """Create a requests.Session with browser-like headers."""
    if config is None:
        config = Config()
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    session.timeout = config.timeout
    return session


@retry(max_attempts=3, backoff_factor=1.0)
def fetch_page(url, session):
    """Fetch a single page, return HTML text. Raises ScraperError on failure."""
    try:
        resp = session.get(url)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except requests.RequestException as e:
        raise ScraperError(f"Failed to fetch {url}: {e}")
