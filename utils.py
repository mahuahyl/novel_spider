import os
import re
import time
from functools import wraps


def retry(max_attempts=3, backoff_factor=1.0):
    """装饰器：异常时指数退避重试。"""
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
    """去除 Windows/Linux 文件名中的非法字符。"""
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()


def ensure_dir(path):
    """创建目录（如不存在）。"""
    os.makedirs(path, exist_ok=True)
