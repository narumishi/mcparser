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

    @count_time
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
                print(f'\r======= finished {finish_num}/{all_num} ========  ', end='')
        return self.data

    @catch_exception
    def _parse_one(self, index: int) -> Servant:
        mc_link = self.src_data.loc[index, 'name_link']
        threading.current_thread().setName(f'Servant-{index}-{mc_link}')
        code = mwp.parse(self.src_data.loc[index, 'wikitext'])
        servant = Servant()
        servant.no = index
        servant.mcLink = mc_link
        servant.icon = os.path.basename(self.src_data.loc[index, 'icon'])
        Icons.add(servant.icon)

        self._base_info(index, code, servant)
        self._treasure_device(index, code, servant)
        self._active_skill(index, code, servant)
        self._passive_skill(index, code, servant)
        self._item_cost(index, code, servant)
        self._bond_points(index, code, servant)
        self._profiles(index, code, servant)
        return servant

    def _base_info(self, index: int, code: Wikicode, servant: Servant):
        servant.info = p_base_info(parse_template(code, r'^{{基础数值'))
        nicknames = [s for s in self.src_data.loc[index, 'name_other'].split('&') if s]
        servant.info.nicknames.extend(nicknames)
        servant.info.nicknames = list(set(servant.info.nicknames))
        servant.info.obtains = self.src_data.loc[index, 'obtains'].split('&')

    def _treasure_device(self, index: int, code: Wikicode, servant: Servant):
        td_sections = code.get_sections(matches='宝具')
        if len(td_sections) <= 0:
            return
        for state, td_text in split_tabber(td_sections[0]):
            td_params = parse_template(remove_tag(td_text), r'^{{宝具')
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

    def _active_skill(self, index: int, code: Wikicode, servant: Servant):
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
                params = parse_template(remove_tag(skill_code), r'^{{持有技能')
                skill = p_active_skill(params)
                skill.state = state
                one_skill.append(skill)
                Icons.add(skill.icon)
            servant.activeSkills.append(one_skill)

    def _passive_skill(self, index: int, code: Wikicode, servant: Servant):
        sections = code.get_sections(matches='职阶技能')
        if len(sections) == 0:
            return
        params = parse_template(remove_tag(str(sections[0])), r'^{{职阶技能')
        servant.passiveSkills = p_passive_skill(params)
        for skill in servant.passiveSkills:
            Icons.add(skill.icon)
        if len(servant.passiveSkills) == 0:
            print(f'No passive skills: No.{index}-{servant.mcLink}')

    def _item_cost(self, index: int, code: Wikicode, servant: Servant):
        sections = code.get_sections(matches='素材需求')
        if not sections:
            return
        code: Wikicode = sections[0]
        # ascension
        sections = code.get_sections(matches='灵基再临')
        if sections:
            section: Wikicode = sections[0]
            servant.itemCost.ascension = p_ascension_cost(parse_template(section, r'^{{灵基再临素材'))
        else:
            print(f'No.{index}-{servant.mcLink} has no ascension items', end='')

        # skill
        sections = code.get_sections(matches='技能强化')
        if sections:
            section: Wikicode = sections[0]
            servant.itemCost.skill = p_skill_cost(parse_template(section, r'^{{技能升级素材'))
        else:
            print(f'No.{index}-{servant.mcLink} has no skill up items', end='')

        # dress
        sections = code.get_sections(matches='灵衣开放')
        if sections:
            section: Wikicode = sections[0]
            dress_result = p_dress_cost(parse_template(section, r'^{{灵衣开放素材'))
            servant.itemCost.dress, servant.itemCost.dressName, servant.itemCost.dressNameJp = dress_result

        return

    def _bond_points(self, index: int, code: Wikicode, servant: Servant):
        params = parse_template(code, r'^{{羁绊点数')
        if index != 1:
            # 玛修 has no bond points
            for i in range(10):
                servant.bondPoints.append(params.get(str(i + 1), cast=int))
            servant.bondPoints.extend([1090000, 1230000, 1360000, 1500000, 1640000])

    def _profiles(self, index: int, code: Wikicode, servant: Servant):  # noqas
        section = code.get_sections(matches='资料')[0]
        params_profile = parse_template(remove_tag(str(section)), r'^{{个人资料')
        servant.profiles = p_profiles(params_profile)
        params_fool = parse_template(code, r'^{{愚人节资料')
        servant.profiles.extend(p_fool_profiles(params_fool))

    def dump(self, fp='output/temp/svt.json'):
        dump_json(self.data, fp, default=lambda o: o.to_json())
