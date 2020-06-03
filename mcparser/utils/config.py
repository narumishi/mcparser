import base64
import os

import mwclient


class Config:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            return super(Config, cls).__new__(cls, *args, **kwargs)
        else:
            return cls._instance

    def __init__(self):
        self.domain = base64.urlsafe_b64decode('ZmdvLndpa2k=').decode('utf-8')
        self.site = mwclient.Site(self.domain, path='/')
        self.url_svt = f'https://{self.domain}/w/%E8%8B%B1%E7%81%B5%E5%9B%BE%E9%89%B4'
        self.url_craft = f'https://{self.domain}/w/%E7%A4%BC%E8%A3%85%E5%9B%BE%E9%89%B4'
        self.url_cmd = f'https://{self.domain}/w/%E6%8C%87%E4%BB%A4%E7%BA%B9%E7%AB%A0%E5%9B%BE%E9%89%B4'
        self.paths = PathManager()
        self.default_workers = 40


class PathManager:
    def __init__(self):
        self.wikitext_folder = 'output/wikitext'
        self.dataset_folder = 'output/dataset'

        self.fn_svt = 'servants'
        self.fn_craft = 'crafts'
        self.fn_cmd = 'cmd'
        self.fn_event = 'events'
        self.fn_icon = 'icons'
        self.fn_item = 'items'
        self.fn_quest = 'quests'
        self.fn_glpk = 'glpk'
        self.fn_dataset = 'dataset.json'

    @property
    def dataset_des(self):
        return os.path.join(self.dataset_folder, self.fn_dataset)

    @property
    def svt_src(self):
        return os.path.join(self.wikitext_folder, f'{self.fn_svt}_src.pkl')

    @property
    def svt_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_svt}.json')

    @property
    def craft_src(self):
        return os.path.join(self.wikitext_folder, f'{self.fn_craft}_src.pkl')

    @property
    def craft_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_craft}.json')

    @property
    def cmd_src(self):
        return os.path.join(self.wikitext_folder, f'{self.fn_cmd}_src.pkl')

    @property
    def cmd_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_cmd}.json')

    @property
    def event_src(self):
        return os.path.join(self.wikitext_folder, f'{self.fn_cmd}_src.json')

    @property
    def event_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_event}.json')

    @property
    def icon_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_icon}.json')

    @property
    def icons_folder(self):
        return os.path.join(self.dataset_folder, 'icons')

    @property
    def item_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_item}.json')

    @property
    def quest_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_quest}.json')

    @property
    def glpk_des(self):
        return os.path.join(self.dataset_folder, f'{self.fn_glpk}.json')


config = Config()
