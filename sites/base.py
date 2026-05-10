from abc import ABC, abstractmethod


class SiteAdapter(ABC):
    """Abstract base class for novel site adapters."""

    # Site domain (e.g. "biquuge.com"), used for URL matching
    domain: str = ""

    # Whether this site supports search
    searchable: bool = False

    @abstractmethod
    def search(self, query, session):
        """Search novels by keyword.

        Returns list of dicts: [{'title': str, 'author': str, 'url': str}, ...]
        """

    @abstractmethod
    def get_novel_info(self, novel_url, session):
        """Get novel metadata and full chapter list.

        Returns dict: {'title': str, 'author': str, 'chapters': [{'title': str, 'url': str}]}
        """

    @abstractmethod
    def get_chapter_content(self, chapter_url, session, delay=0):
        """Fetch a single chapter's text content.

        Returns plain text string.
        """
