# %% CSV
from mcparser.wiki_getter import *  # noqas

WikiGetter.get_servant_data()
WikiGetter.get_craft_data()
WikiGetter.get_cmd_data()
EventWikiGetter.get_event_data()

# %% set ICONS fp first
from mcparser.utils.icons import ICONS  # noqas

ICONS.load(config.paths.icon_des)

# %% items
from mcparser.item_parser import *  # noqas

ip = ItemParser()
ip.parse()
ip.dump(config.paths.item_des)

# %% Servants
from mcparser.svt_parser import *  # noqas

# logger.setLevel(logging.INFO)
sp = ServantParser(config.paths.svt_src)
sp.parse(range(0, 500), workers=40)
sp.dump(config.paths.svt_des)

# %% Crafts
from mcparser.craft_parser import *  # noqas

# logger.setLevel(logging.INFO)
cep = CraftParser(config.paths.craft_src, sp)
cep.parse(range(0, 2000), workers=40)
cep.dump(config.paths.craft_des)
sp.dump(config.paths.svt_des)

# %% CmdCodes
from mcparser.cmd_parser import *  # noqas

# logger.setLevel(logging.INFO)
ccp = CmdParser(config.paths.cmd_src)
ccp.parse(range(0, 500), workers=20)
ccp.dump(config.paths.cmd_des)

# %% Event
from mcparser.event_parser import *  # noqas

ep = EventParser(config.paths.event_src, ip)
ep.parse(workers=40)
ep.dump(config.paths.event_des)

# %% quest
from mcparser.quest_parser import *  # noqas

qp = QuestParser()
qp.parse_free_quest(config.paths.event_src)
qp.parse_svt_quest(config.paths.svt_src)
qp.dump(config.paths.quest_des)

# %% glpk
from mcparser.glpk_parser import *  # noqas

gp = GLPKParser()
gp.parse()
gp.check_quest(qp)
gp.add_special_drops()
gp.dump(config.paths.glpk_des)

# %% save icons
ICONS.download_icons(config.paths.icons_folder)
ICONS.dump(config.paths.icon_des)

# %% pack
from mcparser.packer import *  # noqas

make_dataset(config.paths.dataset_des, sp, cep, ccp, ep, ip, ICONS, qp, gp)
make_zip('output/test_default.zip')
