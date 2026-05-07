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

    results = []

    # Real biquuge site uses dl>dt>a for image+link and dd>h3>a for title
    items = root.xpath("//div[contains(@class,'hot')]//dl")
    if not items:
        items = root.xpath("//div[@id='main']//dl")
    if not items:
        items = root.xpath("//div[contains(@class,'result')]//li")

    for dl in items:
        # Title and URL from h3>a or dt>a
        title_links = dl.xpath(".//h3/a")
        if not title_links:
            title_links = dl.xpath(".//dt/a")
        if not title_links:
            title_links = dl.xpath(".//a")

        if not title_links:
            continue

        a = title_links[0]
        title = (a.text or '').strip()
        # Strip category prefix like "[科幻]"
        title = re.sub(r'^\[.*?\]', '', title).strip()
        href = a.get("href", "")

        # Author from span inside book_other dd
        author = ""
        author_spans = dl.xpath(".//dd[contains(@class,'book_other')]/span/text()")
        if author_spans:
            author = author_spans[0].strip()

        if title and href:
            if href.startswith("/"):
                href = "https://www.biquuge.com" + href
            elif not href.startswith("http"):
                href = "https://www.biquuge.com/" + href
            results.append({"title": title, "author": author, "url": href})

    # Fallback: try generic patterns
    if not results:
        rows = root.xpath("//div[@id='main']//table/tr[position()>1]")
        for row in rows:
            links = row.xpath(".//a")
            if not links:
                continue
            a = links[0]
            title = (a.text or '').strip()
            href = a.get("href", "")
            if title and href:
                if href.startswith("/"):
                    href = "https://www.biquuge.com" + href
                results.append({"title": title, "author": "", "url": href})

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


def parse_total_pages(html):
    """Extract total chapter list page count from pagination (e.g. '1/6' → 6).
    Returns 1 if no pagination found.
    """
    root = etree.HTML(html)
    # Look for "1/6" pattern in page links
    page_texts = root.xpath("//div[contains(@class,'pages')]//a/text()")
    for text in page_texts:
        text = text.strip()
        if '/' in text and text.replace('/', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '') == '/':
            parts = text.split('/')
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])
    # Fallback: count page number links
    page_links = root.xpath("//div[contains(@class,'pages')]//a/@href")
    max_page = 1
    for href in page_links:
        m = re.search(r'index_(\d+)\.html', href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page
