import zipfile

from .cmd_parser import CmdParser  # noqas
from .craft_parser import CraftParser  # noqas
from .event_parser import EventParser  # noqas
from .event_parser import EventParser  # noqas
from .glpk_parser import GLPKParser  # noqas
from .item_parser import ItemParser  # noqas
from .quest_parser import QuestParser  # noqas
from .svt_parser import ServantParser, kUnavailableSvt  # noqas
from .utils.basic import *
from .utils.config import config
from .utils.datatypes import *
from .utils.icons import ICONS, Icons  # noqas


def make_dataset(fp: str = None, sp: ServantParser = None, cep: CraftParser = None, ccp: CmdParser = None,
                 ep: EventParser = None, ip: ItemParser = None, icons: Icons = None, qp: QuestParser = None,
                 gp: GLPKParser = None):
    fp = fp or config.paths.dataset_des
    gamedata = GameData()
    gamedata.version = time.strftime("%Y%m%dT%H%M")

    def _get_data(parser, _fp):
        data = getattr(parser, 'data', None)
        if data:
            return data
        else:
            return load_json(_fp)

    gamedata.servants = _get_data(sp, config.paths.svt_des)
    gamedata.crafts = _get_data(cep, config.paths.craft_des)
    gamedata.cmdCodes = _get_data(ccp, config.paths.cmd_des)
    gamedata.events = _get_data(ep, config.paths.event_des)
    gamedata.items = _get_data(ip, config.paths.item_des)
    gamedata.icons = _get_data(icons, config.paths.icon_des)
    gamedata.glpk = _get_data(gp, config.paths.glpk_des)

    if qp and qp.free_quest_data and qp.svt_quest_data:
        gamedata.freeQuests = qp.free_quest_data
        gamedata.svtQuests = qp.svt_quest_data
    else:
        quests = load_json(config.paths.quest_des)
        gamedata.freeQuests = quests['freeQuests']
        gamedata.svtQuests = quests['svtQuests']
    gamedata.unavailable_svts = kUnavailableSvt
    gamedata.dump(fp)
    logger.info(f'dump gamedata at "{fp}"')


def make_zip(fp: str, dataset_fp: str = None, icon_folder: str = None):
    dataset_fp = dataset_fp or config.paths.dataset_des
    icon_folder = icon_folder or config.paths.icons_folder
    with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED)as fd:
        fd.write(dataset_fp, 'dataset.json')
        for filename in os.listdir(icon_folder):
            if filename[0] not in '._':
                fd.write(os.path.join(icon_folder, filename), f'icons/{filename}')
    logger.info(f'zip file saved at "{fp}"')
