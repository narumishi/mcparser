from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from urllib.request import urlopen
from urllib.parse import urlencode

from .utils.util import *


class WikiGetter:
    """Download html code to get csv str then parse it"""

    def __init__(self, fp: str, reload=True):
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

    def dump(self, fp=None):
        fp = fp or self.fp
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        pickle.dump(self.data, open(fp, 'wb'))
        self.data.to_json(open(fp + '.json', 'w', encoding='utf8'), orient='index', force_ascii=False, indent=2)
        logger.info(f'dump pickle and json data at "{fp}(.json)"')

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

    @count_time
    def down_all_wikitext(self, _range: Iterable = None, workers=kWorkersNum, subpages: Dict[str, str] = None):
        if _range is None:
            _range = self.data.index
        executor = ThreadPoolExecutor(max_workers=workers)
        valid_index = [i for i in self.data.index if i in _range]
        finish_num, all_num = 0, len(valid_index)
        for _ in executor.map(self._download_wikitext, valid_index, [subpages] * len(valid_index)):
            index = valid_index[finish_num]
            finish_num += 1
            logger.debug(f'======= No. {index} finished, {finish_num}/{all_num} ========')
        self.data[pd.isna(self.data)] = ''
        logger.info(f'All {all_num} wikitext downloaded.')

    @catch_exception
    def _download_wikitext(self, index: int, subpages: Dict[str, str]):
        name_link = self.data.loc[index, 'name_link']
        if threading.current_thread() != threading.main_thread():
            threading.current_thread().setName(f'No.{index}-{name_link}')
        pages = {'wikitext': name_link}
        if subpages:
            for key, sublink in subpages.items():
                pages[key] = name_link + '/' + sublink

        for key, page_link in pages.items():
            wikitext = get_site_page(page_link)
            assert wikitext != '', f'No.{index}-{page_link} wikitext is null!'
            redirect_link = redirect_page(wikitext)
            assert redirect_link is None, wikitext
            wikitext = remove_tag(wikitext, ('ref', 'br', 'comment', 'del', 'sup', 'include', 'heimu', 'ruby'))
            if key in self.data.keys():
                old_text = str(self.data.loc[index, key])
                if old_text != wikitext:
                    logger.info(f'No.{index:<3d}-{page_link}: wikitext changed: len {len(old_text)}->{len(wikitext)}')
            self.data.loc[index, key] = wikitext
        return index

    @staticmethod
    def get_servant_data(fp='output/wikitext/svt.pkl', **kwargs):
        svt_spider = WikiGetter(fp, reload=kwargs.pop('reload', True))
        svt_spider.parse_csv(url=config.url_svt,
                             remain_cols=['name_link', 'name_cn', 'name_other'],
                             replace_cols={'avatar': 'icon', 'get': 'obtain', 'np_type': 'nobel_type'})
        svt_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                     workers=kwargs.pop('workers', kWorkersNum),
                                     subpages={'wikitext_voice': '语音'})
        svt_spider.dump()

    @staticmethod
    def get_craft_data(fp='output/wikitext/craft.pkl', **kwargs):
        craft_spider = WikiGetter(fp, reload=kwargs.pop('reload', True))
        craft_spider.parse_csv(url=config.url_craft,
                               remain_cols=['name_link', 'name', 'name_other', 'icon', 'hp1', 'hpmax', 'atk1', 'atkmax',
                                            'des', 'des_max', 'type_marker'],
                               replace_cols={})
        for index in craft_spider.data.index:
            craft_spider.data.loc[index, 'des'] = remove_tag(craft_spider.data.loc[index, 'des'])
            craft_spider.data.loc[index, 'des_max'] = remove_tag(craft_spider.data.loc[index, 'des_max'])
        craft_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                       workers=kwargs.pop('workers', kWorkersNum))
        craft_spider.dump()

    @staticmethod
    def get_cmd_data(fp='output/wikitext/cmd.pkl', **kwargs):
        cmd_spider = WikiGetter(fp, reload=kwargs.pop('reload', True))
        cmd_spider.parse_csv(url=config.url_cmd,
                             remain_cols=['name_link', 'name', 'name_other', 'des', 'method', 'method_link_text',
                                          'icon', 'type_marker'],
                             replace_cols={})
        cmd_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                     workers=kwargs.pop('workers', kWorkersNum))
        cmd_spider.dump()


class EventWikiGetter:
    def __init__(self, fp: str, reload=True):
        self.fp = fp
        if reload is False and G.get(fp) is not None:
            data = G[fp]
        elif not os.path.exists(fp):
            data = {}
        else:
            data = load_json(fp)
            logger.info(f'loaded json data: {fp}')
        G[fp] = data
        self.data: Dict[str, Any] = data

    def dump(self, fp=None):
        fp = fp or self.fp
        dump_json(self.data, fp)
        logger.info(f'dump event json wikitext data at "{fp}"')

    def ask_event_list(self, event_types: List[str] = None, workers=kWorkersNum):
        executor = ThreadPoolExecutor(max_workers=workers)
        if event_types is None:
            event_types = ['MainStory', 'Event']
        for _event_type in event_types:
            param = {
                "action": "ask",
                "format": "json",
                "query": f"[[分类:有活动信息的页面]][[EventType::{_event_type}]]|?EventNameJP|sort=EventStartJP|limit=500",
                "api_version": "2",
                "utf8": 1
            }
            response = urlopen(f'https://fgo.wiki/api.php?{urlencode(param)}')
            event_query_list: List[Dict] = list(json.load(response)['query']['results'].values())
            events = self.data.setdefault(_event_type, {})
            finish_num, all_num = 0, len(event_query_list)
            for result in executor.map(self._down_wikitext, event_query_list):
                fullname = event_query_list[finish_num]['fulltext']
                finish_num += 1
                if result:
                    events[fullname] = result
                    logger.debug(f'======= {_event_type}: No.{finish_num}-"{fullname}" success,'
                                 f' {finish_num}/{all_num} ========')
                else:
                    logger.warning(f'======= {_event_type}: No.{finish_num}-"{fullname}" failed,'
                                   f' {finish_num}/{all_num} ========')
            logger.info(f'{_event_type}: All {all_num} wikitext downloaded.')

    @staticmethod
    @catch_exception
    def _down_wikitext(event_info: Dict[str, Any]):
        name = event_info['fulltext']
        return {
            'name': name,
            'event_page': get_site_page(name),
            'quest_page': get_site_page(name + '/关卡配置'),
            'subpages': {}
        }
