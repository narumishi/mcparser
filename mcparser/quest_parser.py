from .utils.datatypes import *
from .utils.templates import t_quest
from .utils.util import *


class QuestParser:
    def __init__(self):
        self.free_quest_data: Dict[str, Quest] = {}  # placeCn as key
        self.svt_quest_data: Dict[str, List[Quest]] = {}

    def parse_free_quest(self, event_src_fp: str):
        event_data: Dict = load_json(event_src_fp)['MainStory']
        for chapter in event_data:
            quest_wikitext = mwp.parse(event_data[chapter]['quest_page'])
            for section in quest_wikitext.get_sections(matches='自由关卡'):
                for template in section.filter_templates(matches='^{{关卡配置'):
                    quest = t_quest(parse_template(template))
                    if not quest.isFree:
                        continue
                    quest.chapter = chapter
                    place = quest.get_place()
                    if place in self.free_quest_data:
                        pre_quest = self.free_quest_data.pop(place)
                        logger.info(f'======= two quests at same place "{place}": {pre_quest.name}-{quest.name} ======')
                        for q in (pre_quest, quest):
                            self.free_quest_data[f'{q.get_place()}（{q.name}）'] = q
                        pass
                    else:
                        self.free_quest_data[place] = quest
            logger.debug(f'parsed free quests of {chapter}')

    def parse_svt_quest(self, svt_src_fp: str):
        svt_pd: pd.DataFrame = load_pickle(svt_src_fp)
        for index in svt_pd.index:
            svt_name = svt_pd.loc[index, 'name_link']
            print(f'\rsvt quest: {index}-{svt_name: <25s}\r', end='')
            quest_text = svt_pd.loc[index, 'wikitext_quest']
            if not quest_text:
                continue
            for section_title in ('幕间物语', '强化任务'):
                for section in mwp.parse(quest_text).get_sections(matches=f'^{section_title}$'):
                    for template in section.filter_templates(matches='^{{关卡配置'):
                        quest = t_quest(parse_template(template))
                        quest.chapter = section_title + '-' + svt_name
                        self.svt_quest_data.setdefault(svt_name, []).append(quest)
        print('')
        logger.debug(f'All {len(svt_pd.index)} servants\' quests parsed.')

    def dump(self, fp: str = None):
        fp = fp or config.paths.quest_des
        dump_json({
            "freeQuests": self.free_quest_data,
            "svtQuests": self.svt_quest_data
        }, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
