import pickle
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from mcparser.utils.icons import Icons
from mcparser.utils.util_svt import *


# noinspection PyMethodMayBeStatic
class ServantParser:
    def __init__(self, pkl_fn):
        self.src_data: pd.DataFrame = pickle.load(open(pkl_fn, 'rb'))
        self.data: Dict[int, Servant] = {}

    def parse(self, _range: Iterable = range(1, 2000), workers=kWorkersNum):
        valid_index = [k for k in self.src_data.index if k in _range]
        finish_num, all_num = 0, len(valid_index)
        if workers == 1:
            for index in valid_index:
                servant = self._parse_one(index)
                if servant:
                    self.data[servant.no] = servant
                    finish_num += 1
                    print(f'\r======= finished {finish_num}/{all_num} ========', end='')
        else:
            executor = ThreadPoolExecutor(max_workers=workers)
            for servant in executor.map(self._parse_one, valid_index):
                if servant:
                    self.data[servant.no] = servant
                    finish_num += 1
                print(f'\r======= finished {finish_num}/{all_num} ========', end='')

    @catch_exception
    def _parse_one(self, index: int) -> Servant:
        threading.current_thread().setName(f'Servant-{index}')
        code = mwp.parse(self.src_data.loc[index, 'wikitext'])
        servant = Servant()
        servant.no = index
        servant.mcLink = self.src_data.loc[index, 'name_link']
        servant.icon = os.path.basename(self.src_data.loc[index, 'icon'])
        Icons.add(servant.icon)

        self._base_info(index, code, servant)
        self._treasure_device(index, code, servant)
        self._active_skill(index, code, servant)

        return servant

    def _base_info(self, index: int, code: Wikitext, servant: Servant):
        servant.info = p_base_info(parse_template(code, '{{基础数值'))
        nicknames = [s for s in self.src_data.loc[index, 'name_other'].split('&') if s]
        servant.info.nicknames.extend(nicknames)
        servant.info.nicknames = list(set(servant.info.nicknames))
        servant.info.obtains = self.src_data.loc[index, 'obtains'].split('&')

    def _treasure_device(self, index: int, code: Wikitext, servant: Servant):
        td_sections = code.get_sections(matches='宝具')
        if len(td_sections) <= 0:
            return
        for state, td_text in split_tabber(td_sections[0]):
            td_params = parse_template(td_text, '{{宝具')
            td = p_treasure_device(td_params)
            td.state = state
            servant.treasureDevice.append(td)
        if index == 1:  # 玛修: [第1部真名解放前, 第1部真名解放后, 第2部灵衣]
            servant.treasureDevice[0].state = '强化前'
            servant.treasureDevice[1].state = '强化后'
            servant.treasureDevice.pop(2)  # pop 第二部灵衣
        elif index == 150:  # 梅林: [宝具, 巴比伦尼亚NPC限定]
            servant.treasureDevice[0].state = ''
            servant.treasureDevice.pop(1)
        elif index in (239, 267, 268):
            # 239-迦摩: [初始, 灵基再临3后]
            # 267-泳装总司: [战斗形象1&3, 战斗形象2]
            # 268-S凛: [Arts, Buster, Quick]
            pass
        elif index in (156, 169, 170, 171, 172, 184, 185):  # 1.5 真名解放
            # 156-莫里亚蒂, 171-彭忒西勒亚, 185-千代女
            # 含强化: 169-山鲁佐德, 170-武则天, 172-哥伦布, 184-巴御前
            servant.treasureDevice.pop(0)  # pop 真名解放前
            if len(servant.treasureDevice) == 1:
                servant.treasureDevice[0].state = ''
            else:
                for td in servant.treasureDevice:
                    td.state = '强化后' if '强化后' in td.state else '强化前'

    def _active_skill(self, index: int, code: Wikitext, servant: Servant):
        if index == 1:  # 玛修 只用第一部技能
            section = parse_template(code.get_sections(matches=r'持有技能')[0], '复合标签')['2']
        else:
            sections = code.get_sections(matches=r'^持有技能$')
            if len(sections) == 0:
                return
            section = str(sections[0])
        splits = re.split(r"'''技能(?:[1-3])(?:（(?:.+?)）)?'''", section)
        for s in splits:
            if '{{持有技能' not in s:
                continue
            one_skill = []  # including 强化前/后
            for state, skill_code in split_tabber(s):
                params = parse_template(skill_code, '{{持有技能')
                skill = p_active_skill(params)
                skill.state = state
                one_skill.append(skill)
                Icons.add(skill.icon)
            servant.activeSkills.append(one_skill)

    def _passive_skill(self, index: int, code: Wikitext, servant: Servant):
        pass

    def dump(self, fp='output/temp/svt.json'):
        dump_json(self.data, fp, default=lambda o: o.to_json())
