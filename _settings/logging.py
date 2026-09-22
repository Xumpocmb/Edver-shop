import os
from logging.handlers import RotatingFileHandler


class EnsureRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler, создающий каталог для файла лога при запуске."""

    def __init__(self, filename, *args, **kwargs):
        directory = os.path.dirname(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
        super().__init__(filename, *args, **kwargs)