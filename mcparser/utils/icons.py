from concurrent.futures.thread import ThreadPoolExecutor
from urllib.request import urlretrieve

from PIL import Image

from .datatypes import *
from .util import *


class _Icons:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            return super().__new__(cls, *args, **kwargs)
        else:
            return cls._instance

    def __init__(self, fp='output/temp/icons.json'):
        self.fp = fp
        self.data: Dict[str, FileResource] = {}
        self.load(fp)

    def add(self, filename: str, key: str = None, save: bool = True):
        if self.data == {}:
            self.load()
        fn_split = re.split(r'[(（]有框[)）]', filename)
        if len(fn_split) > 1:
            print(f'add a 无框 version of {"".join(fn_split)}')
            self.add(''.join(fn_split))
        if key is None:
            key = filename
        if key not in self.data:
            for fn in (filename, filename + '.png', filename + '.jpg'):
                info = config.site.images[filename].imageinfo
                if info != {}:
                    self.data[key] = FileResource(name=key, filename=fn, url=info['url'], save=save)
                    return key
            print(f'Adding icon: "{filename}" not exist!')
            return None
        else:
            return key

    def add_common_icons(self):
        jpg_fn = [fn + '.jpg' for fn in ('QP', '圣杯', '传承结晶')]
        png_fn = [fn + '.png' for fn in ('QP', '圣杯', '传承结晶', '圣杯传承结晶', 'Quick', 'Arts', 'Buster',
                                         '技能强化', '宝具强化', '灵衣开放权', '0星', '1星', '2星', '3星', '4星', '5星')]
        class_names = ['All', 'Saber', 'Archer', 'Lancer', 'Rider', 'Caster', 'Assassin', 'Berserker', 'Shielder',
                       'Ruler', 'Avenger', 'Alterego', 'MoonCancer', 'Foreigner']
        class_fn = [f'{color}{name}.png' for name in class_names for color in ('铜卡', '金卡')]
        class_back_fn = [f'{name}{color}卡背.png' for name in class_names for color in ('金', '银', '铜', '黑')]
        for fn in (jpg_fn + png_fn + class_fn + class_back_fn):
            self.add(fn)
        self.add('Beast.png', '金卡Beast.png')
        self.add('Beast-gray.png', '铜卡Beast.png')

    def download_icons(self, icon_dir=None, force=False):
        icon_dir = icon_dir or os.path.join(os.path.dirname(self.fp), 'icons')
        logger.info(f'downloading icons at {icon_dir}')
        self.add_common_icons()
        os.makedirs(icon_dir, exist_ok=True)

        def _down_icon(key):
            icon = self.data[key]
            icon_fp = os.path.join(icon_dir, icon.name)
            if not icon.url:
                # resolve exact file url
                icon.url = get_site_page(icon.filename or icon.name, isfile=True).imageinfo.get('url', None)
            if icon.save and icon.url and (force or not os.path.exists(icon_fp)):
                urlretrieve(icon.url, icon_fp)
                print(f'downloaded {icon.name}')
            else:
                # print(f'skip download {item["filename"]}')
                pass
            if '卡背' in key and os.stat(icon_fp).st_size > 200000:
                Image.open(icon_fp).convert('RGB').save(icon_fp, format='jpeg')
                print(f'compress icon {key}')

        executor = ThreadPoolExecutor(max_workers=kWorkersNum * 2)
        for _ in executor.map(_down_icon, self.data.keys()):
            pass
        for s in ('技能', '宝具'):
            img: Image.Image = Image.open(os.path.join(icon_dir, f'{s}强化.png'))
            palette = img.getpalette()
            for i in range(len(palette) // 3):
                gray = (palette[3 * i] * 299 + palette[3 * i + 1] * 587 + palette[3 * i + 2] * 114) // 1000
                palette[3 * i:3 * i + 3] = [gray, gray, gray]
            img.putpalette(palette)
            filename = f'{s}未强化.png'
            img.save(os.path.join(icon_dir, filename), format="png")
            self.data[filename] = FileResource(name=filename, url=None, save=False)
        print(f'downloaded icons at {icon_dir}')

    def dump(self, fp=None):
        """Call `download_icon()` before dump icons json"""
        fp = fp or self.fp
        dump_json(self.data, fp, default=lambda o: o.to_json(), sort_keys=True)
        logger.info(f'dump icons data at "{fp}"')
        return

    def load(self, fp=None):
        self.fp = fp = fp or self.fp
        if os.path.exists(fp):
            data = json.load(open(fp, encoding='utf8'))
            self.data = Jsonable.convert_map(data, FileResource)


ICONS = _Icons()
