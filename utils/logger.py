from typing import Union, Optional

from loguru import logger
from sys import stderr  # stdin, stdout or stderr


def setup_logger(level: Union[str, int] = 'DEBUG', colorize: Optional[bool] = True):
    logger.remove()
    logger.add(
        sink=stderr, level=level, colorize=colorize,
        enqueue=True, format="<lvl>{level}</lvl> <green>{time:YY.MM.DD HH:mm}</green> - {message}"
    )
    logger.debug("Logging setuped!")
