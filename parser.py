import re
from lxml import etree


class ParseError(Exception):
    """XPath 提取失败（网站模板可能已变更）时抛出。"""


PAGE_INFO_RE = re.compile(r'第\((\d+)/(\d+)\)页')


def parse_page_info(text):
    """从"第(1/3)页"翻页标记中提取 (当前页, 总页数)。
    如无翻页标记则返回 (1, 1)（单页章节）。
    """
    m = PAGE_INFO_RE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1, 1


def parse_chapter_body(html):
    """从 HTML 中提取章节正文和翻页信息。

    返回 (正文内容, 当前页码, 总页数)。
    """
    root = etree.HTML(html)
    lines = root.xpath("//article[@class='font_max']/text()")

    if not lines:
        raise ParseError("章节正文提取失败 — "
                         "XPath '//article[@class=\"font_max\"]/text()' 返回为空")

    # 翻页标记通常在前 3 行内（常在第 1 行，因为第 0 行是空白缩进）。扫描前几行。
    page_info = (1, 1)
    for line in lines[:3]:
        pi = parse_page_info(line)
        if pi != (1, 1):
            page_info = pi
            break

    # 去除网站固定内容：前2行（缩进+翻页标记），后2行（翻页标记+上下页链接）
    body_lines = lines[2:-2]

    content = ''.join(body_lines)
    return content, page_info[0], page_info[1]


def _xpath_first(root, paths, label):
    """尝试多个 XPath 表达式，返回第一个非空结果。
    全部失败则抛出 ParseError。
    """
    for xpath in paths:
        result = root.xpath(xpath)
        if result:
            return result
    raise ParseError(f"Failed to extract {label} — all XPaths returned empty")


def parse_search_results(html):
    """从搜索结果页面提取小说条目。

    返回字典列表: [{"title": 书名, "author": 作者, "url": 链接}, ...]
    """
    root = etree.HTML(html)

    results = []

    # 实际 biquuge 站点的搜索结果使用 dl>dt>a 放封面图，dd>h3>a 放标题
    items = root.xpath("//div[contains(@class,'hot')]//dl")
    if not items:
        items = root.xpath("//div[@id='main']//dl")
    if not items:
        items = root.xpath("//div[contains(@class,'result')]//li")

    for dl in items:
        # 标题和链接从 h3>a 或 dt>a 提取
        title_links = dl.xpath(".//h3/a")
        if not title_links:
            title_links = dl.xpath(".//dt/a")
        if not title_links:
            title_links = dl.xpath(".//a")

        if not title_links:
            continue

        a = title_links[0]
        title = (a.text or '').strip()
        # 去掉 "[科幻]" 等分类前缀
        title = re.sub(r'^\[.*?\]', '', title).strip()
        href = a.get("href", "")

        # 作者从 book_other 的 dd 内 span 提取
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

    # 备选方案：尝试通用搜索结果模式
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
        raise ParseError("搜索结果提取失败 — 未找到小说条目")
    return results


def parse_novel_info(html, base_url=""):
    """从小说首页提取元数据和章节目录。

    返回字典:
        {"title": 书名, "author": 作者, "chapters": [{"title": 章节名, "url": 链接}, ...]}
    """
    root = etree.HTML(html)

    # 提取书名
    title_paths = [
        "//meta[@property='og:novel:book_name']/@content",
        "//div[@class='info']/h1/text()",
        "//h1/text()",
        "//meta[@property='og:title']/@content",
    ]
    title = _xpath_first(root, title_paths, "novel title")[0].strip()

    # 提取作者 — 优先用 og:novel:author meta，备选 info 区块
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

    # 提取章节列表 — 实际站点使用 book_list book_list2 样式类
    chapter_paths = [
        "//div[contains(@class,'book_list2')]//li/a",
        "//div[contains(@class,'book_list')]//li/a",
        "//div[@id='list']//dd/a",
    ]
    chapter_nodes = _xpath_first(root, chapter_paths, "章节列表")

    chapters = []
    for a in chapter_nodes:
        ch_title = (a.text or '').strip()
        ch_href = a.get("href", "")
        if ch_title and ch_href:
            # 补全相对 URL 为绝对路径
            if ch_href.startswith("/"):
                ch_href = "https://www.biquuge.com" + ch_href
            elif not ch_href.startswith("http"):
                ch_href = base_url.rstrip("/") + "/" + ch_href.lstrip("/")
            chapters.append({"title": ch_title, "url": ch_href})

    if not chapters:
        raise ParseError("章节目录提取失败 — 未找到章节链接")

    return {"title": title, "author": author, "chapters": chapters}


def parse_total_pages(html):
    """从分页控件提取章节目录总页数（如 "1/6" → 6）。
    无分页则返回 1。
    """
    root = etree.HTML(html)
    # 在分页链接中查找 "1/6" 模式
    page_texts = root.xpath("//div[contains(@class,'pages')]//a/text()")
    for text in page_texts:
        text = text.strip()
        if '/' in text and text.replace('/', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '') == '/':
            parts = text.split('/')
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])
    # 备选方案：统计分页链接数量
    page_links = root.xpath("//div[contains(@class,'pages')]//a/@href")
    max_page = 1
    for href in page_links:
        m = re.search(r'index_(\d+)\.html', href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page
