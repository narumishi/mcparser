from io import StringIO

import numpy  # noqas

from .quest_parser import QuestParser
from .utils.datatypes import *
from .utils.util import *


# noinspection DuplicatedCode
class GLPKParser:
    def __init__(self):
        self.data = GLPKData()
        self.df: Optional[pd.DataFrame] = None

    def parse(self, cn_columns: int):
        csv_str = get_site_page('Widget:QuestItemAP/data')
        csv_str = csv_str.replace('航行点', '起航点').replace('得摩斯岛', '戴摩斯岛')
        df: pd.DataFrame = pd.read_csv(StringIO(csv_str), index_col='地点')
        df.pop('绊')
        self.data.costs = df.pop('AP').tolist()
        df = df.transpose()
        df.fillna(0, inplace=True)
        self.data.colNames = df.columns.tolist()
        self.data.rowNames = df.index.tolist()
        # TODO: manual update this value
        self.data.cnMaxColNum = cn_columns
        self.data.jpMaxColNum = len(self.data.colNames)
        for i in range(len(df.index)):
            row = []
            for j in range(len(df.columns)):
                v = df.iloc[i, j]
                row.append(v if v > 0 else 0)
            self.data.matrix.append(row)
        self.df = df

    def add_special_drops(self):
        extra_data = [
            ['狩猎5-1', 40, {'凶骨': 16.1}],
            ['狩猎5-2', 40, {'宵泣之铁桩': 21.2}],
            ['狩猎5-3', 40, {'禁断书页': 32.4}],
            ['狩猎5-4', 40, {'血之泪石': 76.5, '英雄之证': 26.7}],
            ['狩猎5-5', 40, {'陨蹄铁': 31.8}],
            ['狩猎5-6', 40, {'龙之逆鳞': 114.9, '极光之钢': 69.6}],

            ['狩猎6-1', 40, {'凶骨': 16.0}],
            ['狩猎6-2', 40, {'大骑士勋章': 39.7}],
            ['狩猎6-3', 40, {'凤凰羽毛': 40.4}],
            ['狩猎6-4', 40, {'无间齿轮': 44.9, '魔术髓液': 41.3}],
            ['狩猎6-5', 40, {'封魔之灯': 68.9, '振荡火药': 40.8}],
            ['狩猎6-6', 40, {'咒兽胆石': 98.6, '祸罪的箭镞': 67.6}],

            ['狩猎7-1', 40, {'凶骨': 16.0}],
            ['狩猎7-2', 40, {'八连双晶': 35.0}],
            ['狩猎7-3', 40, {'凤凰羽毛': 40.2}],
            ['狩猎7-4', 40, {'闲古铃': 54.8, '宵泣之铁桩': 36.0}],
            ['狩猎7-5', 40, {'战马的幼角': 66.9, '永远结冰': 57.6}],
            ['狩猎7-6', 40, {'智慧之圣甲虫像': 113.2, '枯淡勾玉': 56.8}],

            ['南丁圣诞2019', 40, {'蛮神心脏': 197.0, '极光之钢': 109.7}],

            ['弓凛祭2019-正赛', 40, {'蛮神心脏': 193.5, '闲古铃': 110.5}],
            ['弓凛祭2019-S正赛', 40, {'晓光炉心': 161.8, '人工生命体幼体': 112.6}],
            ['弓凛祭2019-决赛', 40, {'九十九镜': 198.4, '鬼魂提灯': 110.3}],

            ['ONILAND复刻', 40, {'真理之卵': 251.3, '极光之钢': 125.8, '振荡火药': 56.3, '宵泣之铁桩': 57.2}],
            ['莱妮丝事件簿', 40, {'龙之逆鳞': 201.5, '蛮神心脏': 202.7, '人工生命体幼体': 49.8, '无间齿轮': 46.6,
                            '禁断书页': 50.1, '鬼魂提灯': 149.0, '虚影之尘': 119.4, '凶骨': 75.0}],
        ]
        for row in extra_data:
            name, ap, items = row
            self.data.colNames.append(name)
            self.data.costs.append(ap)
            for row_index, row_item in enumerate(self.data.rowNames):
                self.data.matrix[row_index].append(items.get(row_item, 0))

    def check_quest(self, quest_parser: QuestParser):
        not_found = []
        for name in self.data.colNames:
            if name not in quest_parser.free_quest_data:
                if not name.startswith('周') and not name.endswith('级'):
                    not_found.append(name)
        if not_found:
            logger.warning(f'The following quests not in free quest data: {not_found}')

    def dump(self, fp: str = None):
        fp = fp or config.paths.quest_des
        dump_json(self.data, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump data at "{fp}"')


# noinspection DuplicatedCode
class GLPKNumParser:
    def __init__(self):
        self.data = GLPKData()
        self.df: Optional[pd.DataFrame] = None

    def parse(self):
        csv_str = get_site_page('Widget:QuestItemNum/data')
        df: pd.DataFrame = pd.read_csv(StringIO(csv_str), index_col='地点')
        self.data.costs = df.pop('AP').tolist()
        df = df.transpose()
        df.fillna(0, inplace=True)
        self.data.colNames = df.columns.tolist()
        self.data.rowNames = df.index.tolist()
        # TODO: manual update this value
        self.data.cnMaxColNum = 170
        self.data.jpMaxColNum = len(self.data.colNames)
        for i in range(len(df.index)):
            row = []
            for j in range(len(df.columns)):
                v = df.iloc[i, j]
                row.append(v if v > 0 else 0)
            self.data.matrix.append(row)
        globals()['qp_df'] = self.df = df

    def add_special_drops(self):
        extra_data = [
            ['狩猎5-1', 40, {'凶骨': 16.1}],
            ['狩猎5-2', 40, {'宵泣之铁桩': 21.2}],
            ['狩猎5-3', 40, {'禁断书页': 32.4}],
            ['狩猎5-4', 40, {'血之泪石': 76.5, '英雄之证': 26.7}],
            ['狩猎5-5', 40, {'陨蹄铁': 31.8}],
            ['狩猎5-6', 40, {'龙之逆鳞': 114.9, '极光之钢': 69.6}],

            ['狩猎6-1', 40, {'凶骨': 16.0}],
            ['狩猎6-2', 40, {'大骑士勋章': 39.7}],
            ['狩猎6-3', 40, {'凤凰羽毛': 40.4}],
            ['狩猎6-4', 40, {'无间齿轮': 44.9, '魔术髓液': 41.3}],
            ['狩猎6-5', 40, {'封魔之灯': 68.9, '振荡火药': 40.8}],
            ['狩猎6-6', 40, {'咒兽胆石': 98.6, '祸罪的箭镞': 67.6}],

            ['狩猎7-1', 40, {'凶骨': 16.0}],
            ['狩猎7-2', 40, {'八连双晶': 35.0}],
            ['狩猎7-3', 40, {'凤凰羽毛': 40.2}],
            ['狩猎7-4', 40, {'闲古铃': 54.8, '宵泣之铁桩': 36.0}],
            ['狩猎7-5', 40, {'战马的幼角': 66.9, '永远结冰': 57.6}],
            ['狩猎7-6', 40, {'智慧之圣甲虫像': 113.2, '枯淡勾玉': 56.8}],

            ['南丁圣诞2019', 40, {'蛮神心脏': 197.0, '极光之钢': 109.7}],

            ['弓凛祭2019-正赛', 40, {'蛮神心脏': 193.5, '闲古铃': 110.5}],
            ['弓凛祭2019-S正赛', 40, {'晓光炉心': 161.8, '人工生命体幼体': 112.6}],
            ['弓凛祭2019-决赛', 40, {'九十九镜': 198.4, '鬼魂提灯': 110.3}],

            ['ONILAND复刻', 40, {'真理之卵': 251.3, '极光之钢': 125.8, '振荡火药': 56.3, '宵泣之铁桩': 57.2}],
            ['莱妮丝事件簿', 40, {'龙之逆鳞': 201.5, '蛮神心脏': 202.7, '人工生命体幼体': 49.8, '无间齿轮': 46.6,
                            '禁断书页': 50.1, '鬼魂提灯': 149.0, '虚影之尘': 119.4, '凶骨': 75.0}],
        ]
        for row in extra_data:
            name, ap, items = row
            self.data.colNames.append(name)
            self.data.costs.append(ap)
            for row_index, row_item in enumerate(self.data.rowNames):
                ap_rate = items.get(row_item, None)
                v = round(ap / ap_rate, 3) if ap_rate else 0
                self.data.matrix[row_index].append(v)

    def check_quest(self, quest_parser: QuestParser):
        not_found = []
        for name in self.data.colNames:
            if name not in quest_parser.free_quest_data:
                if not name.startswith('周') and not name.endswith('级'):
                    not_found.append(name)
        if not_found:
            logger.warning(f'The following quests not in free quest data: {not_found}')

    def dump(self, fp: str = None):
        fp = fp or config.paths.quest_des
        dump_json(self.data, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump data at "{fp}"')
