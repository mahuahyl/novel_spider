from urllib.parse import urlparse

from sites.base import SiteAdapter

_registry = {}


def register_site(cls):
    """注册站点适配器类的装饰器。"""
    _registry[cls.domain] = cls
    return cls


def get_site(url):
    """根据 URL 获取站点适配器实例。

    如果域名不支持，抛出 ValueError。
    """
    domain = urlparse(url).netloc.replace("www.", "")
    if domain not in _registry:
        supported = ", ".join(_registry.keys()) or "（无）"
        raise ValueError(f"不支持的站点：{domain}。支持的站点：{supported}")
    return _registry[domain]()


def list_sites():
    """返回已注册的站点域名列表。"""
    return list(_registry.keys())


def get_all_sites():
    """返回所有已注册的站点适配器实例列表。"""
    return [cls() for cls in _registry.values()]


def get_searchable_sites():
    """返回支持搜索的站点适配器实例列表。"""
    return [cls() for cls in _registry.values() if cls.searchable]


# 导入适配器以触发注册
import sites.biquuge  # noqa: E402, F401
import sites.xiaoshuopu  # noqa: E402, F401
import sites.newqy  # noqa: E402, F401
import sites.douyinxs  # noqa: E402, F401
