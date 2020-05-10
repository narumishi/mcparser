from .datatypes import *
from .util import *


def p_craft_essential(params: Params, instance: CraftEssential = None):
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
