from ..base.basic import *
from ..base.config import *

kAllTags = ('ref', 'br', 'comment', 'del', 'sup', 'nowiki', 'include', 'heimu', 'texing', 'link', 'ruby', 'bold')


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


# %% site related
def get_site_page(name, isfile=False, n=10):
    retry_no = 0
    while retry_no < n:
        try:
            if isfile:
                result = config.site.images[name]
            else:
                result = config.site.pages[name].text()
            return result
        except:  # noqas
            retry_no += 1
    logger.error(f'Error download page "{name}" after {n} retry.')
    return None


# %% common used wikitext edit functions

def remove_tag(string: str, tags: Sequence[str] = kAllTags, console=False):
    string = string.strip()
    code = mwp.parse(string)

    # html tags
    # REMOVE - ref/comment
    for tag_name in ('ref',):
        if tag_name in tags:
            for tag in code.filter_tags(matches=r'^<' + tag_name):
                string = string.replace(str(tag), '')
    if 'comment' in tags:
        for comment in code.filter_comments():
            string = string.replace(str(comment), '')
    if 'br' in tags:
        string = re.sub(r'<br *?/? *?>', '\n', string)
    # Replace with contents - sup/del/noinclude
    for tag_name in ('del', 'sup'):
        if tag_name in tags:
            for tag in code.filter_tags(matches=r'^<' + tag_name):  # type:mwp.nodes.tag.Tag
                string = string.replace(str(tag), str(tag.contents))

    if 'nowiki' in tags:
        string = re.sub(r'<\s*/?\s*nowiki\s*>', '', string)
    if 'include' in tags:
        # may nested
        string = re.sub(r'<\s*/?\s*(include|onlyinclude|includeonly|noinclude)\s*>', '', string)

    # wiki templates
    # just keep 1st
    if 'heimu' in tags:
        for template in code.filter_templates(matches=r'^{{(黑幕|heimu|模糊|修正)'):
            params = parse_template(template)
            string = string.replace(str(template), params.get('1', ''))

    # replace
    if 'texing' in tags:
        for template in code.filter_templates(matches=r'^{{特性'):
            params = parse_template(template)
            string = string.replace(str(template), params.get('2', params.get('1')))
    if 'ruby' in tags:
        for template in code.filter_templates(matches=r'^{{ruby'):
            params = parse_template(template)
            string = string.replace(str(template), f"{params.get('1')}[{params.get('2')}]")
    if 'link' in tags:
        # remove [[File:a.jpg|b|c]] - it show img
        string = re.sub(r'\[\[(文件|File):([^\[\]]*?)\]\]', '', string)
        for wiki_link in code.filter_wikilinks():  # type:mwp.nodes.wikilink.Wikilink
            # [[语音关联从者::somebody]]
            link = re.split(r':+', str(wiki_link.title))[-1]
            shown_text = wiki_link.text
            if shown_text:
                shown_text = str(shown_text).split('|', maxsplit=1)[0]
            string = string.replace(str(wiki_link), shown_text or link)

    # special
    if 'bold' in tags:
        string = re.sub(r"'''([^']*?)'''", r'\1', string)
    # Okita Souji Alter
    string = string.replace('{{jin}}', 'jin')

    # final check
    old_string = str(code)
    if string != old_string and console:
        logger.info(f'remove tags: from {len(old_string)}->{len(string)}\n'
                    f'Old string:{old_string}\n\nNew string: {string}')
    if string in ('-', '—', ''):
        return ''
    return string


def redirect_page(code, default=None):
    if 'redirect' in code or '重定向' in code:
        new_page = trim(mwp.parse(code).filter_wikilinks()[0].title)
        logger.info(f'Redirect {default} to {new_page}')
        return new_page
    else:
        return default


def parse_template(template: Wikitext, match_pattern: str = None) -> Params:
    if not isinstance(template, Template):
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


def split_tabber(code: Wikitext, default: str = '') -> List[Tuple[str, str]]:
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
            tab_list.append((res[0].strip(), res[1].strip()))
        return tab_list


def split_file_link(code: str):
    result = re.findall(r'\[\[(?:文件|File|file):([^|\]\[\n]+)', code)
    if len(result) > 0:
        return trim(result[0])
    else:
        return None


def find_effect_target(description: str, last=None):
    """
    https://fgo.wiki/w/Module:SkillString
    """
    if '敌方单体' in description:
        target = '敌方单体'
    elif '敌方全体' in description:
        target = '敌方全体'
    elif '己方单体' in description:
        target = '己方单体'
    elif '获得' in description and '暴击星' in description and '提升' not in description:  # 防止女神変生及变种夏日破坏者误判
        target = '获得暴击星'
    elif '自身' in description and '己方全体' in description:
        target = '除自身以外的己方全体'
    elif '己方全体' in description:
        target = '己方全体'
    elif '自身' in description:
        target = '自身'
    elif last == '获得暴击星':
        target = '自身'
    else:
        target = last
    return target


# %% common used template parse functions
def p_one_item(params: Params):
    """For template 材料消耗&道具"""
    return params.get('1'), params.get('2', default=1, cast=int)


def p_items(code: Wikitext):
    # qp counts may be no correct
    items: Dict[str, int] = {}
    fragments = re.findall(r'(?={{)(.+?)(?<=}})([^{}]*?)(?={{|$)', str(code))
    for item_template, groups in fragments:
        item, num = p_one_item(parse_template(item_template, match_pattern=r'^{{(道具|材料消耗)'))
        if item is None:
            continue
        groups = re.sub(r',\+', '', groups)
        group_find = re.findall(r'\d+', groups)
        if len(group_find) == 0:
            group_num = 1
        else:
            group_num = int(group_find[0])
        items[item] = num * group_num
    return items
