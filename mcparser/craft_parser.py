from .base_parser import *
from .utils.datatypes import CraftEssential
from .utils.icons import ICONS
from .utils.util_other import p_craft_essential


def check_equal(hint: str, a, b, stop=True):
    # a: csv value, b: parsed value
    if isinstance(a, str):
        a = re.sub(r'[・·＆& ()\[\]〔〕【】,，%％的]', '', a)
        b = re.sub(r'[・·＆& ()\[\]〔〕【】,，%％的]', '', b)
        if a == b:
            return
        ab = a + b
        if '无效果' in ab or '礼装经验' in ab or '情人节' in ab:
            return
        if '装备时' in b or '自身在场' in b or '自身战败退场' in b:
            return
    if stop:
        assert a == b, f'Differ: {hint}\n  - {a}\n  - {b}'
    else:
        if a != b:
            logger.info(f'Differ: {hint}\n  - {a}\n  - {b}')


class CraftParser(BaseParser):
    def __init__(self, pkl_fn: str, svt_pkl_fn: str = None):
        self.svt_name_id_map = {}
        if svt_pkl_fn:
            svt_pkl: pd.DataFrame = pickle.load(open(svt_pkl_fn, 'rb'))
            if svt_pkl.shape[0] > 200:
                for index in svt_pkl.index:
                    self.svt_name_id_map[svt_pkl.loc[index, 'name_link']] = index
        super().__init__(pkl_fn)

    @catch_exception
    def _parse_one(self, index: int) -> CraftEssential:
        mc_link = self.src_data.loc[index, 'name_link']
        if threading.current_thread() != threading.main_thread():
            threading.current_thread().setName(f'Craft-{index}-{mc_link}')

        code = mwp.parse(self.src_data.loc[index, 'wikitext'])
        craft = p_craft_essential(parse_template(code, r'^{{概念礼装'))
        check_equal('index', index, craft.no)

        name_link, name, name_other, icon, hp1, hp_max, atk1, atk_max, des, des_max, type_marker = \
            self.src_data.loc[index,
                              ['name_link', 'name', 'name_other', 'icon', 'hp1', 'hpmax', 'atk1', 'atkmax',
                               'des', 'des_max', 'type_marker']]

        check_equal('mcLink', name_link, craft.mcLink, False)
        check_equal('name', name, craft.name, False)
        list_extend(craft.nameOther, name_other.split('&'))
        craft.icon = os.path.basename(icon)

        for icon in [craft.icon, craft.skillIcon] + craft.eventIcons:
            ICONS.add(icon)
        check_equal('hp min', int(hp1), craft.hpMin)
        check_equal('hp max', int(hp_max), craft.hpMax)
        check_equal('atk min', int(atk1), craft.atkMin)
        check_equal('atk min', int(atk_max), craft.atkMax)
        # check_equal('skill des', des, craft.skill, False)
        # check_equal('skill des max', des_max, craft.skillMax or '', False)
        craft.category = int(type_marker)

        # bond craft & valentine craft
        craft.bond = self._which_svt(code, 0)
        craft.valentine = self._which_svt(code, 1)
        return craft

    def _which_svt(self, code: Wikicode, kind=0) -> int:
        if kind == 0:
            pattern = r'^{{羁绊礼装'
        elif kind == 1:
            pattern = r'^{{情人节礼装'
        else:
            raise KeyError(f'Invalid kind: {kind}')
        params = parse_template(code, pattern)
        if not params or not self.svt_name_id_map:
            return -1
        svt_name = params.get('1')
        index = self.svt_name_id_map.get(svt_name, -1)
        if index > 0:
            return index

        new_name = redirect_page(get_site_page(svt_name), svt_name)
        if new_name != svt_name:
            index = self.svt_name_id_map.get(new_name, -1)
            if index > 0:
                return index
        logger.warning(f'CANNOT found svt "{svt_name}" for bond/valentine craft:\n{code}')
