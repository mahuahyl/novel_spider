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

    # --- 搜索 ---

    def search(self, query, session):
        print("[xiaoshuopu.com] 搜索接口有反爬虫保护，不可用。")
        print("  请直接提供小说目录页 URL：")
        print("  示例：https://www.xiaoshuopu.com/xiaoshuo/69/69516/")
        return []

    # --- 小说信息 ---

    def get_novel_info(self, novel_url, session):
        resp = _fetch_page(novel_url, session)
        tree = lxml_html.fromstring(resp.text)

        # 从 og 标签获取元数据
        title = _extract_meta(tree, "og:novel:book_name")
        if not title:
            h1 = tree.xpath("//h1/text()")
            title = h1[0].strip() if h1 else "未知"

        author = _extract_meta(tree, "og:novel:author") or ""

        # 章节列表：table[@id='at'] > td.L > a
        chapters = _parse_chapter_list(tree, novel_url)

        return {"title": title, "author": author, "chapters": chapters}

    # --- 章节内容 ---

    def get_chapter_content(self, chapter_url, session, delay=0):
        import time

        if delay > 0:
            time.sleep(delay)

        resp = _fetch_page(chapter_url, session)
        return _parse_chapter_body(resp.text)


# ---------------------------------------------------------------------------
# HTTP 辅助函数
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
# 章节列表
# ---------------------------------------------------------------------------

def _parse_chapter_list(tree, novel_url):
    base = urllib.parse.urlparse(novel_url)
    base_domain = f"{base.scheme}://{base.netloc}"

    chapters = []

    # xiaoshuopu 使用 table[@id='at'] 配合 td.L > a
    links = tree.xpath("//table[@id='at']//td[@class='L']/a[@href]")

    if not links:
        # 兜底方案：任意 dd/a 模式
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
# 章节内容
# ---------------------------------------------------------------------------

def _parse_chapter_body(html_text):
    tree = lxml_html.fromstring(html_text)

    # xiaoshuopu 使用 div#htmlContent
    content_elements = tree.xpath("//div[@id='htmlContent']")

    if not content_elements:
        # 兜底方案
        content_elements = tree.xpath(
            "//div[@id='content' or @class='content' or @id='chaptercontent']"
        )

    if not content_elements:
        raise ParseError("无法找到章节内容")

    content_el = content_elements[0]
    raw_text = content_el.text_content()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
