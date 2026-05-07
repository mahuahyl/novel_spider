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
