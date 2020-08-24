# __all__ = ['logging', 'logger']

import logging
import os
from logging.handlers import RotatingFileHandler

import colorama
import termcolor

colorama.init(True)  # fix for windows cmd


class ColorFormatter(logging.Formatter):
    """
    DEBUG - white
    INFO - grey
    WARNING - red

    Or force set color in extra.
    """

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        color = None
        if hasattr(record, 'color'):
            color = getattr(record, 'color').lower()
            assert color in termcolor.COLORS, f'invalid terminal color: {color}'
        else:
            if record.levelno == logging.DEBUG:
                color = 'white'
            elif record.levelno == logging.INFO:
                color = 'grey'
            elif record.levelno > logging.INFO:
                color = 'red'
        if color:
            s = termcolor.colored(s, color)
        return s


def color_extra(color: str, extra: dict = None):
    if extra is None:
        extra = {}
    extra['color'] = color
    return extra


_date_fmt = "%m-%d %H:%M:%S"
_fmt = '{asctime} {filename} [line:{lineno:>3d}] {levelname:<5s}: {message}'
LOG_FORMATTER = logging.Formatter(style='{', fmt=_fmt, datefmt=_date_fmt)
COLOR_FORMATTER = ColorFormatter(style='{', fmt=_fmt, datefmt=_date_fmt)


def get_logger(name='log', level=logging.INFO, save_path='logs/'):
    """
    :param name: logger name in logging's loggerDict
    :param level: logging level for file handler, stream handler's logging level is always DEBUG
    :param save_path: folder path to save log. If set to None, logs will not be saved.
    :return:
    """
    # noinspection PyUnresolvedReferences
    if name in logging.Logger.manager.loggerDict:
        _logger = logging.getLogger(name)
    else:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setFormatter(COLOR_FORMATTER)
        console.setLevel(logging.DEBUG)
        _logger.addHandler(console)

        if save_path is not None:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            fp = os.path.join(save_path, f'{name}.log')
            fh = RotatingFileHandler(fp, encoding='utf8', maxBytes=1024 * 1024 * 3, backupCount=3)
            fh.setFormatter(LOG_FORMATTER)
            fh.setLevel(level)
            _logger.addHandler(fh)
    return _logger


logger = get_logger()
