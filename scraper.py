import time
import re

import requests

from config import Config
from parser import parse_chapter_body, parse_search_results, parse_novel_info, parse_total_pages
from utils import retry


class ScraperError(Exception):
    """不可恢复的 HTTP 或网络错误时抛出。"""


def create_session(config=None):
    """创建带浏览器模拟请求头的 requests.Session。"""
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
    """抓取单个页面，返回 HTML 文本。失败时抛出 ScraperError。"""
    try:
        resp = _do_request(session, url)
        return resp.text
    except requests.RequestException as e:
        raise ScraperError(f"Failed to fetch {url}: {e}")


def _make_page_url(base_url, page_num):
    """构造章节某一页的 URL。

    无后缀的 base_url 是第一页；第 2 页起用 _N 后缀：
      .../123456.html       → 第 1 页
      .../123456_2.html     → 第 2 页
      .../123456_3.html     → 第 3 页
    """
    if page_num == 1:
        return base_url
    # 在 .html 前面插入 _N
    return re.sub(r'(_\d+)?\.html$', f'_{page_num}.html', base_url)


def fetch_chapter_all_pages(first_page_url, session, delay=0):
    """抓取一章的全部页面，返回拼接后的内容。

    自动处理单页和多页章节。
    通过"第(X/Y)页"翻页标记判断何时停止。
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
    """按名称搜索小说，返回字典列表。

    尝试多个搜索接口。搜索失败返回空列表
    （用户应降级为直接提供小说首页 URL）。
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
    """抓取小说首页，提取元数据和章节目录。

    自动处理分页的章节目录。
    返回字典，键: title（书名）, author（作者）, chapters（章节列表）。
    """
    # 标准化：去掉尾部文件名，得到干净的 base URL
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
