from mcparser.svt_parser import *  # noqas

t0 = time.time()
# logger.setLevel(logging.INFO)
tasks = ['csv', 'icon', 'item', 'svt', 'craft', 'cmd', 'event', 'quest', 'glpk', 'dicon', 'pack']
# tasks = [ 'icon', 'dicon']
# tasks = ['icon', 'item', 'svt', 'craft', 'cmd', 'event', 'quest', 'glpk', 'dicon', 'pack']
# %% 1-CSV
from mcparser.wiki_getter import *  # noqas

if 'csv' in tasks:
    WikiGetter.get_servant_data()
    WikiGetter.get_craft_data()
    WikiGetter.get_cmd_data()
    EventWikiGetter.get_event_data()
else:
    print('skip csv')

# %% 2-set ICONS first
from mcparser.utils.icons import ICONS  # noqas

if 'icon' in tasks:
    ICONS.load(config.paths.icon_des)
    # ICONS.add_common_icons()
else:
    print('skip icon')

# %% 3-then items
from mcparser.item_parser import *  # noqas

if 'item' in tasks:
    ip = ItemParser()
    ip.parse()
    ip.dump(config.paths.item_des)
else:
    print('skip item')

# %% 4-Servants
from mcparser.svt_parser import *  # noqas

if 'svt' in tasks:
    sp = ServantParser(config.paths.svt_src)
    sp.parse(range(0, 500))
    sp.dump(config.paths.svt_des)
else:
    print('skip svt')

# %% 5-Crafts
from mcparser.craft_parser import *  # noqas

if 'craft' in tasks:
    # logger.setLevel(logging.INFO)
    sp = globals().get('sp', None)
    cep = CraftParser(config.paths.craft_src, sp)
    cep.parse(range(0, 2000))
    cep.dump(config.paths.craft_des)
    if sp:
        sp.dump(config.paths.svt_des)
else:
    print('skip craft')

# %% 6-CmdCodes
from mcparser.cmd_parser import *  # noqas

if 'cmd' in tasks:
    ccp = CmdParser(config.paths.cmd_src)
    ccp.parse(range(0, 500))
    ccp.dump(config.paths.cmd_des)
else:
    print('skip cmd')

# %% 7-Event
from mcparser.event_parser import *  # noqas

if 'event' in tasks:
    ip = globals().get('ip', None)
    ep = EventParser(config.paths.event_src, ip)
    ep.parse()
    ep.dump(config.paths.event_des)
else:
    print('skip event')

# %% 8-quest
from mcparser.quest_parser import *  # noqas

if 'quest' in tasks:
    ip = globals().get('ip', None)
    qp = QuestParser(ip)
    qp.parse(config.paths.event_src, config.paths.svt_src)
    qp.dump(config.paths.quest_des)
else:
    print('skip quest')

# %% 9-glpk
from mcparser.glpk_parser import *  # noqas

if 'glpk' in tasks:
    qp = globals().get('qp', None)
    gp = GLPKParser()
    gp.parse()
    gp.check_quest(qp)
    gp.add_special_drops()
    gp.dump(config.paths.glpk_des)
else:
    print('skip glpk')

# %% 10-save icons
if 'dicon' in tasks:
    ICONS.download_icons(config.paths.icons_folder, workers=config.default_workers * 2)
    ICONS.dump(config.paths.icon_des)
else:
    print('skip dicon')

# %% 11-pack
from mcparser.packer import *  # noqas

if 'pack' in tasks:
    # make_dataset(config.paths.dataset_des, sp, cep, ccp, ep, ip, ICONS, qp, gp)
    make_dataset(config.paths.dataset_des)
    make_zip('output/dataset.zip')
    make_zip(r'D:\Projects\AndroidStudioProjects\chaldea\res\data\dataset.zip')
else:
    print('skip pack')

# %%
dt = time.time() - t0
logger.info(f'====== run example for {dt:.1f} seconds =====')
