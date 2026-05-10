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
class XiaoshuopuAdapter(SiteAdapter):
    domain = "xiaoshuopu.com"

    # --- search ---

    def search(self, query, session):
        print("[xiaoshuopu.com] Search requires JS execution and is not supported.")
        print("Please provide the novel index URL directly.")
        print("Example: https://www.xiaoshuopu.com/xiaoshuo/69/69516/")
        return []

    # --- novel info ---

    def get_novel_info(self, novel_url, session):
        resp = _fetch_page(novel_url, session)
        tree = lxml_html.fromstring(resp.text)

        # Metadata from og tags
        title = _extract_meta(tree, "og:novel:book_name")
        if not title:
            h1 = tree.xpath("//h1/text()")
            title = h1[0].strip() if h1 else "Unknown"

        author = _extract_meta(tree, "og:novel:author") or ""

        # Chapter list: table[@id='at'] > td.L > a
        chapters = _parse_chapter_list(tree, novel_url)

        return {"title": title, "author": author, "chapters": chapters}

    # --- chapter content ---

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
# Chapter list
# ---------------------------------------------------------------------------

def _parse_chapter_list(tree, novel_url):
    base = urllib.parse.urlparse(novel_url)
    base_domain = f"{base.scheme}://{base.netloc}"

    chapters = []

    # xiaoshuopu uses table[@id='at'] with td.L > a
    links = tree.xpath("//table[@id='at']//td[@class='L']/a[@href]")

    if not links:
        # Fallback: any dd/a pattern
        links = tree.xpath("//dd/a[@href]")

    for link in links:
        href = link.get("href", "")
        title = link.get("title", "") or link.text_content().strip()
        if not href or not title:
            continue

        if href.startswith("/"):
            href = base_domain + href
        elif not href.startswith("http"):
            href = novel_url.rstrip("/") + "/" + href

        chapters.append({"title": title, "url": href})

    return chapters


# ---------------------------------------------------------------------------
# Chapter content
# ---------------------------------------------------------------------------

def _parse_chapter_body(html_text):
    tree = lxml_html.fromstring(html_text)

    # xiaoshuopu uses div#htmlContent
    content_elements = tree.xpath("//div[@id='htmlContent']")

    if not content_elements:
        # Fallback
        content_elements = tree.xpath(
            "//div[@id='content' or @class='content' or @id='chaptercontent']"
        )

    if not content_elements:
        raise ParseError("Could not find chapter content in the page")

    content_el = content_elements[0]
    raw_text = content_el.text_content()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
