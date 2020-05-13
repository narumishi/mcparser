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


def p_cmd_code(params: Params, instance: CmdCode = None):
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


def p_quest(params: Params, instance: Quest = None):
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
                enemy = p_enemy(parse_template(enemy_text, '^{{敌人'))
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


def check_unique_quest(quests: List[Quest], in_place=True):
    if not in_place:
        quests = [q for q in quests]
    names = []
    for i, quest in enumerate(quests):
        if quest.name in names:
            quests.pop(i)
            logger.info(f'redundant quest: {quest.chapter}-{quest.name}')
    return quests


def p_enemy(params: Params, instance: Enemy = None):
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
