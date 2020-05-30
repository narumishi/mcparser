__all__ = ['logging', 'logger']

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FORMATTER = logging.Formatter(
    style='{',
    datefmt="%m-%d %H:%M:%S",
    fmt='{filename} [line:{lineno:>3d}] {levelname:<5s}: {message}')


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
        console.setFormatter(LOG_FORMATTER)
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
