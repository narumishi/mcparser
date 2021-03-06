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

    def parse_csv(self, url, remain_cols: List[str] = None, replace_cols: Dict[str, str] = None,
                  override: pd.DataFrame = None):
        """Download html and parse csv str to DataFrame

        Pattern: 'var raw_str = "*****";'

        override: only override data if index not in csv

        svt cols:
         id,star,name_cn,name_jp,name_en,name_link,name_other,cost,faction,get,hp,atk,class_link,avatar,
         card1,card2,card3,card4,card5,np_card,np_type,class_icon,stars_marker,class_marker,get_marker,cards_marker,
         npc_marker,npt_marker,fac_marker,sex_marker,prop1_marker,prop2_marker,traits_marker,sort_atk,sort_hp

        craft cols:
         id,star,star_str,cost,hp1,hpmax,atk1,atkmax,icon,icon_eff,stars_marker,stats_marker,sort_atk,sort_hp

        cmd code cols:
         id,star,name,name_link,name_other,des,method,method_link,method_link_text,icon,icon_eff,stars_marker,type_marker
        """
        if replace_cols is None:
            replace_cols = {}
        page = urlopen(url)
        html_code = page.read().decode('utf-8')
        csv_str = re.findall(r'var raw_str = "(.*?)";', html_code)[0]
        csv_str = csv_str.replace('\\n', '\n')
        # cmd_code page error src code
        csv_str = csv_str.replace('id,star,icon,icon_eff,stars_marker', 'id,star,icon,icon_eff,stars_marker,nothing')
        df: pd.DataFrame = pd.read_csv(StringIO(csv_str), sep=',', index_col='id', dtype='object')
        if override is not None:
            for i in override.index:
                # only override if index not in csv
                if i not in df.index:
                    for j in override.columns:
                        if not pd.isna(override.loc[i, j]):
                            df.loc[i, j] = override.loc[i, j]
        df = df.fillna('')

        # override_data
        override_data_str: str = re.findall(r'override_data = "(.*?)";', html_code)[0]
        override_data_str = override_data_str.replace('\\n', '\n')
        override_list = override_data_str.split('\n\n')
        for override_record in override_list:
            if 'id' in override_record:
                override_map = {}
                for row in override_record.split('\n'):
                    k, v = row.split('=', maxsplit=1)
                    k, v = trim(k), trim(v)
                    if v != '':
                        override_map[k] = v
                item_id = int(override_map['id'])
                for key, value in override_map.items():
                    if key != 'id':
                        if key not in df.columns:
                            df.loc[item_id, key] = ''  # set dtype to object rather float
                        df.loc[item_id, key] = value
                # logger.info(f'override map: {override_map}')
        df = df.fillna('')
        for col in list(remain_cols) + list(replace_cols.values()):
            if col not in df.columns:
                df.loc[1, col] = ''
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
    def down_all_wikitext(self, _range: Iterable = None, workers: int = None, sub_pages: Dict[str, str] = None):
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
                if key == 'wikitext':
                    logger.warning(f'No.{index}-{page_link} wikitext is null!')
                continue
            redirect_link = redirect_page(wikitext)
            if redirect_link:
                logger.warning(f'redirect No.{index}-{name_link} to {redirect_link}')
                self.data.loc[index, 'name_link'] = redirect_link
                wikitext = get_site_page(redirect_link)
            # assert redirect_link is None, (redirect_link, wikitext)
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
        WikiGetter.svt_spider = svt_spider = WikiGetter(fp)
        svt_spider.parse_csv(url=config.url_svt,
                             remain_cols=['name_link', 'name_cn', 'name_other'],
                             replace_cols={'avatar': 'icon', 'method': 'obtain', 'np_type': 'nobel_type'},
                             override=kwargs.pop('override', None))
        svt_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                     workers=kwargs.pop('workers', config.default_workers),
                                     sub_pages={'wikitext_voice': '语音', 'wikitext_quest': '从者任务'})
        svt_spider.dump(fp)
        return svt_spider

    @staticmethod
    def get_craft_data(fp: str = None, **kwargs):
        fp = fp or config.paths.craft_src
        WikiGetter.craft_spider = craft_spider = WikiGetter(fp)
        craft_spider.parse_csv(url=config.url_craft,
                               remain_cols=['name_link', 'name', 'name_other', 'icon', 'hp1', 'hpmax', 'atk1', 'atkmax',
                                            'des', 'des_max', 'type'],
                               replace_cols={},
                               override=kwargs.pop('override', None))
        for index in craft_spider.data.index:
            craft_spider.data.loc[index, 'des'] = remove_tag(craft_spider.data.loc[index, 'des'])
            craft_spider.data.loc[index, 'des_max'] = remove_tag(craft_spider.data.loc[index, 'des_max'])
        craft_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                       workers=kwargs.pop('workers', config.default_workers))
        craft_spider.dump(fp)
        return craft_spider

    @staticmethod
    def get_cmd_data(fp: str = None, **kwargs):
        fp = fp or config.paths.cmd_src
        WikiGetter.cmd_spider = cmd_spider = WikiGetter(fp)
        cmd_spider.parse_csv(url=config.url_cmd,
                             remain_cols=['name_link', 'name', 'name_other', 'des', 'method', 'method_link_text',
                                          'icon', 'type'],
                             replace_cols={},
                             override=kwargs.pop('override', None))
        cmd_spider.down_all_wikitext(_range=kwargs.pop('_range', None),
                                     workers=kwargs.pop('workers', config.default_workers))
        cmd_spider.dump(fp)
        return cmd_spider


class EventWikiGetter:
    def __init__(self, fp: str = None):
        if fp and os.path.exists(fp):
            self.data = load_json(fp)
        else:
            self.data: Dict[str, Any] = {}

    def dump(self, fp: str):
        dump_json(self.data, fp)
        logger.info(f'dump event json wikitext data at "{fp}"')

    def ask_event_list(self, event_types: List[str] = None, workers: int = None, start_from=None):
        executor = ThreadPoolExecutor(max_workers=workers)
        # add daily first
        daily_key = '迦勒底之门/每日任务'
        self.data['DailyQuest'] = {
            'name': daily_key,
            'event_page': '',
            'quest_page': remove_tag(get_site_page(daily_key), tags=kSafeTags),
            'sub_pages': {}
        }

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
            response = urlopen(f'https://{config.domain}/api.php?{urlencode(param)}')
            event_query_result: Dict = json.load(response)['query']['results']
            events = self.data.setdefault(_event_type, {})

            start_key, start_index = (start_from or {}).get(_event_type), 0
            for i, k in enumerate(event_query_result.keys()):
                if start_key and k.startswith(start_key):
                    start_index = i
                    logger.warning(f'start at {i}-{k}')
                    break
            all_keys = list(event_query_result.keys())
            down_keys, success_keys, error_keys = all_keys[start_index:], [], []
            finish_num, all_num = 0, len(down_keys)
            tasks = [executor.submit(self._down_wikitext, event_query_result[k]) for k in down_keys]

            # drop renamed event in previous `events` dict
            for e in [k for k in events.keys() if k not in all_keys]:
                logger.warning(f'Drop invalid event in previous records: {e}')
                events.pop(e)

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
            error_keys = [k for k in down_keys if k not in success_keys]
            logger.info(f'All {all_num} {_event_type} wikitext downloaded. {len(error_keys)} errors: {error_keys}',
                        extra=color_extra('red') if error_keys else None)
            self.data[_event_type] = sort_dict(events, lambda x: all_keys.index(x))

    @staticmethod
    @catch_exception
    def _down_wikitext(event_info: Dict[str, Any]) -> MapEntry[str, Dict]:
        name = event_info['fulltext']
        sub_pages = {}
        sub_page_titles = []

        if '亚马逊' in name:
            sub_page_titles = ['亚马逊仓库', '阿耳忒弥斯神殿塔', '极·阿耳忒弥斯神殿塔']
        elif '百重塔' in name:
            sub_page_titles = ['百重塔', '百重塔(阳炎)']
        elif '大奥' in name:
            sub_page_titles = [f'第{i}层' for i in '一二三四五']
        for title in sub_page_titles:
            sub_pages[title] = remove_tag(get_site_page(f'{name}/关卡配置/{title}'), tags=kSafeTags)
        result = {
            'name': name,
            'event_page': remove_tag(get_site_page(name), tags=kSafeTags),
            'quest_page': remove_tag(get_site_page(name + '/关卡配置'), tags=kSafeTags),
            'sub_pages': sub_pages
        }
        return name, result

    @staticmethod
    def get_event_data(fp: str = None, **kwargs):
        fp = fp or config.paths.event_src
        event_spider = EventWikiGetter(fp)
        event_spider.ask_event_list(event_types=kwargs.pop('event_types', None),
                                    workers=kwargs.pop('workers', config.default_workers),
                                    start_from=kwargs.pop('start_from', None))
        event_spider.dump(fp)
