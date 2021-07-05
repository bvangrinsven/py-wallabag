class WallabagError(Exception):
    __slots__ = ('message',)

    def __init__(self, message: str):
        super().__init__()
        self.message = message.capitalize()

    def __str__(self) -> str:
        return f"{self.message}"


class NotFound(WallabagError):
    __slots__ = ()
