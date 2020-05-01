import base64

import mwclient

kWorkersNum = 20


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


config = Config()
