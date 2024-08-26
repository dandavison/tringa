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


def debug(msg: str) -> None:
    if log_level <= LogLevel.DEBUG:
        print(msg, file=sys.stderr)


def info(msg: str) -> None:
    if log_level <= LogLevel.INFO:
        print(msg, file=sys.stderr)


def warn(msg: str) -> None:
    if log_level <= LogLevel.WARN:
        print(msg, file=sys.stderr)


def error(msg: str) -> None:
    print(msg, file=sys.stderr)
