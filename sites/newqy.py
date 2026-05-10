from sites import register_site
from sites.base import SiteAdapter
from sites.xiaoshuopu import (
    _fetch_page,
    _extract_meta,
    _parse_chapter_list,
    _parse_chapter_body,
)


@register_site
class NewqyAdapter(SiteAdapter):
    domain = "newqy.com"

    def search(self, query, session):
        print("[newqy.com] 搜索接口有反爬虫保护，不可用。")
        print("  请直接提供小说目录页 URL：")
        print("  示例：https://www.newqy.com/xs89070/")
        return []

    def get_novel_info(self, novel_url, session):
        resp = _fetch_page(novel_url, session)
        from lxml import html as lxml_html
        tree = lxml_html.fromstring(resp.text)

        title = _extract_meta(tree, "og:novel:book_name")
        if not title:
            h1 = tree.xpath("//h1/text()")
            title = h1[0].strip() if h1 else "未知"

        author = _extract_meta(tree, "og:novel:author") or ""
        chapters = _parse_chapter_list(tree, novel_url)

        return {"title": title, "author": author, "chapters": chapters}

    def get_chapter_content(self, chapter_url, session, delay=0):
        import time
        if delay > 0:
            time.sleep(delay)

        resp = _fetch_page(chapter_url, session)
        return _parse_chapter_body(resp.text)
