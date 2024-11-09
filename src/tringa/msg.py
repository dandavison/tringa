import os
import sys
from enum import IntEnum
from typing import NoReturn

from rich.console import Console


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3

    @classmethod
    def from_env(cls) -> "LogLevel":
        return cls[os.getenv("TRINGA_LOG_LEVEL", "WARN").upper()]


log_level = LogLevel.from_env()


def debug(*args) -> None:
    if log_level <= LogLevel.DEBUG:
        print(*args, file=sys.stderr)


def info(*args) -> None:
    if log_level <= LogLevel.INFO:
        print(*args, file=sys.stderr)


def warn(*args) -> None:
    if log_level <= LogLevel.WARN:
        console = Console(stderr=True)
        console.print("[bold yellow]WARN:[/bold yellow]", *args)


def error(*args) -> None:
    if log_level <= LogLevel.ERROR:
        console = Console(stderr=True)
        console.print("[bold red]ERROR:[/bold red]", *args)


def fatal(*args) -> NoReturn:
    error(*args)
    sys.exit(1)
