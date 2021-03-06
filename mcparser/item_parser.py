from .utils.datatypes import Item
from .utils.icons import ICONS
from .utils.util import *


class ItemParser:
    def __init__(self):
        self.data: Dict[str, Item] = {}

    def parse(self):
        wikitext: Wikitext = mwp.parse(get_site_page('道具一览'))

        # category 1
        for i, section_title in enumerate(['铜素材', '银素材', '金素材']):
            section = wikitext.get_sections(matches=section_title)[0]
            table = wikitextparser.parse(str(section)).tables[-1]
            item_icons = [split_file_link(link) for link in table.data(column=0) if '[[' in link]
            for j, item_icon in enumerate(item_icons):
                ICONS.add(item_icon)
                item = Item()
                item.name = item_icon.split('.')[0]
                item.category = 1
                item.rarity = i + 1
                item.id = item.category * 1000 + item.rarity * 100 + (j + 1)
                self.data[item.name] = item
        ICONS.add('圣杯传承结晶.png')
        for i, link in enumerate(['传承结晶.jpg', '圣杯.jpg']):
            item_name = link.split('.')[0]
            ICONS.add(link)
            self.data[item_name] = Item(id=1400 + i + 1, name=item_name, category=1, rarity=4)
        # category 2
        for i, suffix in enumerate(['辉石', '魔石', '秘石']):
            for j, class_name in enumerate('剑弓枪骑术杀狂'):
                item = Item()
                item.name = f'{class_name}之{suffix}'
                ICONS.add(item.name + '.jpg')
                item.category = 2
                item.rarity = i + 1
                item.id = item.category * 1000 + item.rarity * 100 + (j + 1)
                self.data[item.name] = item
        # category 3
        for i, suffix in enumerate(['银棋', '金像']):
            for j, class_name in enumerate('剑弓枪骑术杀狂'):
                item = Item()
                item.name = f'{class_name}阶{suffix}'
                ICONS.add(item.name + '.jpg')
                item.category = 3
                item.rarity = i + 2
                item.id = item.category * 1000 + item.rarity * 100 + (j + 1)
                self.data[item.name] = item
        # category 4
        self.data['QP'] = Item(id=5101, name='QP', category=5, rarity=1)
        # category 5
        section = wikitext.get_sections(matches='活动从者灵基再临素材')[0]
        table = wikitextparser.parse(str(section)).tables[-1]
        item_icons = [split_file_link(link) for link in table.data(column=0) if '[[' in link]
        for j, item_icon in enumerate(item_icons):
            ICONS.add(item_icon)
            item = Item()
            item.name = item_icon.split('.')[0]
            item.category = 4
            item.rarity = 3
            item.id = item.category * 1000 + item.rarity * 100 + (j + 1)
            self.data[item.name] = item
        self.data = sort_dict(self.data, lambda k, v: v.id)

    def dump(self, fp: str = None):
        fp = fp or config.paths.item_des
        dump_json(self.data, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
