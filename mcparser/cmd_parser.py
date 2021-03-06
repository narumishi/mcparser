from .base_parser import *
from .utils.datatypes import CmdCode
from .utils.icons import ICONS
from .utils.templates import t_cmd_code


def check_equal(hint: str, a, b, stop=True):
    # a: csv value, b: parsed value
    if isinstance(a, str):
        a = re.sub(r'[・·＆& ()\[\]〔〕【】,，%％的]', '', a)
        b = re.sub(r'[・·＆& ()\[\]〔〕【】,，%％的]', '', b)
        if a == b:
            return
    if stop:
        assert a == b, f'Differ: {hint}\n  - {a}\n  - {b}'
    else:
        if a != b:
            logger.info(f'Differ: {hint}\n  - {a}\n  - {b}')


class CmdParser(BaseParser):
    def __init__(self, pkl_fn: str):
        super().__init__()
        self.src_data: pd.DataFrame = load_pickle(pkl_fn, pd.DataFrame())
        self.data: Dict[int, CmdCode] = {}

    def dump(self, fp: str = None):
        super().dump(fp or config.paths.cmd_des)

    def get_keys(self):
        return self.src_data.index

    @catch_exception
    def _parse_one(self, index: int) -> MapEntry[int, CmdCode]:
        mc_link = self.src_data.loc[index, 'name_link']
        if threading.current_thread() != threading.main_thread():
            threading.current_thread().setName(f'CmdCode-{index}-{mc_link}')

        code = mwp.parse(self.src_data.loc[index, 'wikitext'])
        cmd_code = t_cmd_code(parse_template(code, r'^{{指令纹章'))
        check_equal('index', index, cmd_code.no)

        name_link, name, name_other, des, method, method_text, icon, _type = \
            self.src_data.loc[index,
                              ['name_link', 'name', 'name_other', 'des', 'method', 'method_link_text',
                               'icon', 'type']]

        check_equal('mcLink', name_link, cmd_code.mcLink, False)
        check_equal('name', name, cmd_code.name, False)
        list_extend(cmd_code.nameOther, name_other.split('&'))
        # check_equal('des', des, cmd_code.skill, False)
        cmd_code.obtain = remove_tag(method.replace('%LINK%', f'「{method_text}」'))

        cmd_code.icon = os.path.basename(icon)
        ICONS.add(cmd_code.illustration, save=False)
        for icon in [cmd_code.icon, cmd_code.skillIcon]:
            ICONS.add(icon)
        cmd_code.category = _type

        return index, cmd_code
