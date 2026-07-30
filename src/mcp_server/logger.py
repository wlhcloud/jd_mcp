import os
import sys
from pathlib import Path

from loguru import logger as log

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = Path(os.getenv("LOG_FILE", "./logs/jd_literature.log"))
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

log.remove()
log.add(
    sys.stderr,
    level=LOG_LEVEL,
    enqueue=True,
    backtrace=False,
    diagnose=False,
)
log.add(
    str(LOG_FILE),
    level=LOG_LEVEL,
    rotation=os.getenv("LOG_ROTATION", "50 MB"),
    retention=os.getenv("LOG_RETENTION", "30 days"),
    encoding="utf-8",
    enqueue=True,
    backtrace=False,
    diagnose=False,
)


def get_logger(name: str = ""):
    """返回绑定了 name 上下文的 loguru logger，用法类似 logging.getLogger。"""
    if name:
        return log.bind(name=name)
    return log
