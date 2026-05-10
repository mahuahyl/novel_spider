import os
import re
import time
from functools import wraps


def retry(max_attempts=3, backoff_factor=1.0):
    """装饰器：异常时按指数退避重试。"""
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
    """移除 Windows/Linux 文件名中非法的字符。"""
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()


def ensure_dir(path):
    """如果目录不存在则创建。"""
    os.makedirs(path, exist_ok=True)
