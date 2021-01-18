from mcparser.cmd_parser import *  # noqas
from mcparser.craft_parser import *  # noqas
from mcparser.event_parser import *  # noqas
from mcparser.glpk_parser import *  # noqas
from mcparser.item_parser import *  # noqas
from mcparser.packer import *  # noqas
from mcparser.quest_parser import *  # noqas
from mcparser.svt_parser import *  # noqas
from mcparser.svt_parser import *  # noqas
from mcparser.utils.icons import ICONS  # noqas
from mcparser.wiki_getter import *  # noqas

t0 = time.time()
# logger.setLevel(logging.INFO)
tasks = ['csv', 'icon', 'item', 'svt', 'craft', 'cmd', 'event', 'quest', 'glpk', 'dicon', 'pack']
# tasks = [ 'icon', 'dicon']
# tasks = ['icon', 'item', 'svt', 'craft', 'cmd', 'event', 'quest', 'glpk', 'dicon', 'pack']
# %% 1-CSV
if 'csv' in tasks:
    # override = pd.DataFrame(index=[289, 290, 291],
    #                         columns=['name_link', 'name_cn', 'avatar', 'get', 'np_type'],
    #                         data=[['阿比盖尔·威廉姆斯〔夏〕', '阿比盖尔·威廉姆斯〔夏〕', 'Servant289.jpg', '期间限定', '全体']])
    override = None
    WikiGetter.get_servant_data(override=override, )
    WikiGetter.get_craft_data()
    WikiGetter.get_cmd_data()
    EventWikiGetter.get_event_data(start_from=None)  # {'Event': '狩猎关卡 第6'})
else:
    print('skip csv')

# %% 2-set ICONS first
if 'icon' in tasks:
    ICONS.load(config.paths.icon_des)
    # ICONS.add_common_icons()
else:
    print('skip icon')

# %% 3-then items
if 'item' in tasks:
    ip = ItemParser()
    ip.parse()
    ip.dump(config.paths.item_des)
else:
    print('skip item')

# %% 4-Servants
if 'svt' in tasks:
    sp = ServantParser(config.paths.svt_src)
    sp.parse()
    sp.dump(config.paths.svt_des)
else:
    print('skip svt')

# %% 5-Crafts
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
if 'cmd' in tasks:
    ccp = CmdParser(config.paths.cmd_src)
    ccp.parse(range(0, 500))
    ccp.dump(config.paths.cmd_des)
else:
    print('skip cmd')

# %% 7-Event
if 'event' in tasks:
    ip = globals().get('ip', None)
    ep = EventParser(config.paths.event_src, ip)
    ep.parse()
    ep.dump(config.paths.event_des)
else:
    print('skip event')

# %% 8-quest
if 'quest' in tasks:
    ip = globals().get('ip', None)
    qp = QuestParser(ip)
    qp.parse(config.paths.event_src, config.paths.svt_src)
    qp.dump(config.paths.quest_des)
else:
    print('skip quest')

# %% 9-glpk
if 'glpk' in tasks:
    qp = globals().get('qp', None)
    gp = GLPKParser()
    gp.parse(cn_columns=189)
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
if 'pack' in tasks:
    # make_dataset(config.paths.dataset_des, sp, cep, ccp, ep, ip, ICONS, qp, gp)
    make_dataset(config.paths.dataset_des)
    make_zip('output/releases/')
    make_zip('output/releases/', text_only=True)
    make_zip('output/', 'dataset.zip')
    make_zip('output/', 'dataset.zip', text_only=True)
    if is_windows():
        make_zip(r'D:/Projects/AndroidStudioProjects/chaldea/res/data/', 'dataset.zip')
    if is_macos():
        make_zip(r'/Users/narumi/Projects/chaldea/res/data/', 'dataset.zip')
else:
    print('skip pack')

# %%
dt = time.time() - t0
logger.info(f'====== run example for {int(dt / 60)} min {dt % 60:.1f} sec =====')
assert 1 == 2
