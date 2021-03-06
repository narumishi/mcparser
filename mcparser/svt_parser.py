from .base_parser import *
from .utils.icons import ICONS
from .utils.templates import *


# noinspection PyMethodMayBeStatic
class ServantParser(BaseParser):
    def __init__(self, pkl_fn: str):
        super().__init__()
        self.src_data: pd.DataFrame = load_pickle(pkl_fn, pd.DataFrame())
        self.data: Dict[int, Servant] = {}

    def dump(self, fp: str = None):
        super().dump(fp or config.paths.svt_des)

    def get_keys(self):
        return self.src_data.index

    @catch_exception
    def _parse_one(self, index: int) -> MapEntry[int, Servant]:
        mc_link = self.src_data.loc[index, 'name_link']
        if threading.current_thread() != threading.main_thread():
            threading.current_thread().setName(f'Servant-{index}-{mc_link}')
        code = mwp.parse(self.src_data.loc[index, 'wikitext'])
        servant = Servant()
        servant.no = index
        servant.mcLink = mc_link
        servant.icon = os.path.basename(self.src_data.loc[index, 'icon'])
        ICONS.add(servant.icon)

        self._base_info(index, code, servant)
        self._treasure_device(index, code, servant)
        self._active_skill(index, code, servant)
        self._passive_skill(index, code, servant)
        self._item_cost(index, code, servant)
        self._bond_points(index, code, servant)
        self._profiles(index, code, servant)
        wikicode_voice = mwp.parse(self.src_data.loc[index, 'wikitext_voice'])
        self._voices(index, wikicode_voice, servant)
        return index, servant

    def _base_info(self, index: int, code: Wikicode, servant: Servant):
        servant.info = t_base_info(parse_template(code, r'^{{基础数值'))
        nicknames = [s for s in self.src_data.loc[index, 'name_other'].split('&') if s]
        servant.info.nicknames.extend(nicknames)
        servant.info.nicknames = list(set(servant.info.nicknames))
        servant.info.obtains = re.split(r'\s*[\n|&]\s*', remove_tag(self.src_data.loc[index, 'obtain'], ['br']))
        for illust in servant.info.illustrations.values():
            ICONS.add(illust, save=False)

    def _treasure_device(self, index: int, code: Wikicode, servant: Servant):
        td_sections = code.get_sections(matches='宝具')
        if len(td_sections) <= 0:
            return
        for state, td_text in split_tabber(td_sections[0]):
            td_params = parse_template(remove_tag(td_text), r'^{{宝具')
            td = t_treasure_device(td_params)
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
        left_section = section
        tabber_skills: List[Tag] = mwp.parse(left_section).filter_tags(recursive=False, matches='tabber')
        for _tabber in tabber_skills:
            left_section = left_section.replace(str(_tabber), '')
            if "'''技能" in str(_tabber):
                logger.error(f"No.{index}-active skill: '''技能x''' inside tabber!!!")
        standalone_skills = mwp.parse(left_section).filter_templates(matches='{{持有技能')
        split_skills = [str(c) for c in tabber_skills + standalone_skills]
        split_skills.sort(key=lambda x: section.index(x))

        # splits = re.split(r"'''技能(?:[1-3])(?:（(?:.+?)）)?'''", section)
        for s in split_skills:
            if '{{持有技能' not in s:
                continue
            skills_unsorted: List[Skill] = []  # including 强化前/后
            # print(split_tabber(s))
            # print('before split,', s)
            for state, skill_code in split_tabber(s):
                # print((state, skill_code))
                params = parse_template(remove_tag(skill_code), r'^{{持有技能')
                skill = t_active_skill(params)
                skill.state = state
                skills_unsorted.append(skill)
                ICONS.add(skill.icon)

            def _sort_skill(_skill: Skill):
                if '强化前' in _skill.state:
                    return 0
                elif '再强化' in _skill.state:  # Emiya skill3
                    return 2
                elif '强化后' in _skill.state:
                    return 1
                else:
                    return 0

            skills_sorted = sorted(skills_unsorted, key=_sort_skill)
            active_skill = ActiveSkill()
            active_skill.skills = skills_sorted
            active_skill.cnState = skills_sorted.index(skills_unsorted[0])
            servant.activeSkills.append(active_skill)

    def _passive_skill(self, index: int, code: Wikicode, servant: Servant):
        sections = code.get_sections(matches='职阶技能')
        if len(sections) == 0:
            return
        params = parse_template(remove_tag(str(sections[0])), r'^{{职阶技能')
        servant.passiveSkills = t_passive_skill(params)
        for skill in servant.passiveSkills:
            ICONS.add(skill.icon)
        if len(servant.passiveSkills) == 0:
            logger.info(f'No passive skills: No.{index}-{servant.mcLink}')

    def _item_cost(self, index: int, code: Wikicode, servant: Servant):
        sections = code.get_sections(matches='素材需求')
        if not sections:
            return
        code: Wikicode = sections[0]
        # ascension
        sections = code.get_sections(matches='灵基再临')
        if sections:
            section: Wikicode = sections[0]
            servant.itemCost.ascension = t_ascension_cost(parse_template(section, r'^{{灵基再临素材'))
        else:
            logger.warning(f'No.{index}-{servant.mcLink} has no ascension items', end='')

        # skill
        sections = code.get_sections(matches='技能强化')
        if sections:
            section: Wikicode = sections[0]
            servant.itemCost.skill = t_skill_cost(parse_template(section, r'^{{技能升级素材'))
        else:
            logger.warning(f'No.{index}-{servant.mcLink} has no skill up items', end='')

        # dress
        sections = code.get_sections(matches='灵衣开放')
        if sections:
            section: Wikicode = sections[0]
            for template in section.filter_templates(matches=r'^{{灵衣开放素材'):
                dress_result = t_dress_cost(parse_template(template))
                servant.itemCost.dress.extend(dress_result[0])
                servant.itemCost.dressName.extend(dress_result[1])
                servant.itemCost.dressNameJp.extend(dress_result[2])
        return

    def _bond_points(self, index: int, code: Wikicode, servant: Servant):
        params = parse_template(code, r'^{{羁绊点数')
        if index != 1 and index not in kUnavailableSvt:
            # 玛修 has no bond points
            for i in range(10):
                servant.bondPoints.append(params.get(str(i + 1), cast=int))
            servant.bondPoints.extend([1090000, 1230000, 1360000, 1500000, 1640000])

    def _profiles(self, index: int, code: Wikicode, servant: Servant):  # noqas
        section = code.get_sections(matches='资料')[0]
        params_profile = parse_template(remove_tag(str(section)), r'^{{个人资料')
        servant.profiles = t_profiles(params_profile)
        params_fool = parse_template(code, r'^{{愚人节资料')
        servant.profiles.extend(t_fool_profiles(params_fool))

    def _voices(self, index: int, code: Wikicode, servant: Servant):  # noqas
        for template in code.filter_templates(matches=r'^{{#invoke:VoiceTable'):
            params = parse_template(remove_tag(str(template)), r'^{{#invoke:VoiceTable')
            table = t_voice_table(params)
            # # resolve real url in client
            # for record in table.table:
            #     if record.voiceFile:
            #         ICONS.add(record.voiceFile, save=False)
            servant.voices.append(table)
