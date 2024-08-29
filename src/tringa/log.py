import os
import sys
from enum import IntEnum


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3

    @classmethod
    def from_env(cls) -> "LogLevel":
        return cls[os.getenv("TRINGA_LOG_LEVEL", "INFO").upper()]


log_level = LogLevel.from_env()


def debug(*args) -> None:
    if log_level <= LogLevel.DEBUG:
        print(*args, file=sys.stderr)


def info(*args) -> None:
    if log_level <= LogLevel.INFO:
        print(*args, file=sys.stderr)


def warn(*args) -> None:
    if log_level <= LogLevel.WARN:
        print(*args, file=sys.stderr)


def error(*args) -> None:
    print(*args, file=sys.stderr)
