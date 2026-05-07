import os
import re
import time
from functools import wraps


def retry(max_attempts=3, backoff_factor=1.0):
    """Decorator: retry on exception with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    delay = backoff_factor * (2 ** (attempt - 1))
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def sanitize_filename(name):
    """Remove characters illegal in Windows/Linux filenames."""
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()


def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)
