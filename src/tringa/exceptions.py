class TringaException(Exception):
    pass


class TringaQueryException(TringaException):
    def __init__(self, message=""):
        super().__init__(
            f"{message}\nYou can use `tringa repl` to issue arbitrary SQL queries to investigate."
        )
