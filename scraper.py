import time
import re
from urllib.parse import urljoin

import requests

from config import Config
from parser import parse_chapter_body
from utils import retry


class ScraperError(Exception):
    """Raised on unrecoverable HTTP or network errors."""


BASE_URL = "https://www.biquuge.com"


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
def _do_request(session, url):
    resp = session.get(url)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp


def fetch_page(url, session):
    """Fetch a single page, return HTML text. Raises ScraperError on failure."""
    try:
        resp = _do_request(session, url)
        return resp.text
    except requests.RequestException as e:
        raise ScraperError(f"Failed to fetch {url}: {e}")


def _make_page_url(base_url, page_num):
    """Construct URL for a specific page of a chapter.

    base_url without suffix is page 1; page 2+ use _N suffix:
      .../123456.html       -> page 1
      .../123456_2.html     -> page 2
      .../123456_3.html     -> page 3
    """
    if page_num == 1:
        return base_url
    # Insert _N before .html
    return re.sub(r'(_\d+)?\.html$', f'_{page_num}.html', base_url)


def fetch_chapter_all_pages(first_page_url, session, delay=0):
    """Fetch all pages of a chapter, return concatenated content.

    Handles both single-page and multi-page chapters.
    Uses the page indicator '第(X/Y)页' to detect when to stop.
    """
    parts = []
    page_num = 1

    while True:
        url = _make_page_url(first_page_url, page_num)
        html = fetch_page(url, session)
        content, cur, total = parse_chapter_body(html)

        parts.append(content)

        if page_num >= total:
            break

        page_num += 1
        if delay:
            time.sleep(delay)

    return ''.join(parts)
