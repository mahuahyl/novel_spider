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
    searchable = True

    # --- 搜索 ---

    def search(self, query, session):
        return _search_novels(query, session)

    # --- 小说信息 ---

    def get_novel_info(self, novel_url, session):
        return _get_novel_info(novel_url, session)

    # --- 章节内容 ---

    def get_chapter_content(self, chapter_url, session, delay=0):
        return _fetch_chapter_all_pages(chapter_url, session, delay)


# ---------------------------------------------------------------------------
# HTTP 辅助函数
# ---------------------------------------------------------------------------

@retry(max_attempts=3, backoff_factor=1.0)
def _fetch_page(url, session=None):
    """获取页面并返回响应对象。"""
    if session is None:
        session = requests.Session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp


# ---------------------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------------------

def _search_novels(query, session):
    """在 biquuge.com 搜索小说，返回 {title, author, url} 列表。"""
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

    # 如果 GET 失败，尝试 POST
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
    """从 HTML 树中提取搜索结果。"""
    results = []

    # 方案 1：dl 块中的 dd > h3 > a（当前 biquuge 布局）
    dl_items = tree.xpath("//dl")
    for dl in dl_items:
        # 标题链接位于 dd > h3 > a 中
        title_links = dl.xpath(".//dd/h3/a[@href]")
        if not title_links:
            continue
        link = title_links[0]
        href = link.get("href", "")
        title = link.text_content().strip()
        # 去掉分类前缀，如 [网游]、[玄幻]
        title = re.sub(r'^\[.*?\]', '', title).strip()
        if not title or not href:
            continue

        if not href.startswith("http"):
            href = "https://www.biquuge.com" + href

        # 作者位于 dd.book_other > span 中
        author = ""
        author_spans = dl.xpath(".//dd[@class='book_other'][contains(text(),'作者')]/span")
        if author_spans:
            author = author_spans[0].text_content().strip()

        results.append({"title": title, "author": author, "url": href})

    if results:
        return results

    if results:
        return results

    # 方案 2：div#main 链接
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

    # 方案 3：表格行
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
# 小说信息
# ---------------------------------------------------------------------------

def _get_novel_info(novel_url, session):
    """获取小说目录页，返回 {title, author, chapters}。"""
    resp = _fetch_page(novel_url, session)
    tree = lxml_html.fromstring(resp.text)

    # 解析元数据
    title = _extract_meta(tree, "og:novel:book_name")
    if not title:
        h1 = tree.xpath("//h1/text()")
        title = h1[0].strip() if h1 else "未知"

    author = _extract_meta(tree, "og:novel:author") or ""

    # 从第一页解析章节列表
    chapters = _parse_chapter_list(tree, novel_url)

    # 处理分页（index_N.html）
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
    """从 meta[property] 标签提取内容。"""
    el = tree.xpath(f"//meta[@property='{prop}']/@content")
    return el[0].strip() if el else None


def _parse_chapter_list(tree, novel_url):
    """从目录页 HTML 树中提取章节链接。"""
    import urllib.parse

    base = urllib.parse.urlparse(novel_url)
    base_domain = f"{base.scheme}://{base.netloc}"

    chapters = []

    # 方案 1：div.book_list2（完整章节列表） > ul > li > a
    links = tree.xpath("//div[contains(@class,'book_list2')]//ul//li/a[@href]")

    if not links:
        # 兜底方案：任意 div.book_list
        links = tree.xpath("//div[contains(@class,'book_list')]//ul//li/a[@href]")

    if not links:
        # 方案 2：dd/a（旧版布局）
        links = tree.xpath("//dd/a[@href]")

    if not links:
        # 方案 3：div#list（兜底）
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
    """确定章节列表的分页总数。"""
    # 方案 1：在分页中查找 "1/N" 文本（当前 biquuge）
    page_info = tree.xpath(
        "//ul[contains(@class,'pagination')]//li[contains(@class,'disabled')]/a[contains(@class,'page-link')]/text()"
    )
    for text in page_info:
        match = re.search(r"\d+/(\d+)", text)
        if match:
            return int(match.group(1))

    # 方案 2：从页面链接 href 中提取
    page_links = tree.xpath("//ul[contains(@class,'pagination')]//a[contains(@class,'page-link')][@href]/@href")
    max_page = 1
    for href in page_links:
        match = re.search(r"index_(\d+)\.html", href)
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num

    if max_page > 1:
        return max_page

    # 方案 3：旧版布局，使用 div.page
    page_links = tree.xpath("//div[@class='page']//a[@href]")
    for link in page_links:
        href = link.get("href", "")
        match = re.search(r"index_(\d+)\.html", href)
        if match:
            page_num = int(match.group(1))
            if page_num > max_page:
                max_page = page_num

    return max_page


# ---------------------------------------------------------------------------
# 章节内容
# ---------------------------------------------------------------------------

def _fetch_chapter_all_pages(first_page_url, session, delay=0):
    """获取章节的所有分页并返回合并后的文本。"""
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
    """从 HTML 中提取章节正文。

    返回 (text, total_pages)，其中 total_pages 在单页章节时为 None。
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
        raise ParseError("无法找到章节内容")

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
