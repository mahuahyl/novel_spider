import re
from lxml import etree


class ParseError(Exception):
    """Raised when XPath extraction fails (site template may have changed)."""


PAGE_INFO_RE = re.compile(r'第\((\d+)/(\d+)\)页')


def parse_page_info(text):
    """Extract (current_page, total_pages) from page indicator text like '第(1/3)页'.
    Returns (1, 1) if no page indicator found (single-page chapter).
    """
    m = PAGE_INFO_RE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1, 1


def parse_chapter_body(html):
    """Extract chapter body text and page info from HTML.

    Returns (content, current_page, total_pages).
    """
    root = etree.HTML(html)
    lines = root.xpath("//article[@class='font_max']/text()")

    if not lines:
        raise ParseError("Failed to extract chapter content — "
                         "XPath '//article[@class=\"font_max\"]/text()' returned empty")

    # Detect page info from the first line before trimming
    page_info = parse_page_info(lines[0]) if lines else (1, 1)

    # Strip boilerplate: first 2 lines (page indicator + site header),
    # last 2 lines (page indicator + next/prev links)
    body_lines = lines[2:-2]

    content = ''.join(body_lines)
    return content, page_info[0], page_info[1]


def _xpath_first(root, paths, label):
    """Try multiple XPath expressions, return first non-empty result.
    Raises ParseError if all fail.
    """
    for xpath in paths:
        result = root.xpath(xpath)
        if result:
            return result
    raise ParseError(f"Failed to extract {label} — all XPaths returned empty")


def parse_search_results(html):
    """Extract novel entries from search results page.

    Returns list of dicts: [{"title": str, "author": str, "url": str}, ...]
    """
    root = etree.HTML(html)

    # Try common result row patterns
    rows = root.xpath("//div[@id='main']//table/tr[position()>1]")
    if not rows:
        rows = root.xpath("//div[contains(@class,'result')]//li")
    if not rows:
        rows = root.xpath("//div[@class='novellist']//li")

    results = []
    for row in rows:
        links = row.xpath(".//a")
        if not links:
            continue
        a = links[0]
        title = (a.text or '').strip()
        href = a.get("href", "")

        # Author is often in the 3rd column or a sibling span
        spans = row.xpath(".//span")
        author = spans[0].text.strip() if spans and spans[0].text else ""

        if title and href:
            results.append({"title": title, "author": author, "url": href})

    if not results:
        raise ParseError("Failed to extract search results — no novel entries found")
    return results


def parse_novel_info(html, base_url=""):
    """Extract novel metadata and chapter list from novel index page.

    Returns dict:
        {"title": str, "author": str, "chapters": [{"title": str, "url": str}, ...]}
    """
    root = etree.HTML(html)

    # Title
    title_paths = [
        "//meta[@property='og:novel:book_name']/@content",
        "//div[@class='info']/h1/text()",
        "//h1/text()",
        "//meta[@property='og:title']/@content",
    ]
    title = _xpath_first(root, title_paths, "novel title")[0].strip()

    # Author — prefer og:novel:author meta, fall back to info block
    author = ""
    author_meta = root.xpath("//meta[@property='og:novel:author']/@content")
    if author_meta:
        author = author_meta[0].strip()
    else:
        try:
            author_paths = [
                "//div[contains(@class,'info')]//li[1]/a/text()",
                "//div[@class='info']//ul/li[1]/a/text()",
            ]
            author = _xpath_first(root, author_paths, "author")[0].strip()
        except ParseError:
            pass

    # Chapter list — real site uses book_list book_list2 class
    chapter_paths = [
        "//div[contains(@class,'book_list2')]//li/a",
        "//div[contains(@class,'book_list')]//li/a",
        "//div[@id='list']//dd/a",
    ]
    chapter_nodes = _xpath_first(root, chapter_paths, "chapter list")

    chapters = []
    for a in chapter_nodes:
        ch_title = (a.text or '').strip()
        ch_href = a.get("href", "")
        if ch_title and ch_href:
            # Resolve relative URLs
            if ch_href.startswith("/"):
                ch_href = "https://www.biquuge.com" + ch_href
            elif not ch_href.startswith("http"):
                ch_href = base_url.rstrip("/") + "/" + ch_href.lstrip("/")
            chapters.append({"title": ch_title, "url": ch_href})

    if not chapters:
        raise ParseError("Failed to extract chapter list — no chapter links found")

    return {"title": title, "author": author, "chapters": chapters}
