import abc
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils.util import *


# noinspection PyMethodMayBeStatic
class BaseParser(metaclass=abc.ABCMeta):
    def __init__(self):
        self.data: Dict = {}  # override to specify type

    @abc.abstractmethod
    def get_keys(self):
        pass

    @count_time
    def parse(self, _range: Iterable = None, workers=kWorkersNum):
        executor = ThreadPoolExecutor(max_workers=workers)
        all_keys = self.get_keys()
        if _range is None:
            _range = all_keys
        valid_keys = [k for k in all_keys if k in _range]
        finish_num, all_num = 0, len(valid_keys)

        tasks = [executor.submit(self._parse_one, key) for key in valid_keys]
        for future in as_completed(tasks):
            result = future.result()
            if result:
                key, value = result
                self.data[key] = value
                logger.debug(f'======= {finish_num}/{all_num}: "{key}" finished ========')
            else:
                # error in thread or invalid return
                logger.debug(f'======= There is a thread went wrong, {finish_num}/{all_num} ========')
            finish_num += 1
        logger.info(f'All {all_num} wikitext downloaded.')
        self.data = dict([(k, self.data[k]) for k in sorted(self.data.keys())])
        return self.data

    @abc.abstractmethod
    @catch_exception
    def _parse_one(self, key: Any) -> Tuple[Any, Any]:
        """One job for one record. Return (key, result) tuple.

        If works > 1, jobs are run in multi-threading, decorate method with `@catch_exception` and
        set friendly thread name at the start, so that decorator will know which thread went wrong.
        """
        return key, "value"

    def dump(self, fp: str):
        dump_json(self.data, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
