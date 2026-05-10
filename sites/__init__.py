from urllib.parse import urlparse

from .base import SiteAdapter

_registry = {}


def register_site(cls):
    """Decorator to register a site adapter class."""
    _registry[cls.domain] = cls
    return cls


def get_site(url):
    """Get a site adapter instance by URL.

    Raises ValueError if the domain is not supported.
    """
    domain = urlparse(url).netloc.replace("www.", "")
    if domain not in _registry:
        supported = ", ".join(_registry.keys()) or "(none)"
        raise ValueError(f"Unsupported site: {domain}. Supported: {supported}")
    return _registry[domain]()


def list_sites():
    """Return list of registered site domains."""
    return list(_registry.keys())


# Import adapters to trigger registration
from . import biquuge, xiaoshuopu  # noqa: E402, F401
