import json
import re
import sys
import threading
import traceback
from typing import Any, List, Dict, Type, Union, Iterable, Optional, Sequence  # noqas

import mwclient  # noqas
import mwparserfromhell as mwp  # noqas
import wikitextparser  # noqas
from mwparserfromhell.nodes.extras.parameter import Parameter  # noqas
from mwparserfromhell.nodes.tag import Tag  # noqas
from mwparserfromhell.nodes.template import Template  # noqas
from mwparserfromhell.wikicode import Wikicode  # noqas

from .config import *  # noqas
from .log import *

Wikitext = Union[str, Wikicode, Template]

G = {}  # global vars


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

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:  # noqas
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(f'================= Error in {threading.current_thread()} ====================\n'
                         f'{"".join(traceback.format_exception(exc_type, exc_value, exc_traceback))}')

    return wrapper


class CatchException:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except:  # noqas
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(f'================= Error in {threading.current_thread()} ====================\n'
                         f'{"".join(traceback.format_exception(exc_type, exc_value, exc_traceback))}')


# %% site related
def get_site_page(page, n=10):
    retry_no = 0
    while retry_no < n:
        try:
            result = config.site.pages[page].text()
            return result
        except:  # noqas
            retry_no += 1
    logger.error(f'Error download page "{page}" after {n} retry.')
    return None


def redirect(code, default=None):
    if 'redirect' in code or '重定向' in code:
        new_page = trim(mwp.parse(code).filter_wikilinks()[0].title)
        logger.info(f'redirect {default} to {new_page}')
        return new_page
    else:
        return default


# %% wikitext base util
kAllTags = ('br', 'heimu', 'del', 'sup', 'bold', 'ref', 'comment', 'link', 'tegong')


class Params(dict):
    def get(self, k, default=None, cast=None, tags=None):
        """
        :param k: dict key.
        :param default: default value if key not in dict.
        :param cast: A callable function for type cast, e.g. int, str.
        :param tags: tags to be removed.
        :return:
        """
        if k not in self:
            return default
        v = super(Params, self).get(k)
        if isinstance(v, str) and tags is not None:
            v = remove_tag(v, tags)
        if cast is not None:
            v = cast(v)
        return v


def remove_tag(string: str, tags: Sequence[str] = kAllTags, console=False):
    string = string.strip()
    string = re.sub(r'<br *?/? *?>', '\n', string)
    if string in ('-', '—', ''):
        return ''
    old = string
    if 'br' in tags:
        string = re.sub(r'<br *?/? *?>', '\n', string)
    # shadow deal
    if 'heimu' in tags:
        shadows = re.findall(r'({{(?:黑幕|heimu)\|(.+?)}})', string)
        for r in shadows:
            replaced = r[1].split('|')[0]
            string = string.replace(r[0], replaced)
    if 'tegong' in tags:
        traits: List[Template] = mwp.parse(string).filter_templates(matches='{{特性')
        for trait in traits:
            params_trait = parse_template(trait)
            string = string.replace(str(trait), params_trait.get('2', params_trait['1']))

    # del/sup tag, bold('''): remain content
    if 'del' in tags:
        string = re.sub(r'<(del|sup)>(.*?)</\1>', r'\2', string)
    string = re.sub(r'<(nowiki)>(.*?)</\1>', r'\2', string)
    if 'bold' in tags:
        string = re.sub(r"'''([^']*?)'''", r'\1', string)
    # ref tag, html annotation tag, remove content
    if 'ref' in tags:
        string = re.sub(r'<ref([^<>]*?)>(.*?)</ref>', '', string)
    if 'comment' in tags:
        string = re.sub(r'<!--([\w\W]*?)-->', '', string)
    # wikilink,[[File:mash.jpg|params_or_text]]->(whole string, File, mash.jpg, params_or_text)
    if 'link' in tags:
        links = re.findall(r'(\[\[(?:(.*?):)?([^|\]]+?)(?:\|(.*?))?\]\])', string)
        for link in links:
            if link[1] == '':
                string = string.replace(link[0], link[3] or link[2])
            else:
                string = string.replace(link[0], '')
    # special
    # string = string.replace('{{jin}}', 'jin')  # Okita Souji Alter
    # final check
    if string != old and console:
        logger.info(f'remove tags: from {old} -> {string}')
    return string


def parse_template(template: Wikitext, match_pattern: str = None) -> Params:
    if isinstance(template, (str, Wikicode)):
        templates = mwp.parse(template).filter_templates(matches=match_pattern)
        if len(templates) == 0:
            return Params()
        tmpl: Template = templates[0]
    else:
        tmpl = template
    params = Params()
    for p in tmpl.params:  # type:Parameter
        value = trim(p.value)
        if value not in ('-', '—', ''):
            params[trim(p.name)] = value
    return params


def split_tabber(code: Wikitext, default=''):
    if isinstance(code, str):
        code: Wikicode = mwp.parse(code)
    tags: List[Tag] = code.filter_tags(recursive=False, matches='tabber')
    if len(tags) == 0:
        return [(default, trim(str(code)))]
    else:
        tabs = tags[0].contents.__str__().split('|-|')
        tab_list = []
        for tab in tabs:
            res = re.findall(r'^([^{}]+?)=([\w\W]*?)$', tab)[0]
            tab_list.append([res[0].strip(), res[1].strip()])
        return tab_list


def split_file_link(code: str):
    result = re.findall(r'\[\[(?:文件|File|file):([^|\]\[\n]+)', code)
    if len(result) > 0:
        return trim(result[0])
    else:
        return None
