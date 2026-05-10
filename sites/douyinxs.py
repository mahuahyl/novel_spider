import re
import urllib.parse

import requests
from lxml import html as lxml_html

from utils import retry
from sites import register_site
from sites.base import SiteAdapter


class ParseError(Exception):
    pass


@register_site
class DouyinxsAdapter(SiteAdapter):
    domain = "douyinxs.com"
    searchable = True

    def search(self, query, session):
        if len(query) < 2:
            print("[douyinxs.com] Search query too short.")
            return []
        encoded = urllib.parse.quote(query)
        url = f"https://www.douyinxs.com/search/?searchkey={encoded}"
        try:
            resp = _fetch_page(url, session)
            return _parse_search_results(resp.text)
        except Exception as e:
            print(f"[douyinxs.com] Search error: {e}")
            return []

    def get_novel_info(self, novel_url, session):
        resp = _fetch_page(novel_url, session)
        tree = lxml_html.fromstring(resp.text)

        title = _extract_meta(tree, "og:novel:book_name")
        if not title:
            h1 = tree.xpath("//div[@id='info']/h1/text()")
            title = h1[0].strip() if h1 else "Unknown"

        author = _extract_meta(tree, "og:novel:author") or ""

        chapters = _parse_chapter_list(tree, novel_url)

        # Handle pagination (select#indexselect)
        total_pages = _parse_total_pages(tree)
        if total_pages > 1:
            base = novel_url.rstrip("/")
            for page in range(2, total_pages + 1):
                page_url = f"{base}_{page}/"
                try:
                    page_resp = _fetch_page(page_url, session)
                    page_tree = lxml_html.fromstring(page_resp.text)
                    chapters.extend(_parse_chapter_list(page_tree, novel_url))
                except Exception:
                    break

        return {"title": title, "author": author, "chapters": chapters}

    def get_chapter_content(self, chapter_url, session, delay=0):
        import time
        if delay > 0:
            time.sleep(delay)

        resp = _fetch_page(chapter_url, session)
        return _parse_chapter_body(resp.text)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

@retry(max_attempts=3, backoff_factor=1.0)
def _fetch_page(url, session=None):
    if session is None:
        session = requests.Session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp


def _extract_meta(tree, prop):
    el = tree.xpath(f"//meta[@property='{prop}']/@content")
    return el[0].strip() if el else None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _parse_search_results(html_text):
    tree = lxml_html.fromstring(html_text)
    results = []

    items = tree.xpath("//div[@class='novelslist2']//li[span[@class='s2']]")
    for item in items:
        link = item.xpath(".//span[@class='s2']/a[@href]")
        if not link:
            continue
        link = link[0]
        href = link.get("href", "")
        title = link.text_content().strip()
        if not title or not href:
            continue

        if not href.startswith("http"):
            href = "https://www.douyinxs.com" + href

        author = ""
        author_el = item.xpath(".//span[@class='s4']/text()")
        if author_el:
            author = author_el[0].strip()

        results.append({"title": title, "author": author, "url": href})

    return results


# ---------------------------------------------------------------------------
# Chapter list
# ---------------------------------------------------------------------------

def _parse_chapter_list(tree, novel_url):
    base = urllib.parse.urlparse(novel_url)
    base_domain = f"{base.scheme}://{base.netloc}"

    chapters = []

    # Find the "正文" section to skip "最新章节" duplicates
    dts = tree.xpath("//div[@id='list']//dl/dt")
    body_section = None
    for dt in dts:
        if "正文" in dt.text_content():
            body_section = dt
            break

    if body_section is not None:
        # Collect all <dd> siblings after the "正文" <dt>
        links = []
        for elem in body_section.itersiblings():
            if elem.tag == "dt":
                break
            if elem.tag == "dd":
                a = elem.xpath("./a[@href]")
                if a:
                    links.append(a[0])
    else:
        # Fallback: all dd/a links
        links = tree.xpath("//div[@id='list']//dl//dd/a[@href]")

    for link in links:
        href = link.get("href", "")
        title = link.text_content().strip()
        if not href or not title:
            continue

        if href.startswith("/"):
            href = base_domain + href

        chapters.append({"title": title, "url": href})

    return chapters


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def _parse_total_pages(tree):
    options = tree.xpath("//select[@id='indexselect']/option/@value")
    if not options:
        return 1

    max_page = 1
    for val in options:
        match = re.search(r'_(\d+)/?$', val)
        if match:
            p = int(match.group(1))
            if p > max_page:
                max_page = p
    return max_page


# ---------------------------------------------------------------------------
# Chapter content
# ---------------------------------------------------------------------------

def _parse_chapter_body(html_text):
    tree = lxml_html.fromstring(html_text)

    content_el = tree.xpath("//article[@id='content' or @class='content']")
    if not content_el:
        content_el = tree.xpath("//div[@id='content']")

    if not content_el:
        raise ParseError("Could not find chapter content")

    raw_text = content_el[0].text_content()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
