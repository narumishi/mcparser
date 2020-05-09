from .basic import *  # noqas

kAllTags = ('br', 'heimu', 'del', 'sup', 'bold', 'ref', 'comment', 'link', 'tegong', 'xiuzheng', 'ruby')


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


# %% common used wikitext edit functions
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
        for trait in mwp.parse(string).filter_templates(matches=r'^{{特性'):
            params_trait = parse_template(trait)
            string = string.replace(str(trait), params_trait.get('2', params_trait.get('1')))
    if 'xiuzheng' in tags:
        for template in mwp.parse(string).filter_templates(matches=r'{{修正'):
            params = parse_template(template)
            string = string.replace(str(template), params.get('1', ''))
    if 'ruby' in tags:
        for template in mwp.parse(string).filter_templates(matches=r'{{ruby'):
            params = parse_template(template)
            string = string.replace(str(template), f"{params.get('1')}[{params.get('2')}]")
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
    string = string.replace('{{jin}}', 'jin')  # Okita Souji Alter

    # final check
    if string != old and console:
        logger.info(f'remove tags: from {old} -> {string}')
    return string


def redirect(code, default=None):
    if 'redirect' in code or '重定向' in code:
        new_page = trim(mwp.parse(code).filter_wikilinks()[0].title)
        logger.info(f'redirect {default} to {new_page}')
        return new_page
    else:
        return default


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
