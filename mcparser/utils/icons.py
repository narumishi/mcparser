from concurrent.futures.thread import ThreadPoolExecutor
from urllib.request import urlretrieve

from PIL import Image

from .datatypes import *
from .util import *


class Icons:
    filename = 'icons.json'
    data: Dict[str, FileResource] = {}

    @classmethod
    def add(cls, filename: str, key: str = None, save: bool = True):
        if cls.data == {}:
            cls.load()
        fn_split = re.split(r'[(（]有框[)）]', filename)
        if len(fn_split) > 1:
            print(f'add a 无框 version of {"".join(fn_split)}')
            cls.add(''.join(fn_split))
        if key is None:
            key = filename
        if key not in cls.data:
            for fn in (filename, filename + '.png', filename + '.jpg'):
                info = config.site.images[filename].imageinfo
                if info != {}:
                    cls.data[key] = FileResource(name=key, filename=fn, url=info['url'], save=save)
                    return key
            print(f'Adding icon: "{filename}" not exist!')
            return None
        else:
            return key

    @classmethod
    def add_common_icons(cls):
        jpg_fn = [fn + '.jpg' for fn in ('QP', '圣杯', '传承结晶')]
        png_fn = [fn + '.png' for fn in ('QP', '圣杯', '传承结晶', '圣杯传承结晶', 'Quick', 'Arts', 'Buster',
                                         '技能强化', '宝具强化', '灵衣开放权')]
        class_names = ['All', 'Saber', 'Archer', 'Lancer', 'Rider', 'Caster', 'Assassin', 'Berserker', 'Shielder',
                       'Ruler', 'Avenger', 'Alterego', 'MoonCancer', 'Foreigner']
        class_fn = [f'{color}{name}.png' for name in class_names for color in ('铜卡', '金卡')]
        class_back_fn = [f'{name}{color}卡背.png' for name in class_names for color in ('金', '银', '铜', '黑')]
        for fn in (jpg_fn + png_fn + class_fn + class_back_fn):
            cls.add(fn)
        cls.add('Beast.png', '金卡Beast.png')
        cls.add('Beast-gray.png', '铜卡Beast.png')

    @classmethod
    def download_icons(cls, icon_dir='output/temp/icons', force=False):
        print(f'downloading icons at {icon_dir}')
        cls.add_common_icons()
        os.makedirs(icon_dir, exist_ok=True)

        def _down_icon(key):
            icon = cls.data[key]
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
        for _ in executor.map(_down_icon, cls.data.keys()):
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
            cls.data[filename] = FileResource(name=filename, url=None, save=False)
        print(f'downloaded icons at {icon_dir}')

    @classmethod
    def dump(cls, fn='output/temp/icons.json'):
        print(f'dumping icon data at {fn}')
        return dump_json(cls.data, fn, default=lambda o: o.to_json(), sort_keys=True)

    @classmethod
    def load(cls, fn='output/temp/icons.json'):
        if os.path.exists(fn):
            data = json.load(open(fn, encoding='utf8'))
            for k, v in data.items():
                cls.data[k] = FileResource(**v)
