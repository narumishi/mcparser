import json
import pickle  # noqas
import platform
import re
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqas
from inspect import signature
from pprint import pprint  # noqas
from typing import Any, List, Dict, Type, Union, Iterable, Optional, Sequence, Tuple, Callable, T, KT, VT  # noqas

import mwparserfromhell as mwp  # noqas
import pandas as pd  # noqas
import wikitextparser  # noqas
from mwparserfromhell.nodes.extras.parameter import Parameter  # noqas
from mwparserfromhell.nodes.tag import Tag  # noqas
from mwparserfromhell.nodes.template import Template  # noqas
from mwparserfromhell.wikicode import Wikicode  # noqas

from .log import *

MapEntry = Tuple[KT, VT]
Wikitext = Union[str, Wikicode, Template]
G = {}  # global vars


# %% assist functions
def trim(s: str, chars=None):
    return s.strip(chars)


def valid_var_name(name: str):
    """Generate a valid variable name"""
    var = re.sub(r'[\\/ .\-]', '_', name.strip())
    var = re.sub(r'[^_a-zA-Z]', '', var)
    assert len(name) > 1, (name, var)
    return var


def list_append(_list: List, element, ignore=(None, '')):
    if element not in ignore:
        _list.append(element)


def list_extend(_list: List, elements: Iterable, ignore=(None, '')):
    for e in elements:
        if e not in ignore:
            _list.append(e)


def add_dict(x: Dict[Any, Union[int, float]], *args, in_place=True):
    result: Dict[Any, Union[int, float]] = x if in_place else {}
    for y in args:
        for k, v1 in y.items():
            v0 = x.get(k, 0)
            assert isinstance(v0, (int, float)) and isinstance(v1, (int, float)), \
                f'dict value must be number: v0={type(v0)} {v0}, v1={type(v1)} {v1}'
            result[k] = v0 + v1
    return result


def sort_dict(obj: Dict, key=None, reverse=False):
    """
    Return a new sorted dict using sorting function `key(k)` or `key(k, v)`.
    """
    if key is None:
        sorted_keys = sorted(obj.keys(), reverse=reverse)
    else:
        sig = signature(key)
        param_num = len(sig.parameters)
        assert param_num in (1, 2)
        if param_num == 1:
            sorted_keys = sorted(obj.keys(), key=key, reverse=reverse)
        elif param_num == 2:
            sorted_keys = sorted(obj.keys(), key=lambda k: key(k, obj[k]), reverse=reverse)
        else:
            raise ValueError()
    return dict([(k, obj[k]) for k in sorted_keys])


def load_json(fp: str, **kwargs):
    return json.load(open(fp, encoding='utf8'), **kwargs)


def dump_json(obj, fp: str = None, **kwargs):
    indent = kwargs.pop('indent', 2)
    ensure_ascii = kwargs.pop('ensure_ascii', False)
    if fp is not None:
        os.makedirs(os.path.dirname(fp) or '.', exist_ok=True)
        json.dump(obj, open(fp, 'w', encoding='utf-8'), ensure_ascii=ensure_ascii, indent=indent, **kwargs)
        return None
    else:
        return json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent, **kwargs)


def load_pickle(fp: str, default=None):
    if os.path.exists(fp):
        return pickle.load(open(fp, 'rb'))
    else:
        return default


def dump_pickle(obj, fp: str):
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    pickle.dump(obj, open(fp, 'wb'))


def catch_exception(func):
    """Catch exception then print error and traceback to logger.

    Decorator can be applied to multi-threading but multi-processing
    """

    def catch_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:  # noqas
            s = f'=== Error in {threading.current_thread()}, {func} ===\n'
            if args:
                s += f'args={str(args):.200s}\n'
            if kwargs:
                s += f'kwargs={str(kwargs):.200s}\n'
            logger.error(s, exc_info=sys.exc_info())

    return catch_exception_wrapper


def count_time(func):
    """Count time wrapper"""

    def count_time_wrapper(*args, **kwargs):
        t0 = time.time()
        res = func(*args, **kwargs)
        dt = time.time() - t0
        logger.info(f'========= Time: {func} run for {dt:.3f} secs =========')
        return res

    return count_time_wrapper


def is_windows():
    return platform.system().lower() == 'windows'


def is_macos():
    return platform.system().lower() == 'darwin'
