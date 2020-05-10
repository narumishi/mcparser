import json
import os
import re
import sys
import threading
import time
import traceback
from pprint import pprint  # noqas
from typing import Any, List, Dict, Type, Union, Iterable, Optional, Sequence, Tuple  # noqas

import mwparserfromhell as mwp  # noqas
import wikitextparser  # noqas
from mwparserfromhell.nodes.extras.parameter import Parameter  # noqas
from mwparserfromhell.nodes.tag import Tag  # noqas
from mwparserfromhell.nodes.template import Template  # noqas
from mwparserfromhell.wikicode import Wikicode  # noqas

from mcparser.base.log import *

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


def dump_json(obj, fp: str = None, **kwargs):
    indent = kwargs.pop('indent', 2)
    ensure_ascii = kwargs.pop('ensure_ascii', False)
    if fp is not None:
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        json.dump(obj, open(fp, 'w', encoding='utf-8'), ensure_ascii=ensure_ascii, indent=indent, **kwargs)
        return None
    else:
        return json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent, **kwargs)


def load_json(fp: str, **kwargs):
    return json.load(open(fp, encoding='utf8'), **kwargs)


def catch_exception(func):
    """Catch exception then print error and traceback to logger.

    Decorator can be applied to multi-threading but multi-processing
    """

    def catch_exception_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:  # noqas
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(f'================= Error in {threading.current_thread()} ====================\n'
                         f'{"".join(traceback.format_exception(exc_type, exc_value, exc_traceback))}')

    return catch_exception_wrapper


def count_time(func):
    def count_time_wrapper(*args, **kwargs):
        t0 = time.time()
        res = func(*args, **kwargs)
        dt = time.time() - t0
        logger.info(f'Counting time:\n========= {func} run for {dt:.3f} secs =========\n\n')
        return res

    return count_time_wrapper
