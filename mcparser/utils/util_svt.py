"""Servant related template parser"""
from .datatypes import *
from .util import *  # noqas

kUnavailableSvt = (83, 149, 151, 152, 168, 240)


def p_base_info(params: Params, instance: ServantBaseInfo = None):
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

    list_extend(instance.nicknames, re.split(r'[,，\s]', remove_tag(params.get('昵称', ''))))

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
            instance.illust.append(GameIcon(filename=illust_name, url=config.site.images[illust_file].imageinfo['url']))
    else:
        for i in range(1, 11):
            illust_name = params.get(f'立绘{i}', '')
            illust_file = params.get(f'文件{i}', '')
            if illust_name or illust_file:
                illust_file = illust_file + '.png'
                instance.illust.append(
                    GameIcon(filename=illust_name, url=config.site.images[illust_file].imageinfo['url']))

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


def p_treasure_device(params: Params, instance: TreasureDevice = None):
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
        effect.target = params.get('对象' + i)
        if not effect.target:
            last_target = instance.effects[-1].target if instance.effects else None
            effect.target = find_effect_target(effect.description, last_target)
        for j in range(1, 6):
            value = params.get(f'数值{i}{j}')
            if value is None:
                break
            effect.lvData.append(value)
        assert len(effect.lvData) in (1, 5), effect.lvData
        instance.effects.append(effect)
    return instance


def p_active_skill(params: Params, instance: Skill = None):
    # {{持有技能|技能图标|技能名称|技能名称(日文)|充能时间（a → b）
    # |技能效果1|Lv.1数值|Lv.2数值|Lv.3数值|Lv.4数值|Lv.5数值|Lv.6数值|Lv.7数值|Lv.8数值|Lv.9数值|Lv.10数值
    # |<技能效果2>|<Lv.1数值>|...|<Lv.10数值>}}
    if instance is None:
        instance = Skill()
    instance.icon = params.get('1') + '.png'
    instance.cd = params.get('4', cast=int)
    name_rank = remove_tag(params.get('2'))
    name_rank_jp = remove_tag(params.get('3'))
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
        print('No skill rank: ', cn_splits, jp_splits)
        instance.name, instance.nameJp = cn_splits[0], jp_splits[0]
        instance.rank = ''  # or None?
    offset = 5  # first effect description is at "5"(str)
    while True:
        des = params.get(str(offset))
        if not des:
            break
        effect = Effect()
        effect.description = remove_tag(des)
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
