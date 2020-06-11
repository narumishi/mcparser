from .item_parser import ItemParser
from .utils.datatypes import *
from .utils.templates import t_quest
from .utils.util import *


class QuestParser:
    def __init__(self, item_parser: ItemParser = None):
        self.free_quest_data: Dict[str, Quest] = {}  # placeCn as key
        self.svt_quest_data: Dict[str, List[Quest]] = {}
        self._item_parser = item_parser

    def parse(self, event_src_fp: str, svt_src_fp: str, workers: int = None):
        executor = ThreadPoolExecutor(max_workers=workers or config.default_workers)

        # free quests of main story
        src_data = load_json(event_src_fp)
        event_data: Dict = src_data['MainStory']
        daily_key = '迦勒底之门/每日任务'
        event_data[daily_key] = src_data['DailyQuest']
        all_keys, success_keys, error_keys = list(event_data.keys()), [], []

        finish_num, all_num = 0, len(all_keys)
        tasks = [executor.submit(self._parse_free_quest, chapter, event_data) for chapter in event_data]
        for future in as_completed(tasks):
            finish_num += 1
            key = future.result()
            if key is None:
                logger.warning(f'======= parse free quest {finish_num}/{all_num}: FAILED ========')
            else:
                success_keys.append(key)
                logger.debug(f'======= parse free quest {finish_num}/{all_num} success: {key}')
        error_keys = [k for k in all_keys if k not in success_keys]
        logger.info(f'All free quests of {all_num} chapters parsed. {len(error_keys)} errors: {error_keys}',
                    extra=color_extra('red') if error_keys else None)
        self.free_quest_data = sort_dict(self.free_quest_data, lambda k, v: all_keys.index(v.chapter))

        # svt quests
        svt_pd: pd.DataFrame = load_pickle(svt_src_fp)
        all_keys, success_keys, error_keys = list(svt_pd.index), [], []
        finish_num, all_num = 0, len(all_keys)
        tasks = [executor.submit(self._parse_svt_quest, index, svt_pd) for index in svt_pd.index]
        for future in as_completed(tasks):
            finish_num += 1
            key = future.result()
            if key is None:
                logger.warning(f'======= parse svt quest {finish_num}/{all_num}: FAILED ========')
            else:
                success_keys.append(key)
                logger.debug(f'======= parse svt quest {finish_num}/{all_num} success:'
                             f' No.{key} {svt_pd.loc[key, "name_link"]}')
        error_keys = [k for k in all_keys if k not in success_keys]
        logger.info(f'All quests of {all_num} servants parsed. {len(error_keys)} errors: {error_keys}',
                    extra=color_extra('red') if error_keys else None)
        names = svt_pd['name_link'].tolist()
        self.svt_quest_data = sort_dict(self.svt_quest_data, lambda k: names.index(k))

    @catch_exception
    def _parse_free_quest(self, chapter: str, event_data: Dict) -> str:
        quest_wikitext = mwp.parse(event_data[chapter]['quest_page'])
        is_daily = '迦勒底之门/每日任务' == chapter
        if is_daily:
            section = quest_wikitext
        else:
            sections = quest_wikitext.get_sections(matches='自由关卡')
            section = sections[0] if sections else mwp.parse('')
        for template in section.filter_templates(matches='^{{关卡配置'):
            quest = t_quest(parse_template(template))
            if not quest.isFree:
                continue
            quest.chapter = chapter
            self.check_valid_item(quest)
            key = quest.indexKey = quest.name if is_daily else quest.get_place()
            if key in self.free_quest_data:
                pre_quest = self.free_quest_data.pop(key)
                logger.info(f'======= two quests at same place "{key}": {pre_quest.name}-{quest.name} ======')
                for q in (pre_quest, quest):
                    q.indexKey = f'{q.get_place()}（{q.name}）'
                    self.free_quest_data[q.indexKey] = q
                pass
            else:
                self.free_quest_data[key] = quest
        logger.debug(f'parsed free quests of {chapter}')
        return chapter

    @catch_exception
    def _parse_svt_quest(self, index: int, svt_pd: pd.DataFrame) -> int:
        svt_name = svt_pd.loc[index, 'name_link']
        quest_text = svt_pd.loc[index, 'wikitext_quest']
        if quest_text:
            for section_title in ('幕间物语', '强化任务'):
                for section in mwp.parse(quest_text).get_sections(matches=f'^{section_title}$'):
                    for template in section.filter_templates(matches='^{{关卡配置'):
                        quest = t_quest(parse_template(template))
                        quest.chapter = section_title + '-' + svt_name
                        self.check_valid_item(quest)
                        self.svt_quest_data.setdefault(svt_name, []).append(quest)
        return index

    def check_valid_item(self, quest: Quest, remain_special=False):
        if self._item_parser:
            data_to_check = [quest.rewards]
            for battle in quest.battles:
                data_to_check.append(battle.drops)
            for d in data_to_check:
                for item in list(d.keys()):
                    if item not in self._item_parser.data:
                        d.pop(item)
                    elif not remain_special and ('圣杯' == item or '传承结晶' == item):
                        d.pop(item)

    def dump(self, fp: str = None):
        fp = fp or config.paths.quest_des
        dump_json({
            "freeQuests": self.free_quest_data,
            "svtQuests": self.svt_quest_data
        }, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
