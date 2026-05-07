import time
import re

import requests

from config import Config
from parser import parse_chapter_body, parse_search_results, parse_novel_info, parse_total_pages
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


def search_novels(query):
    """Search for novels by name. Returns list of dicts.

    Tries multiple search endpoints. Returns empty list if search fails
    (user should fall back to providing URL directly).
    """
    session = create_session()

    search_urls = [
        ("GET", "https://www.biquuge.com/search.php?q=" + query, None),
        ("POST", "https://www.biquuge.com/search.html", {"searchkey": query}),
    ]

    for method, url, data in search_urls:
        try:
            if method == "POST":
                resp = session.post(url, data=data, timeout=30)
            else:
                resp = session.get(url, timeout=30)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return parse_search_results(resp.text)
        except Exception:
            continue

    return []


def get_novel_info(novel_url, session):
    """Fetch the novel index page and extract metadata + chapter list.

    Handles paginated chapter lists.
    Returns dict with keys: title, author, chapters.
    """
    # Normalize: strip trailing filename, get clean base URL
    base = re.sub(r'index_\d+\.html$', '', novel_url.rstrip("/"))
    base = base.rstrip("/")

    html = fetch_page(base + "/", session)
    info = parse_novel_info(html, base + "/")

    total_pages = parse_total_pages(html)

    if total_pages > 1:
        for page_num in range(2, total_pages + 1):
            page_url = f"{base}/index_{page_num}.html"
            page_html = fetch_page(page_url, session)
            page_info = parse_novel_info(page_html, page_url)
            info["chapters"].extend(page_info["chapters"])

    return info
