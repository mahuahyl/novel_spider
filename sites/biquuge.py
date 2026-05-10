import re
import time

import requests
from lxml import html as lxml_html

from config import Config
from utils import retry
from sites import register_site
from sites.base import SiteAdapter


class ParseError(Exception):
    pass


class ScraperError(Exception):
    pass


@register_site
class BiquugeAdapter(SiteAdapter):
    domain = "biquuge.com"

    # --- search ---

    def search(self, query, session):
        return _search_novels(query, session)

    # --- novel info ---

    def get_novel_info(self, novel_url, session):
        return _get_novel_info(novel_url, session)

    # --- chapter content ---

    def get_chapter_content(self, chapter_url, session, delay=0):
        return _fetch_chapter_all_pages(chapter_url, session, delay)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

@retry(max_attempts=3, backoff_factor=1.0)
def _fetch_page(url, session=None):
    """Fetch a page and return the response object."""
    if session is None:
        session = requests.Session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _search_novels(query, session):
    """Search novels on biquuge.com, return list of {title, author, url}."""
    import urllib.parse

    encoded = urllib.parse.quote(query)
    search_urls = [
        f"https://www.biquuge.com/search.php?q={encoded}",
        f"https://www.biquuge.com/search.html",
    ]

    for url in search_urls:
        try:
            resp = _fetch_page(url, session)
            tree = lxml_html.fromstring(resp.text)
            results = _parse_search_results(tree)
            if results:
                return results
        except Exception:
            continue

    # Try POST if GET failed
    try:
        resp = session.post(
            "https://www.biquuge.com/search.html",
            data={"searchkey": query},
            timeout=30,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        tree = lxml_html.fromstring(resp.text)
        return _parse_search_results(tree)
    except Exception:
        pass

    return []


def _parse_search_results(tree):
    """Extract search results from HTML tree."""
    results = []

    # Strategy 1: dl > dt > a pattern
    items = tree.xpath("//dl/dt")
    for item in items:
        link = item.xpath(".//a[@href]")
        if not link:
            continue
        link = link[0]
        href = link.get("href", "")
        title = link.text_content().strip()
        if not title:
            continue

        if not href.startswith("http"):
            href = "https://www.biquuge.com" + href

        author = ""
        author_el = item.xpath(".//a[contains(@href, 'author')]")
        if author_el:
            author = author_el[0].text_content().strip()

        results.append({"title": title, "author": author, "url": href})

    if results:
        return results

    # Strategy 2: div#main links
    items = tree.xpath("//div[@id='main']//a[@href]")
    for item in items:
        href = item.get("href", "")
        if re.match(r"/\d+/\d+/?$", href):
            title = item.text_content().strip()
            if title:
                results.append(
                    {
                        "title": title,
                        "author": "",
                        "url": "https://www.biquuge.com" + href,
                    }
                )

    if results:
        return results

    # Strategy 3: table rows
    rows = tree.xpath("//table//tr")
    for row in rows:
        cells = row.xpath(".//td")
        if len(cells) < 2:
            continue
        link = cells[0].xpath(".//a[@href]")
        if not link:
            continue
        link = link[0]
        href = link.get("href", "")
        title = link.text_content().strip()
        if not title:
            continue

        if not href.startswith("http"):
            href = "https://www.biquuge.com" + href

        author = cells[1].text_content().strip() if len(cells) > 1 else ""

        results.append({"title": title, "author": author, "url": href})

    return results


# ---------------------------------------------------------------------------
# Novel info
# ---------------------------------------------------------------------------

def _get_novel_info(novel_url, session):
    """Fetch novel index page and return {title, author, chapters}."""
    resp = _fetch_page(novel_url, session)
    tree = lxml_html.fromstring(resp.text)

    # Parse metadata
    title = _extract_meta(tree, "og:novel:book_name")
    if not title:
        h1 = tree.xpath("//h1/text()")
        title = h1[0].strip() if h1 else "Unknown"

    author = _extract_meta(tree, "og:novel:author") or ""

    # Parse chapter list from first page
    chapters = _parse_chapter_list(tree, novel_url)

    # Handle pagination (index_N.html)
    total_pages = _parse_total_pages(tree)
    if total_pages > 1:
        base_url = novel_url.rstrip("/")
        if not base_url.endswith("/"):
            base_url += "/"
        for page in range(2, total_pages + 1):
            page_url = f"{base_url}index_{page}.html"
            try:
                page_resp = _fetch_page(page_url, session)
                page_tree = lxml_html.fromstring(page_resp.text)
                chapters.extend(_parse_chapter_list(page_tree, novel_url))
            except Exception:
                break

    return {"title": title, "author": author, "chapters": chapters}


def _extract_meta(tree, prop):
    """Extract content from a meta[property] tag."""
    el = tree.xpath(f"//meta[@property='{prop}']/@content")
    return el[0].strip() if el else None


def _parse_chapter_list(tree, novel_url):
    """Extract chapter links from the index page tree."""
    import urllib.parse

    base = urllib.parse.urlparse(novel_url)
    base_domain = f"{base.scheme}://{base.netloc}"

    chapters = []
    links = tree.xpath("//dd/a[@href]")

    if not links:
        links = tree.xpath("//div[@id='list']//a[@href]")

    for link in links:
        href = link.get("href", "")
        title = link.text_content().strip()
        if not href or not title:
            continue

        if href.startswith("/"):
            href = base_domain + href
        elif not href.startswith("http"):
            href = novel_url.rstrip("/") + "/" + href

        chapters.append({"title": title, "url": href})

    return chapters


def _parse_total_pages(tree):
    """Determine how many pages the chapter list spans."""
    page_links = tree.xpath("//div[@class='page']//a[@href]")
    max_page = 1

    for link in page_links:
        href = link.get("href", "")
        match = re.search(r"index_(\d+)\.html", href)
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num

    if max_page == 1:
        last_links = tree.xpath(
            "//a[contains(@href, 'index_') and contains(text(), '末页')]/@href"
        )
        if last_links:
            match = re.search(r"index_(\d+)\.html", last_links[0])
            if match:
                max_page = int(match.group(1))

    return max_page


# ---------------------------------------------------------------------------
# Chapter content
# ---------------------------------------------------------------------------

def _fetch_chapter_all_pages(first_page_url, session, delay=0):
    """Fetch all pages of a chapter and return combined text."""
    url = first_page_url
    all_lines = []
    page_num = 1

    while url:
        resp = _fetch_page(url, session)
        text, total_pages = _parse_chapter_body(resp.text)

        if page_num == 1 and total_pages and total_pages > 1:
            base = url.rsplit(".", 1)[0]
            ext = "." + url.rsplit(".", 1)[1] if "." in url else ""

            for p in range(2, total_pages + 1):
                page_url = f"{base}_{p}{ext}"
                try:
                    if delay > 0:
                        time.sleep(delay)
                    page_resp = _fetch_page(page_url, session)
                    page_text, _ = _parse_chapter_body(page_resp.text)
                    text += "\n" + page_text
                except Exception:
                    break

        all_lines.append(text)
        url = None

    return "\n".join(all_lines)


def _parse_chapter_body(html_text):
    """Extract chapter text from HTML.

    Returns (text, total_pages) where total_pages is None for single-page chapters.
    """
    tree = lxml_html.fromstring(html_text)

    content_elements = tree.xpath("//article[@class='font_max']")

    if not content_elements:
        content_elements = tree.xpath(
            "//div[@id='content' or @class='content' or @id='chaptercontent']"
        )

    if not content_elements:
        content_elements = tree.xpath("//div[contains(@class, 'txt')]")

    if not content_elements:
        raise ParseError("Could not find chapter content in the page")

    content_el = content_elements[0]
    raw_text = content_el.text_content()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    if len(lines) > 4:
        lines = lines[2:-2]

    page_pattern = re.compile(r"第\s*(\d+)\s*/\s*(\d+)\s*页")
    total_pages = None
    cleaned_lines = []
    for line in lines:
        match = page_pattern.search(line)
        if match:
            total_pages = int(match.group(2))
        else:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), total_pages
