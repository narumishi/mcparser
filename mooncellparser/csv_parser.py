import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from re import RegexFlag
from urllib.request import urlopen

import pandas as pd

from .util import *


class CSVParser:
    """Download html code to get csv str then parse it"""

    def __init__(self, fp, reload=True):
        self.fp = fp
        if reload is False and G.get(fp) is not None:
            data = G[fp]
        elif not os.path.exists(fp):
            data = pd.DataFrame()
        else:
            data = pickle.load(open(fp, 'rb'))
            logger.info(f'loaded pickle data: {fp}')
        G[fp] = data
        self.data: pd.DataFrame = data

    def dump(self):
        os.makedirs(os.path.dirname(self.fp), exist_ok=True)
        pickle.dump(self.data, open(self.fp, 'wb'))
        self.data.to_json(open(self.fp + '.json', 'w', encoding='utf8'), orient='index', force_ascii=False, indent=2)

    def parse_csv(self, url, remain_cols: List[str] = None, replace_cols: Dict[str, str] = None):
        """Download html and parse csv str to DataFrame

        Pattern: 'var raw_str = "*****";'

        svt cols:
         id,star,name_cn,name_jp,name_en,name_link,name_other,cost,faction,get,hp,atk,class_link,avatar,
         card1,card2,card3,card4,card5,np_card,np_type,class_icon,stars_marker,class_marker,get_marker,cards_marker,
         npc_marker,npt_marker,fac_marker,sex_marker,prop1_marker,prop2_marker,traits_marker,sort_atk,sort_hp

        craft cols:
         "id,star,star_str,name,name_link,name_other,cost,hp1,hpmax,atk1,atkmax,des,des_max,icon,icon_eff,
         type_marker,stars_marker,stats_marker,sort_atk,sort_hp

        cmd code cols:
         id,star,name,name_link,name_other,des,method,method_link,method_link_text,icon,icon_eff,stars_marker,type_marker
        """
        if replace_cols is None:
            replace_cols = {}
        page = urlopen(url)
        html_code = page.read().decode('utf-8')
        csv_str = re.findall(r'var raw_str = "(.*?)";', html_code)[0]
        csv_str = csv_str.replace('\\n', '\n')
        df: pd.DataFrame = pd.read_csv(StringIO(csv_str), sep=',', index_col='id', dtype='object')
        df = df.fillna('')

        # override_data
        override_data_str: str = re.findall(r'override_data = "(.*?)";', html_code)[0]
        override_list = override_data_str.split(';')
        for override_record in override_list:
            if 'id' in override_record:
                override_map = {}
                pairs = re.findall(r'([^,=;]+)=([^,=;]+)', override_record)
                for pair in pairs:
                    override_map[trim(pair[0])] = trim(pair[1])
                item_id = int(override_map['id'])
                for key, value in override_map.items():
                    if key != 'id':
                        df.loc[item_id, key] = value
                logger.info(f'override map: {override_map}')

        self.data = self.data.reindex(df.index)
        logger.info(f'records number = {len(self.data.index)}')

        # remain cols
        if remain_cols is None:
            remain_cols = list(df.columns)
        remain_cols_set = set(remain_cols)
        assert len(remain_cols) == len(remain_cols_set), f'duplicated keys: {remain_cols}'
        assert 'name_link' in remain_cols, 'key "name_link" should inside remain_cols'

        self.data[remain_cols] = df[remain_cols]
        self.data[list(replace_cols.values())] = df[list(replace_cols.keys())]
        G[self.fp] = self.data

    def down_all_wikitext(self, _range: Iterable = range(1, 2000), workers=kWorkersNum):
        executor = ThreadPoolExecutor(max_workers=workers)
        tasks = []
        for index in self.data.index:
            if index not in _range:
                continue
            tasks.append(executor.submit(self._download_wikitext, index))
        finished = 0
        for future in as_completed(tasks):
            res = future.result()
            finished += 1
            logger.info(f' - No.{res:<3d} downloaded, finished: [{finished:>3d}/{len(tasks)}]...')
        executor.shutdown(wait=True)
        self.data[pd.isna(self.data)] = ''
        logger.info(f'All {finished} wikitext downloaded.')

    def _download_wikitext(self, index):
        name_link = self.data.loc[index, 'name_link']
        wikitext = get_site_page(name_link)
        assert wikitext != '', f'No.{index}-{name_link} wikitext is null!'
        redirect_link = redirect(wikitext)
        if redirect_link is not None:
            self.data.loc[index, 'name_link'] = redirect_link
            wikitext = get_site_page(redirect_link)
        wikitext = re.sub(r'<br *?/? *?>', '\n', wikitext)
        wikitext = str(re.sub(r'</?(no)?(only)?(include|wiki)(only)?>', '', wikitext, flags=RegexFlag.IGNORECASE))
        wikitext = str(re.sub(r'<!--([\w\W]*?)-->', '', wikitext, flags=RegexFlag.IGNORECASE))
        if 'wikitext' in self.data.keys():
            old_text = str(self.data.loc[index, 'wikitext'])
            if old_text != wikitext:
                logger.info(f'No.{index:<3}: wikitext changed: len {len(old_text)}->{len(wikitext)}')
        self.data.loc[index, 'wikitext'] = wikitext
        return index

    @staticmethod
    def start_svt_spider(path='output/wikitext'):
        svt_spider = CSVParser(os.path.join(path, 'svt.pkl'), reload=False)
        svt_spider.parse_csv(url=config.url_svt,
                             remain_cols=['name_link', 'name_cn', 'name_other'],
                             replace_cols={'avatar': 'icon', 'get': 'obtain', 'np_type': 'nobel_type'})
        svt_spider.down_all_wikitext()
        svt_spider.dump()

    @staticmethod
    def start_craft_spider(path='output/wikitext'):
        craft_spider = CSVParser(os.path.join(path, 'craft.pkl'), reload=False)
        craft_spider.parse_csv(url=config.url_craft,
                               remain_cols=['name_link', 'name', 'name_other', 'icon', 'hp1', 'hpmax', 'atk1', 'atkmax',
                                            'des', 'des_max', 'type_marker'],
                               replace_cols={})
        for index in craft_spider.data.index:
            craft_spider.data.loc[index, 'des'] = remove_tag(craft_spider.data.loc[index, 'des'])
            craft_spider.data.loc[index, 'des_max'] = remove_tag(craft_spider.data.loc[index, 'des_max'])
        craft_spider.down_all_wikitext()
        craft_spider.dump()

    @staticmethod
    def start_cmd_spider(path='output/wikitext'):
        cmd_spider = CSVParser(os.path.join(path, 'cmd.pkl'), reload=False)
        cmd_spider.parse_csv(url=config.url_cmd,
                             remain_cols=['name_link', 'name', 'method', 'method_link_text', 'icon'],
                             replace_cols={})
        cmd_spider.down_all_wikitext()
        cmd_spider.dump()
