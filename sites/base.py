from abc import ABC, abstractmethod


class SiteAdapter(ABC):
    """小说站点适配器抽象基类。"""

    # 站点域名（如 "biquuge.com"），用于 URL 匹配
    domain: str = ""

    # 是否支持搜索
    searchable: bool = False

    @abstractmethod
    def search(self, query, session):
        """按关键词搜索小说。

        返回字典列表：[{'title': str, 'author': str, 'url': str}, ...]
        """

    @abstractmethod
    def get_novel_info(self, novel_url, session):
        """获取小说元数据和完整章节列表。

        返回字典：{'title': str, 'author': str, 'chapters': [{'title': str, 'url': str}]}
        """

    @abstractmethod
    def get_chapter_content(self, chapter_url, session, delay=0):
        """获取单章正文内容。

        返回纯文本字符串。
        """
