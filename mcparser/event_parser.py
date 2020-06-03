import calendar

from .item_parser import ItemParser
from .utils.templates import *


class EventParser:
    """Same quest block, e.g. all free quests of one event or all story quests of one main record"""

    def __init__(self, src_fp: str, item_parser: ItemParser = None):
        super().__init__()
        # src_data: key - event_name, value - event_info(wikitext of home/quests/subpages)
        self.src_data: Dict[str, Any] = load_json(src_fp)
        self.data = Events()
        self._item_parser = item_parser

    @count_time
    def parse(self, event_types: List[str] = None, _range: Iterable[int] = None, workers: int = None):
        executor = ThreadPoolExecutor(max_workers=workers or config.default_workers)
        if event_types is None:
            event_types = ['MainStory', 'Event']
        for _event_type in event_types:
            event_src_data = self.src_data[_event_type]
            all_keys = [v for i, v in enumerate(event_src_data.keys()) if _range is None or i in _range]
            success_keys, error_keys = [], []
            finish_num, all_num = 0, len(all_keys)
            if _event_type == 'MainStory':
                events = self.data.mainRecords
                tasks = [executor.submit(self._parse_main_story, key) for key in all_keys]
            else:
                events = self.data.limitEvents
                tasks = [executor.submit(self._parse_limit_event, key) for key in all_keys]
            for future in as_completed(tasks):
                finish_num += 1
                result = future.result()
                if result is None:
                    logger.warning(f'======= parse {_event_type} event {finish_num}/{all_num} FAILED ========')
                else:
                    key, value = result
                    events[key] = value
                    success_keys.append(key)
                    logger.debug(f'======= parse {_event_type} event {finish_num}/{all_num} success: "{key}"')
            error_keys = [k for k in all_keys if k not in success_keys]
            logger.info(f'All {all_num} {_event_type} parsed. {len(error_keys)} errors: {error_keys}',
                        extra=color_extra('red') if error_keys else None)

        self.data.mainRecords = sort_dict(self.data.mainRecords, lambda k, v: v.startTimeJp)
        self.data.limitEvents = sort_dict(self.data.limitEvents, lambda k, v: v.startTimeJp)
        self._parse_tickets()
        return self.data

    @catch_exception
    def _parse_main_story(self, key: str) -> MapEntry[str, MainRecord]:
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

        t_event_info(params, event)
        main_quests = quest_wikitext.get_sections(matches='主线关卡')
        if main_quests:
            event.rewards, event.drops = p_quest_reward_drop(main_quests[0])
        # check valid items
        self.check_valid_item(event.drops)
        self.check_valid_item(event.rewards)
        return key, event

    @catch_exception
    def _parse_limit_event(self, key: str) -> MapEntry[str, LimitEvent]:
        """100task, event_point, """
        event_src_data = self.src_data['Event'][key]
        event = LimitEvent()

        home_wikitext = mwp.parse(event_src_data['event_page'])
        quest_wikitext = mwp.parse(event_src_data['quest_page'])

        params_event_info = parse_template(home_wikitext, '^{{活动信息')
        event.name = event_src_data['name']
        t_event_info(params_event_info, event)

        # ====== shop/task/point ======
        event.itemShop = p_event_shop(home_wikitext)
        event.itemTask = t_event_task(parse_template(home_wikitext, '^{{活动任务'))
        event.itemPoint = t_event_point(parse_template(home_wikitext, '^{{活动点数'))

        # ====== quests drop & rewards ======
        # merge sub pages into main quest page
        for page in event_src_data['sub_pages']:
            quest_wikitext.append(page)
        # not 高难 or repeatable ? rewards : rewards+drops
        hard_quest_sections = quest_wikitext.get_sections(matches='高难度关卡')
        if hard_quest_sections:
            reward_drop = p_quest_reward_drop(hard_quest_sections[0], False)
            add_dict(event.itemRewardDrop, *reward_drop)
            quest_wikitext.remove(hard_quest_sections[0])
        reward_drop = p_quest_reward_drop(quest_wikitext)
        add_dict(event.itemRewardDrop, *reward_drop)

        add_dict(event.items, event.itemShop, event.itemTask, event.itemPoint, event.itemRewardDrop)

        # ====== 无限池lottery ======
        lottery_templates = home_wikitext.filter_templates(matches='^{{奖品奖池')
        if lottery_templates:
            if '赝作' in event.name:
                lottery_num = len(lottery_templates)
                assert lottery_num % 2 == 0
                event.lottery = t_event_lottery(parse_template(lottery_templates[lottery_num // 2 - 1]))
                t_event_lottery(parse_template(lottery_templates[-1]), event.lottery)
            else:
                event.lottery = t_event_lottery(parse_template(lottery_templates[-1]))

        # ====== extra ======
        # hunting
        if '狩猎' in event.name:
            # data from 效率剧场
            hunting_data = {
                5: [(1, '凶骨', 16.1), (2, '宵泣之铁桩', 21.2), (3, '禁断书页', 32.4), (4, '血之泪石', 76.5),
                    (4, '英雄之证', 26.7), (5, '陨蹄铁', 31.8), (6, '龙之逆鳞', 114.9), (6, '极光之钢', 69.6)],
                6: [(1, '凶骨', 16.0), (2, '大骑士勋章', 39.7), (3, '凤凰羽毛', 40.4), (4, '无间齿轮', 44.9),
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
        # 无限池 free quests' drop
        elif 'BATTLE IN NEWYORK 2019' in event.name:
            event.extra = {'蛮神心脏': '正赛票本: 193.5 AP', '闲古铃': '正赛票本: 110.5 AP',
                           '晓光炉心': 'S正赛票本: 161.8 AP', '人工生命体幼体': 'S正赛票本: 112.6 AP',
                           '九十九镜': '决赛票本: 198.4 AP', '鬼魂提灯': '决赛票本: 110.3 AP'}
        elif '南丁格尔' in event.name:
            event.extra = {'混沌之爪': '兑换券', '凤凰羽毛': '兑换券', '巨人的戒指': '兑换券',
                           '蛮神心脏': '票本: 197.0 AP', '极光之钢': '票本: 109.7 AP'}
        # 柱子
        elif 'ONILAND' in event.name:
            event.extra = {'真理之卵': '鬼救阿級: 251.3 AP', '极光之钢': '鬼救阿級: 125.8 AP',
                           '振荡火药': '鬼救阿級: 56.3 AP', '宵泣之铁桩': '鬼救阿級: 57.2 AP'}
        elif '莱妮丝事件簿' in event.name:
            event.extra = {"龙之逆鳞": "201.5 AP (巴巴妥司压制战)", "蛮神心脏": "202.7", "人工生命体幼体": "49.8 AP",
                           "无间齿轮": "46.6 AP", "禁断书页": "50.1 AP", "鬼魂提灯": "149.0 AP",
                           "虚影之尘": "119.4 AP", "凶骨": "75.0 AP"}

        # check valid items
        self.check_valid_item(event.items)
        self.check_valid_item(event.itemShop)
        self.check_valid_item(event.itemTask)
        self.check_valid_item(event.itemPoint)
        self.check_valid_item(event.itemRewardDrop)
        self.check_valid_item(event.lottery)

        return key, event

    def _parse_tickets(self):
        wikitext: str = get_site_page('素材交换券')
        section = mwp.parse(remove_tag(wikitext, ('comment', 'include'))).get_sections(matches='可兑换的素材清单')[0]
        table = wikitextparser.parse(str(section)).tables[0].data()
        table.pop(0)  # pop header
        assert len(table) > 10

        def _month_str(ym):
            return f'{ym[0]}/{ym[1]:02d}'

        month_cn, month_jp = (2018, 11), (2017, 8)
        for row in table:
            ticket = ExchangeTicket()
            ticket.monthCn = _month_str(month_cn)
            ticket.monthJp = _month_str(month_jp)
            ticket.days = calendar.mdays[month_cn[1]]
            for i in (2, 3, 4):
                ticket.items.append(t_one_item(parse_template(row[i], '道具'))[0])
            self.data.exchangeTickets[ticket.monthCn] = ticket
            month_cn = calendar.nextmonth(*month_cn)
            month_jp = calendar.nextmonth(*month_jp)
        all_months = [e.monthJp for e in self.data.exchangeTickets.values()]
        logger.info(f'exchange tickets of {len(all_months)} months from {all_months[0]} to {all_months[-1]} (jp)')

    def check_valid_item(self, data: Dict[str, Any], remain_special=False):
        if self._item_parser:
            for item in list(data.keys()):
                if item not in self._item_parser.data:
                    data.pop(item)
                elif not remain_special and ('圣杯' in item or '传承结晶' in item):
                    data.pop(item)

    def dump(self, fp: str):
        for event in self.data.limitEvents.values():
            # for debug, comment this to retain item details
            event.set_ignored(['itemShop', 'itemTask', 'itemPoint', 'itemRewardDrop'])
        dump_json(self.data.to_json(), fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
