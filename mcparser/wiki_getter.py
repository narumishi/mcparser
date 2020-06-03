from io import StringIO
from urllib.parse import urlencode
from urllib.request import urlopen

from .utils.util import *


class WikiGetter:
    """Download html code to get csv str then parse it"""

    def __init__(self, pkl_fn: str = None):
        if pkl_fn and os.path.exists(pkl_fn):
            self.data = load_pickle(pkl_fn)
        else:
            self.data = pd.DataFrame()

    def dump(self, fp: str):
        dump_pickle(self.data, fp)
        self.data.to_json(open(fp + '.json', 'w', encoding='utf8'), orient='index', force_ascii=False, indent=2)
        logger.info(f'dump pickle and json data at "{fp}[.json]"')

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

    @count_time
    def down_all_wikitext(self, _range: Iterable = None, workers=kWorkersNum, sub_pages: Dict[str, str] = None):
        if _range is None:
            _range = self.data.index
        executor = ThreadPoolExecutor(max_workers=workers)
        all_keys, success_keys, error_keys = [i for i in self.data.index if i in _range], [], []
        finish_num, all_num = 0, len(all_keys)
        tasks = [executor.submit(self._download_wikitext, index, sub_pages) for index in all_keys]
        for future in as_completed(tasks):
            finish_num += 1
            index = future.result()
            if index is None:
                logger.warning(f'======= download wikitext {finish_num}/{all_num} FAILED ========')
            else:
                success_keys.append(index)
                logger.debug(f'======= download wikitext {finish_num}/{all_num} success:'
                             f' No.{index} {self.data.loc[index, "name_link"]}')
        self.data[pd.isna(self.data)] = ''
        error_keys = [k for k in all_keys if k not in success_keys]
        logger.info(f'All {all_num} wikitext downloaded. {len(error_keys)} errors: {error_keys}',
                    extra=color_extra('red') if error_keys else None)

    @catch_exception
    def _download_wikitext(self, index: int, sub_pages: Dict[str, str]) -> int:
        name_link = self.data.loc[index, 'name_link']
        if threading.current_thread() != threading.main_thread():
            threading.current_thread().setName(f'No.{index}-{name_link}')
        pages = {'wikitext': name_link}
        if sub_pages:
            for key, sublink in sub_pages.items():
                pages[key] = name_link + '/' + sublink

        for key, page_link in pages.items():
            wikitext = get_site_page(page_link)
            if not wikitext:
                # logger.warning(f'No.{index}-{page_link} wikitext is null!')
                continue
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
    def get_servant_data(fp: str = None, **kwargs):
        fp = fp or config.paths.svt_src
        svt_spider = WikiGetter(fp)
        svt_spider.parse_csv(url=config.url_svt,
                             remain_cols=['name_link', 'name_cn', 'name_other'],
                             replace_cols={'avatar': 'icon', 'get': 'obtain', 'np_type': 'nobel_type'})
        svt_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                     workers=kwargs.pop('workers', kWorkersNum),
                                     sub_pages={'wikitext_voice': '语音', 'wikitext_quest': '从者任务'})
        svt_spider.dump(fp)

    @staticmethod
    def get_craft_data(fp: str = None, **kwargs):
        fp = fp or config.paths.craft_src
        craft_spider = WikiGetter(fp)
        craft_spider.parse_csv(url=config.url_craft,
                               remain_cols=['name_link', 'name', 'name_other', 'icon', 'hp1', 'hpmax', 'atk1', 'atkmax',
                                            'des', 'des_max', 'type_marker'],
                               replace_cols={})
        for index in craft_spider.data.index:
            craft_spider.data.loc[index, 'des'] = remove_tag(craft_spider.data.loc[index, 'des'])
            craft_spider.data.loc[index, 'des_max'] = remove_tag(craft_spider.data.loc[index, 'des_max'])
        craft_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                       workers=kwargs.pop('workers', kWorkersNum))
        craft_spider.dump(fp)

    @staticmethod
    def get_cmd_data(fp: str = None, **kwargs):
        fp = fp or config.paths.cmd_src
        cmd_spider = WikiGetter(fp)
        cmd_spider.parse_csv(url=config.url_cmd,
                             remain_cols=['name_link', 'name', 'name_other', 'des', 'method', 'method_link_text',
                                          'icon', 'type_marker'],
                             replace_cols={})
        cmd_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                     workers=kwargs.pop('workers', kWorkersNum))
        cmd_spider.dump(fp)


class EventWikiGetter:
    def __init__(self, fp: str = None):
        if fp and os.path.exists(fp):
            self.data = load_json(fp)
        else:
            self.data: Dict[str, Any] = {}

    def dump(self, fp: str):
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
                "api_version": "2",  # 2-dict, 3-list
                "utf8": 1
            }
            response = urlopen(f'https://fgo.wiki/api.php?{urlencode(param)}')
            event_query_result: Dict = json.load(response)['query']['results']
            events = self.data.setdefault(_event_type, {})

            all_keys, success_keys, error_keys = list(event_query_result.keys()), [], []
            finish_num, all_num = 0, len(all_keys)
            tasks = [executor.submit(self._down_wikitext, e) for e in event_query_result.values()]
            for future in as_completed(tasks):
                finish_num += 1
                result = future.result()
                if result is None:
                    logger.warning(f'======= download {_event_type} wikitext {finish_num}/{all_num} FAILED ========')
                else:
                    key, value = result
                    success_keys.append(key)
                    events[key] = value
                    logger.debug(f'======= download {_event_type} wikitext {finish_num}/{all_num} success: {key}')
            error_keys = [k for k in all_keys if k not in success_keys]
            logger.info(f'All {all_num} {_event_type} wikitext downloaded. {len(error_keys)} errors: {error_keys}',
                        extra=color_extra('red') if error_keys else None)

    @staticmethod
    @catch_exception
    def _down_wikitext(event_info: Dict[str, Any]) -> MapEntry[str, Dict]:
        name = event_info['fulltext']
        sub_pages = {}
        sub_page_titles = []
        tags = ('ref', 'br', 'comment', 'del', 'sup', 'include', 'heimu', 'ruby')

        if '亚马逊' in name:
            sub_page_titles = ['亚马逊仓库', '阿耳忒弥斯神殿塔', '极·阿耳忒弥斯神殿塔']
        elif '百重塔' in name:
            sub_page_titles = ['百重塔', '百重塔(阳炎)']
        elif '大奥' in name:
            sub_page_titles = [f'第{i}层' for i in '一二三四五']
        for title in sub_page_titles:
            sub_pages[title] = remove_tag(get_site_page(f'{name}/关卡配置/{title}'), tags=tags)
        result = {
            'name': name,
            'event_page': remove_tag(get_site_page(name), tags=tags),
            'quest_page': remove_tag(get_site_page(name + '/关卡配置'), tags=tags),
            'sub_pages': sub_pages
        }
        return name, result

    @staticmethod
    def get_event_data(fp: str = None, **kwargs):
        fp = fp or config.paths.event_src
        event_spider = EventWikiGetter(fp)
        event_spider.ask_event_list(event_types=kwargs.pop('event_types', None),
                                    workers=kwargs.pop('workers', kWorkersNum))
        event_spider.dump(fp)
