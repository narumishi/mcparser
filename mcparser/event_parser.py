from .base_parser import *
from .utils.util_other import *  # noqas


class EventParser:
    """Same quest block, e.g. all free quests of one event or all story quests of one main record"""

    def __init__(self, fp: str):
        super().__init__()
        # src_data: key - event_name, value - event_info(wikitext of home/quests/subpages)
        self.src_fp = fp
        self.src_data: Dict[str, Any] = load_json(fp)
        self.data = Events()

    @count_time
    def parse(self, event_types: List[str] = None, _range: Iterable[int] = None, workers=kWorkersNum):
        executor = ThreadPoolExecutor(max_workers=workers)
        if event_types is None:
            event_types = ['MainStory', 'Event']
        for _event_type in event_types:
            event_src_data = self.src_data[_event_type]
            all_keys = list(event_src_data.keys())
            valid_keys = [v for i, v in enumerate(all_keys) if _range is None or i in _range]
            finished, all_num = [], len(valid_keys)
            if _event_type == 'MainStory':
                events = self.data.mainRecords
                tasks = [executor.submit(self._parse_main_story, key) for key in valid_keys]
            else:
                events = self.data.limitEvents
                tasks = [executor.submit(self._parse_limit_event, key) for key in valid_keys]
            for future in as_completed(tasks):
                result = future.result()
                if result is not None:
                    key, value = result
                    events[key] = value
                    finished.append(key)
                    logger.debug(f'======= {len(finished)}/{all_num}: "{key}" finished ========')
                else:
                    finished.append(None)
                    logger.warning(f'####### {len(finished)}/{all_num}: went wrong #######')
            error_keys = [k for k in all_keys if k not in finished]
            logger.info(f'All {all_num} wikitext downloaded. {len(error_keys)} errors: {error_keys}')
        self.data.mainRecords = sort_dict(self.data.mainRecords, lambda k, v: v.startTimeJp)
        self.data.limitEvents = sort_dict(self.data.limitEvents, lambda k, v: v.startTimeJp)
        return self.data

    @catch_exception
    def _parse_main_story(self, key: str) -> Tuple[str, MainRecord]:
        src_data = self.src_data['MainStory'][key]
        event = MainRecord()

        home_wikitext = mwp.parse(src_data['event_page'])
        quest_wikitext = mwp.parse(src_data['quest_page'])

        params = parse_template(home_wikitext, '^{{活动信息')
        event.name = src_data['name']
        if event.name.startswith('序'):
            event.chapter, event.title = event.name, ''
        elif event.name.startswith('Lost'):
            splits = event.name.split(' ')
            event.chapter, event.title = ' '.join(splits[0:2]), ' '.join(splits[2:])
        else:
            event.chapter, event.title = event.name.split(maxsplit=1)

        self._parse_event_base(params, event)
        main_quests = quest_wikitext.get_sections(matches='主线关卡')
        if main_quests:
            event.rewards, event.drops = p_quest_reward_drop(main_quests[0])
        return key, event

    @catch_exception
    def _parse_limit_event(self, key: str) -> Tuple[str, LimitEvent]:
        """100task, event_point, """
        src_data = self.src_data['Event'][key]
        event = LimitEvent()

        home_wikitext = mwp.parse(src_data['event_page'])
        quest_wikitext = mwp.parse(src_data['quest_page'])

        params_event_info = parse_template(home_wikitext, '^{{活动信息')
        event.name = src_data['name']
        self._parse_event_base(params_event_info, event)
        event.itemShop = p_event_shop(home_wikitext)
        event.itemTask = p_event_task(parse_template(home_wikitext, '^{{活动任务'))
        event.itemPoint = p_event_point(parse_template(home_wikitext, '^{{活动点数'))
        # 无限池：
        pond_templates = home_wikitext.filter_templates(matches='^{{奖品奖池')
        if pond_templates:
            event.lottery = p_event_pond(parse_template(pond_templates[-1]))

        # quests drop & rewards
        # add 高难 -> repeatable ? rewards : rewards+drops
        hard_quest_sections = quest_wikitext.get_sections(matches='高难度关卡')
        if hard_quest_sections:
            reward_drop = p_quest_reward_drop(hard_quest_sections[0], False)
            add_dict(event.itemDropReward, *reward_drop)
            quest_wikitext.remove(hard_quest_sections[0])
        reward_drop = p_quest_reward_drop(quest_wikitext)
        add_dict(event.itemDropReward, *reward_drop)
        add_dict(event.items, event.itemShop, event.itemTask, event.itemPoint, event.itemDropReward)

        # special: amazon, hunting, lottery,
        if '亚马逊' in event.name:
            subpages = ['关卡配置/亚马逊仓库', '关卡配置/阿耳忒弥斯神殿塔', '关卡配置/极·阿耳忒弥斯神殿塔']
            updated = False
            for page in subpages:
                if page not in src_data['subpages']:
                    src_data['subpages'][page] = get_site_page(page)
                    updated = True
                subpage_wikitext = mwp.parse(src_data['subpages'][page])
                reward_drop = p_quest_reward_drop(subpage_wikitext)
                add_dict(event.itemDropReward, *reward_drop)
            if updated:
                dump_json(self.src_data, self.src_fp)
        elif '狩猎' in event.name:
            # data from 效率剧场
            hunting_data = {
                5: [(1, '凶骨', 16.1), (2, '宵泣之铁桩', 21.2), (3, '禁断书页', 32.4), (4, '血之泪石', 76.5),
                    (4, '英雄之证', 26.7), (5, '陨蹄铁', 31.8), (6, '龙之逆鳞', 114.9), (6, '极光之钢', 69.6)],
                6: [(1, '凶骨', 16.0), (2, '大骑士勋章', 39.7), (3, '凤凰羽毛', 40.4), (5, '无间齿轮', 44.9),
                    (4, '魔术髓液', 41.3), (5, '封魔之灯', 68.9), (5, '振荡火药', 40.8), (6, '咒兽胆石', 98.6),
                    (6, '祸罪的箭镞', 67.6)],
                7: [(1, '凶骨', 16.0), (2, '八连双晶', 35.0), (3, '凤凰羽毛', 40.2), (4, '闲古铃', 54.8),
                    (4, '宵泣之铁桩', 36), (5, '战马的幼角', 66.9), (5, '永远结冰', 57.6), (6, '智慧的圣甲虫', 113.2),
                    (6, '枯淡勾玉', 56.8)],
            }
            for i, item_list in hunting_data.items():
                if f'狩猎关卡 第{i}弹' == event.name:
                    for day, item, drop_rate in item_list:
                        event.extra[item] = f'Day {day} 参考掉率: {drop_rate} AP'
        # {{奖池 ->{{奖品奖池
        if 'BATTLE IN NEWYORK 2019' in event.name:
            event.extra = {'蛮神心脏': '正赛票本: 193.5 AP', '闲古铃': '正赛票本: 110.5 AP',
                           '晓光炉心': 'S正赛票本: 161.8 AP', '人工生命体幼体': 'S正赛票本: 112.6 AP',
                           '九十九镜': '决赛票本: 198.4 AP', '鬼魂提灯': '决赛票本: 110.3 AP'}
        elif '南丁格尔' in event.name:
            event.extra = {'混沌之爪': '兑换券', '凤凰羽毛': '兑换券', '巨人的戒指': '兑换券',
                           '蛮神心脏': '票本: 197.0 AP', '极光之钢': '票本: 109.7 AP'}
        return key, event

    @staticmethod
    def _parse_event_base(params: Params, event: EventBase):
        event.mcLink = f'https://fgo.wiki/w/{event.name}'
        event.nameJp = params.get('名称jp')
        event.startTimeJp = params.get('开始时间jp') or params.get('时间预估jp')
        event.endTimeJp = params.get('结束时间jp') or params.get('结束预估jp')
        event.startTimeCn = params.get('开始时间cn') or params.get('时间预估cn')
        event.endTimeCn = params.get('结束时间cn') or params.get('结束预估cn')
        banner_image = get_site_page(params.get('标题图文件名cn') or params.get('标题图文件名jp'), True)
        if banner_image.imageinfo != {}:
            event.bannerUrl = banner_image.imageinfo['url']
        event.grail = params.get('圣杯', 0, int)
        event.grail2crystal = params.get('圣杯转结晶', 0, int)
        event.crystal = params.get('传承结晶', 0, int) - event.grail2crystal

    def dump(self, fp: str):
        dump_json(self.data.to_json(), fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')


# %% templates
def p_event_shop_one_item(params: Params):
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
        item, num1 = p_one_item(parse_template(name, '^{{道具'))
        if item and num.isdigit():
            results[item] = int(num) * num1
    return results


def p_event_shop(code: Wikicode):
    result: Dict[str, int] = {}
    for template in code.filter_templates(matches='^{{#invoke:EventShopList'):
        params = parse_template(template)
        add_dict(result, p_event_shop_one_item(params))
    return result


def p_event_point(params: Params):
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


def p_event_task(params: Params):
    """{{活动任务}}"""
    result: Dict[str, int] = {}
    if not params:
        return result
    for i in range(1, 101):
        reward = params.get(f'jl{i}')
        add_dict(result, p_items(reward))
    return result


def p_event_pond(params: Params):
    """{{奖品奖池}}"""
    # 尼禄祭再临 ～2017 Autumn～
    # BATTLE IN NEWYORK 2018
    # 圣诞节2018 Holy·Samba·Night ～降雪遗迹与少女骑士～
    # 复刻：第二代是Alter亲 ～2016圣诞节～ 轻量版
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
