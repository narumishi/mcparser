"""Parse templates parameters to instance"""
from .datatypes import *
from .util import *


# %% simple combination of template parser
def p_items(code: Wikitext):
    """Multiple items"""
    # qp counts may be no correct
    items: Dict[str, int] = {}
    for item_text, num2_text in re.findall(r'(?={{)(.+?)(?<=}})([^{}]*?)(?={{|$)', str(code)):
        item, num1 = t_one_item(parse_template(item_text, match_pattern=r'^{{(道具|材料消耗|素材)'))
        if item is None:
            continue
        num2_text = re.sub(r"([,+*x×]|''')", '', num2_text)
        if item == 'QP':
            num2_re = re.findall(r'\d+', num2_text)
        else:
            num2_re = re.findall(r'^\s*(\d+)', num2_text)
        if len(num2_re) == 0:
            num2 = 1
        else:
            num2 = int(num2_re[0])
        items[item] = num1 * num2
    return items


def p_quest_reward_drop(code: Wikicode, skip_free_drop=True):
    """Parse rewards nd drops of multiple quests"""
    drops, rewards = {}, {}  # type:Dict[str,int]
    for template in code.filter_templates(matches='^{{关卡配置'):
        quest = t_quest(parse_template(template))
        add_dict(rewards, quest.rewards)
        if not quest.isFree or not skip_free_drop:  # hard quest - like free
            for battle in quest.battles:
                add_dict(drops, battle.drops)
    return rewards, drops


def _check_unique_quest(quests: List[Quest], in_place=True):
    # maybe for branch quest? not used yet
    if not in_place:
        quests = [q for q in quests]
    names = []
    for i, quest in enumerate(quests):
        if quest.name in names:
            quests.pop(i)
            logger.info(f'redundant quest: {quest.chapter}-{quest.name}')
    return quests


def p_event_shop(code: Wikicode):
    result: Dict[str, int] = {}
    for template in code.filter_templates(matches='^{{#invoke:EventShopList'):
        params = parse_template(template)
        add_dict(result, t_event_shop_list(params))
    return result


# %% common used
def t_one_item(params: Params) -> Tuple[str, int]:
    """{{道具}}{{材料消耗}}{{素材}}"""
    if 'name' in params:  # {{素材
        return params.get('name'), params.get('count', default=1, cast=int)
    else:  # {{道具, {{材料消耗
        # 种火, num_text=职阶名
        num_text = params.get('2', '1')
        num = int(num_text) if num_text.isdigit() else 1
        return params.get('1'), num


# %% servant
kUnavailableSvt = (83, 149, 151, 152, 168, 240)


def t_base_info(params: Params, instance: ServantBaseInfo = None):
    """{{基础数值}}"""
    if instance is None:
        instance = ServantBaseInfo()
    instance._no = params.get('序号', cast=int)
    instance.rarity = params.get('稀有度', cast=int)
    instance.rarity2 = {1: 3, 107: 2}.get(instance._no, instance.rarity)  # for 玛修&小安
    instance.obtain = params.get('获取途径', '无法召唤')

    instance.name = params.get('中文名', default=params.get('姓名'))
    instance.nameJp = params.get('日文名')
    instance.nameEn = params.get('英文名')
    for i in range(11):
        suffix = '战斗名' if i == 0 else '卡面名' if i == 1 else f'名{i}'
        list_append(instance.namesOther, params.get('中文' + suffix, tags=kAllTags))
        list_append(instance.namesJpOther, params.get('日文' + suffix, tags=kAllTags))
        list_append(instance.namesEnOther, params.get('英文' + suffix, tags=kAllTags))
    list_append(instance.namesOther, params.get('简称', tags=kAllTags))
    list_append(instance.namesJpOther, params.get('日文简称', tags=kAllTags))
    list_append(instance.namesEnOther, params.get('英文简称', tags=kAllTags))

    list_extend(instance.nicknames, re.split(r'[,，\s]', params.get('昵称', '', tags=kAllTags)))

    for suffix in ('', '2', '3', '新'):
        list_append(instance.cv, params.get('声优' + suffix, tags=kAllTags))
    instance.illustrator = params.get('画师')

    for suffix in (1, 12, 2, 22):
        list_append(instance.alignments, params.get(f'属性{suffix}'))
    instance.alignments.extend([trim(i) for i in params.get('属性', '').split('·') if trim(i)])

    instance.gender = params.get('性别')
    instance.height = params.get('身高')
    instance.weight = params.get('体重')
    instance.attribute = params.get('隐藏属性')
    instance.className = params.get('职阶')
    instance.ability = {
        'strength': params.get('筋力'),
        'endurance': params.get('耐久'),
        'agility': params.get('敏捷'),
        'mana': params.get('魔力'),
        'luck': params.get('幸运'),
        'np': params.get('宝具')
    }
    instance.atkMin = params.get('基础ATK', -1, int)
    instance.atkMax = params.get('满级ATK', -1, int)
    instance.atk90 = params.get('90级ATK', -1, int)
    instance.atk100 = params.get('100级ATK', -1, int)
    instance.hpMin = params.get('基础HP', -1, int)
    instance.hpMax = params.get('满级HP', -1, int)
    instance.hp90 = params.get('90级HP', -1, int)
    instance.hp100 = params.get('100级HP', -1, int)
    for i in range(14):
        list_append(instance.traits, params.get('特性' if i == 0 else f'特性{i}'))
    instance.isHumanoid = params.get('人型') in ('是', '1')
    instance.isWeakToEA = params.get('被EA特供') in ('是', '1')
    instance.isHumanoid = params.get('天地拟似') in ('是', '1')

    if '立绘tabber' in params:
        for illust_name, content in split_tabber(params.get('立绘tabber')):
            illust_file = split_file_link(content)
            instance.illust[illust_name] = illust_file
    else:
        for i in range(1, 11):
            illust_name = params.get(f'立绘{i}', '')
            illust_file = params.get(f'文件{i}', '')
            if illust_name or illust_file:
                instance.illust[illust_name] = illust_file + '.png'

    if instance._no not in kUnavailableSvt:
        for i in '一二三四五':
            instance.cards.append(params.get(f'第{i}张卡'))
        for illust_name, prefix in {'quick': 'Q卡', 'arts': 'A卡', 'buster': 'B卡', 'extra': 'EX卡', 'np': '宝具',
                                    'defense': '受击'}.items():
            # info.npRate[k] = int(float(v.strip('%'))*100)
            instance.npRate[illust_name] = params.get(prefix + 'np率')
        for illust_name, prefix in {'quick': 'Q卡', 'arts': 'A卡', 'buster': 'B卡', 'extra': 'EX卡', 'np': '宝具卡'}.items():
            instance.cardHits[illust_name] = params.get(prefix + 'hit数', 0, int)
            dmg = params.get(prefix + '伤害分布', '').split(',')
            instance.cardHitsDamage = [int(s) for s in dmg if s.strip()]
        instance.starRate = params.get('出星率')
        instance.deathRate = params.get('即死率')
        instance.criticalRate = params.get('暴击权重')
    return instance


def t_treasure_device(params: Params, instance: TreasureDevice = None):
    """{{宝具}}"""
    if instance is None:
        instance = TreasureDevice()
    instance.name = params.get('中文名')
    instance.nameJp = params.get('日文名')
    instance.upperName = params.get('国服上标')
    instance.upperNameJp = params.get('日服上标')
    instance.color = params.get('卡色')
    instance.category = params.get('类型')
    instance.rank = params.get('阶级')
    instance.typeText = params.get('种类')
    assert instance.color in ('Quick', 'Arts', 'Buster') and instance.category in ('辅助', '单体', '全体'), instance
    for i in 'ABCDEFGH':
        effect = Effect()
        effect.description = params.get('效果' + i)
        if effect.description is None:
            break
        for j in range(1, 6):
            value = params.get(f'数值{i}{j}')
            if value is None:
                break
            effect.lvData.append(value)
        assert len(effect.lvData) in (1, 5), effect.lvData
        instance.effects.append(effect)
    return instance


def t_active_skill(params: Params, instance: Skill = None):
    """{{持有技能}}"""
    # {{持有技能|技能图标|技能名称|技能名称(日文)|充能时间（a → b）
    # |技能效果1|Lv.1数值|Lv.2数值|Lv.3数值|Lv.4数值|Lv.5数值|Lv.6数值|Lv.7数值|Lv.8数值|Lv.9数值|Lv.10数值
    # |<技能效果2>|<Lv.1数值>|...|<Lv.10数值>}}
    if instance is None:
        instance = Skill()
    instance.icon = params.get('1') + '.png'
    instance.cd = params.get('4', cast=int)
    name_rank = params.get('2', tags=kAllTags)
    name_rank_jp = params.get('3', tags=kAllTags)
    cn_splits = name_rank.rsplit(maxsplit=1)
    jp_splits = name_rank_jp.rsplit(maxsplit=1)
    assert len(cn_splits) == len(jp_splits), (cn_splits, jp_splits)
    if len(cn_splits) == 2:
        name_cn, rank_cn = cn_splits
        name_jp, rank_jp = jp_splits
        assert rank_cn == rank_jp and re.match(r'^([A-E]|EX){1,2}[+\-]*$', rank_cn), (rank_cn, rank_jp)
        instance.name, instance.nameJp = name_cn, name_jp
        instance.rank = rank_cn
    else:
        logger.info(f'Active skill - no skill rank: {cn_splits}, {jp_splits}')
        instance.name, instance.nameJp = cn_splits[0], jp_splits[0]
        instance.rank = ''  # or None?
    offset = 5  # first effect description is at "5"(str)
    while True:
        des = params.get(str(offset), tags=kAllTags)
        if not des:
            break
        effect = Effect()
        effect.description = des
        for i in range(1, 11):
            value = params.get(str(offset + i))
            if value is None:
                break
            else:
                effect.lvData.append(value)
        assert len(effect.lvData) in (1, 10), effect
        instance.effects.append(effect)
        offset += 11
    return instance


def t_passive_skill(params: Params):
    """{{职阶技能}}"""
    # {{职阶技能|  1  |  2  |  3  |   4   |   5   |   6   | 7~12 | 13~21 | }}
    # {{职阶技能|icon1|name1|rank1|effect1| skill2~6}}
    instance = []
    offset = 0
    while True:
        skill = Skill()
        skill.set_ignored(['state', 'nameJp', 'cd'])
        skill.icon = params.get(str(offset + 1))
        if skill.icon is None:
            break
        skill.icon += '.png'
        skill.name = params.get(str(offset + 2))
        skill.rank = params.get(str(offset + 3))
        effect_texts = re.split(r'[＆&+]', params.get(str(offset + 4), tags=kAllTags))
        for text in effect_texts:
            description, value = re.findall(r'^(.*?)(?:\(([\d.]+%?)\))?$', text.strip())[0]
            skill.effects.append(Effect(description=description, lvData=[value]))
        instance.append(skill)
        offset += 4
    return instance


def t_ascension_cost(params: Params):
    """{{灵基再临素材}}"""
    instance: List[Dict[str, int]] = []
    if not params:
        # 玛修 don't need ascension items
        return instance
    qp_cost = [
        [15000, 10000, 15000, 30000, 50000, 100000],  # 0->1
        [45000, 30000, 45000, 100000, 150000, 300000],  # 1->2
        [150000, 90000, 150000, 300000, 500000, 1000000],  # 2->3
        [450000, 300000, 450000, 900000, 1500000, 3000000],  # 3->4
    ]
    rarity = params.get('稀有度', cast=int)
    for i in range(4):
        lv_cost = p_items(params.get(f'{i}->{i + 1}'))
        # for template in mwp.parse(text).filter_templates('{{材料消耗'):
        #     item, num = t_one_item(parse_template(template))
        #     lv_cost[item] = num
        lv_cost['QP'] = qp_cost[i][rarity]
        instance.append(lv_cost)
    return instance


def t_skill_cost(params: Params):
    """{{技能升级素材}}"""
    instance: List[Dict[str, int]] = []
    qp_cost = [
        [2, 1, 2, 5, 10, 20],  # 1->2
        [4, 2, 4, 10, 20, 40],  # 2->3
        [12, 6, 12, 30, 60, 120],  # 3->4
        [16, 8, 16, 40, 80, 160],  # 4->5
        [40, 20, 40, 100, 200, 400],  # 5->6
        [50, 25, 50, 125, 250, 500],  # 6->7
        [100, 50, 100, 250, 500, 1000],  # 7->8
        [120, 60, 120, 300, 600, 1200],  # 8->9
        [200, 100, 200, 500, 1000, 2000],  # 9->10
    ]
    rarity = params.get('稀有度', cast=int)
    for i in range(9):
        text = params.get(f'{i + 1}->{i + 2}')
        lv_cost = p_items(text)
        # for template in mwp.parse(text).filter_templates('{{材料消耗'):
        #     item, num = t_one_item(parse_template(template))
        #     lv_cost[item] = num
        lv_cost['QP'] = qp_cost[i][rarity] * 10000
        instance.append(lv_cost)
    return instance


def t_dress_cost(params: Params):
    """{{灵衣开放素材}}"""
    instance: List[Dict[str, int]] = []
    names_cn, names_jp = [], []
    no = 1
    while True:
        suffix = '' if no == 1 else str(no)
        two_name = params.get('灵衣名称' + suffix, tags=kAllTags)
        if two_name is None:
            break
        splits = two_name.split('\n')
        assert len(splits) % 2 == 0, splits
        center = len(splits) // 2
        names_cn.append(''.join(splits[0:center]))
        names_jp.append(''.join(splits[center:]))
        items = p_items(params.get('素材' + suffix))
        items['QP'] = 3000000
        instance.append(items)
        no += 1
    return instance, names_cn, names_jp


def t_profiles(params: Params):
    """{{个人资料}}"""
    instance: List[SvtProfileData] = []
    for i in range(8):
        profile = SvtProfileData()
        key = '详情' if i == 0 else f'资料{i}'
        profile.title = '角色详情' if i == 0 else f'个人资料{i}'
        profile.description = params.get(key, tags=kAllTags)
        profile.descriptionJp = params.get(key + '日文', tags=kAllTags)
        condition = params.get(key + '条件', tags=kAllTags)
        if condition and not re.match(f'羁绊达到Lv\\.{i}[后时]?开放', condition):
            profile.condition = params.get(key + '条件', tags=kAllTags)
        if profile.descriptionJp:
            instance.append(profile)
    return instance


def t_fool_profiles(params: Params):
    """{{愚人节资料}}"""
    instance: List[SvtProfileData] = []
    for suffix in ('', '2'):
        profile = SvtProfileData()
        profile.title = '愚人节资料' + suffix
        profile.description = params.get('中文' + suffix, tags=kAllTags)
        profile.descriptionJp = params.get('日文' + suffix, tags=kAllTags)
        profile.condition = None
        if profile.descriptionJp:
            instance.append(profile)
    return instance


def t_voice_table(params: Params, instance: VoiceTable = None):
    """{{#invoke:VoiceTable}}"""
    if instance is None:
        instance = VoiceTable()
    instance.section = params.get('表格标题')
    for i in range(1, 60):  # mc: 1~50
        record = VoiceRecord()
        record.title = params.get(f'标题{i}')
        record.text = params.get(f'中文{i}')
        record.textJp = params.get(f'日文{i}')
        record.condition = params.get(f'条件{i}')
        record.file = params.get(f'语音{i}')
        if record.textJp:
            instance.table.append(record)
    return instance


# %% craft essential & command code
def t_craft_essential(params: Params, instance: CraftEssential = None):
    """{{概念礼装}}"""
    if instance is None:
        instance = CraftEssential()
    instance.rarity = params.get('稀有度', cast=int)
    instance.no = params.get('礼装id', cast=int)
    instance.name = params.get('名称')
    instance.nameJp = params.get('日文名称')
    instance.mcLink = params.get('链接名')
    instance.illust = params.get('图片名', instance.name) + '.png'
    for i in range(1, 9):
        key = '画师' if i == 1 else f'画师{i}'
        list_append(instance.illustrators, params.get(key))
    instance.cost = params.get('cost', cast=int)
    hp = params.get('HP')
    if '/' in hp:
        instance.hpMin, instance.hpMax = map(int, hp.split('/'))
    else:
        instance.hpMin = instance.hpMax = int(hp)
    atk = params.get('ATK')
    if '/' in atk:
        instance.atkMin, instance.atkMax = map(int, atk.split('/'))
    else:
        instance.atkMin = instance.atkMax = int(atk)

    def handle_skill_text(text: str):
        text = text.replace('（', '(').replace('）', ')')
        text = re.sub(r'^(日服|国服)[:：]', '', text)
        text = re.sub(r'{{道具(.*?)}}', '', text)
        text = remove_tag(text)
        text = re.sub(r'[^ ]\[最大解放\]]', ' [最大解放]', text)
        text = re.sub(r'提供(\d*)点概念礼装经验值?', '', text)
        text = text.replace('无效果', '')
        text = re.sub(r'{{(中国|日本)}}', r'[\1]', text)
        return text.strip()

    instance.skillIcon = params.get('图标') + '.png'
    skill_text = params.get('持有技能', tags=kAllTags)
    if '最大解放' in skill_text or ('日服' in skill_text and '国服' in skill_text):
        splits = re.split(r' *\n+ *', skill_text)
        if '日服' in skill_text and '国服' in skill_text:
            splits = splits[0:len(splits) // 2]
        if len(splits) % 2 != 0 and splits[-1] == '[最大解放]':
            last = splits.pop()
            splits[-1] = splits[-1] + ' ' + last
        assert len(splits) == 2, splits
        instance.skill = handle_skill_text(splits[0])
        instance.skillMax = handle_skill_text(splits[1])
    else:
        instance.skill = skill_text

    for i in range(0, 5):
        suffix = '' if i == 0 else str(i)
        if f'活动技能{suffix}' in params:
            instance.eventIcons.append(params.get('活动图标' + suffix, '未知技能') + '.png')
            event_skill = handle_skill_text(params.get('活动技能' + suffix))
            instance.eventSkills.append(event_skill)

    instance.description = params.get('解说', tags=kAllTags)
    instance.descriptionJp = params.get('日文解说', tags=kAllTags)
    instance.categoryText = params.get('礼装分类')

    instance.characters = []
    list_append(instance.characters, params.get('出场角色'))
    for i in range(1, 26):
        list_append(instance.characters, params.get(str(i)))
    return instance


def t_cmd_code(params: Params, instance: CmdCode = None):
    """{{指令纹章}}"""
    if instance is None:
        instance = CmdCode()
    instance.rarity = params.get('稀有度', cast=int)
    instance.no = params.get('纹章id', cast=int)
    instance.name = params.get('名称')
    instance.nameJp = params.get('日文名称')
    instance.mcLink = params.get('链接名')
    instance.illust = params.get('图片名', instance.name) + '.png'
    for i in range(1, 9):
        key = '画师' if i == 1 else f'画师{i}'
        list_append(instance.illustrators, params.get(key))

    instance.skillIcon = params.get('图标') + '.png'
    instance.skill = params.get('持有技能', tags=kAllTags)
    instance.description = params.get('解说', tags=kAllTags)
    instance.descriptionJp = params.get('日文解说', tags=kAllTags)
    instance.categoryText = params.get('纹章分类')
    instance.characters = []
    list_append(instance.characters, params.get('出场角色'))
    for i in range(1, 26):
        list_append(instance.characters, params.get(str(i)))
    return instance


# %% event, quest
def t_quest(params: Params, instance: Quest = None):
    """{{关卡配置}}"""
    # at most 8 battles 7 waves 21 enemies
    # for who call this function, branch quests may be wrapped in <tabber> check the redundant "name"
    if instance is None:
        instance = Quest()
    instance.name = params.get('名称cn') or params.get('标题')
    instance.nameJp = params.get('名称jp')
    instance.level = params.get('推荐等级', -1, int)
    instance.bondPoint = params.get('羁绊', 0, int)
    instance.experience = params.get('经验', 0, int)
    instance.qp = params.get('QP', 0, int)
    instance.isFree = params.get('可重复', 0, int) in (1, 3)
    instance.hasChoice = '{{分支关卡' in ''.join(params.values())
    for i in '一二三四五六七八':
        ap = params.get(f'{i}AP', -1, int)
        if ap < 0:
            continue
        battle = Battle()
        battle.ap = ap
        battle.place = params.get(f'{i}地点cn') or params.get(f'{i}地点')
        battle.placeJp = params.get(f'{i}地点jp')

        for j in range(7):
            wave: List[Enemy] = []
            for k in range(21):
                enemy_text = params.get(f'{i}{j + 1}敌人{k + 1}')
                if not enemy_text:
                    continue
                if '关卡分支' in enemy_text:
                    enemy_text = parse_template(enemy_text, '^{{关卡分支')['1']
                enemy = t_enemy(parse_template(enemy_text, '^{{敌人'))
                wave.append(enemy)
            while len(wave) > 0 and len(wave[-1].name) == 0:
                wave.pop()
            battle.enemies.append(wave)
        while len(battle.enemies) > 0 and len(battle.enemies[-1]) == 0:
            battle.enemies.pop()

        drops_text = params.get(f'{i}战利品', '')
        if '关卡分支' in drops_text:
            drops_text = parse_template(drops_text, '^{{关卡分支')['1']
        battle.drops = p_items(drops_text)
        instance.battles.append(battle)
    instance.rewards = p_items(params.get('通关奖励', ''))
    return instance


def t_enemy(params: Params, instance: Enemy = None):
    """{{敌人123}}"""
    # {{敌人1|种类|显示名|职阶|Lv|HP|敌人3|种类2|显示名2|职阶2|Lv2|HP2}}
    #     0----1-----2------3---4--5---6
    # 关卡分支-只选第一个
    if instance is None:
        instance = Enemy()
    offset = 0
    while True:
        name = params.get(str(offset + 1), tags=True)
        if not name:
            break
        instance.name.append(name)
        instance.shownName.append(params.get(str(offset + 2), tags=True))
        instance.className.append(params.get(str(offset + 3), ''))
        instance.rank.append(params.get(str(offset + 4), 0, int))
        instance.hp.append(params.get(str(offset + 5), 0, int))
        offset += 6
    return instance


def t_event_shop_list(params: Params):
    """{{#invoke:EventShopList}}"""
    results: Dict[str, int] = {}
    if not params:
        return results
    data_str = params.get('data').strip()
    item_list = data_str.split(sep='\n')
    for row in item_list:
        # 0:check，1:name，2:num, 3:price，4:bg_color
        datum_table = row.split(sep=';;')
        name, num = datum_table[1], datum_table[2]
        item, num1 = t_one_item(parse_template(name, '^{{道具'))
        if item and num.isdigit():
            results[item] = int(num) * num1
    return results


def t_event_point(params: Params):
    """{{活动点数}}"""
    result: Dict[str, int] = {}
    if not params:
        return result
    names: Dict[int, str] = {}
    for key, value in params.items():
        if key.startswith('name'):
            names[int(key[4:])] = value.strip()
    assert len(names) == max(names.keys())
    no = 1
    while True:
        if str(no) not in params:
            break
        name_key = int(params.get(f'{no}tp'))
        name = names[name_key]
        num_str = params.get(f'{no}num', '1').strip()
        if num_str.isdigit():
            num = int(num_str)
            result[name] = result.get(name, 0) + num
        no += 1
    return result


def t_event_task(params: Params):
    """{{活动任务}}"""
    result: Dict[str, int] = {}
    if not params:
        return result
    for i in range(1, 101):
        reward = params.get(f'jl{i}')
        add_dict(result, p_items(reward))
    return result


def t_event_lottery(params: Params):
    """{{奖品奖池}}"""
    result: Dict[str, int] = {}
    if not params:
        return result
    for i in range(1, 13):
        item = params.get(f'道具{i}')
        if item:
            result[item] = params.get(f'道具{i}次数', cast=int)
    for gem in ('秘石', '魔石', '辉石', '金像', '银像'):
        num = params.get(gem + '次数', 0, int)
        if num > 0:
            for i in range(1, 8):
                class_name = params.get(f'{gem}{i}')
                if class_name:
                    if '石' in gem:
                        item = f'{class_name}之{gem}'
                    else:
                        item = f'{class_name}阶{gem}'
                    result[item] = num
    qp_num = 0
    for i in range(1, 7):
        qp_per = params.get(f'QP{i}', 0, int)
        if qp_per:
            qp_num += qp_per * params.get(f'QP{i}次数', cast=int)
    result['QP'] = qp_num
    return result
