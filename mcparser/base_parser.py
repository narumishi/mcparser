import abc
import pickle
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .utils.util import *


# noinspection PyMethodMayBeStatic
class BaseParser(metaclass=abc.ABCMeta):
    def __init__(self, pkl_fn: str):
        self.src_data: pd.DataFrame = pickle.load(open(pkl_fn, 'rb'))
        self.data: Dict[int, Any] = {}

    @count_time
    def parse(self, _range: Iterable = None, workers=kWorkersNum):
        if _range is None:
            _range = self.src_data.index
        valid_index = [k for k in self.src_data.index if k in _range]
        finish_num, all_num = 0, len(valid_index)
        if workers == 1:
            for index in valid_index:
                result = self._parse_one(index)
                if result:
                    self.data[result.no] = result
                else:
                    logger.warning(f'Empty result: No.{index}')
                finish_num += 1
                logger.debug(f'======= No. {index} finished, {finish_num}/{all_num} ========')
        else:
            executor = ThreadPoolExecutor(max_workers=workers)
            for result in executor.map(self._parse_one, valid_index):
                index = valid_index[finish_num]
                if result:
                    self.data[result.no] = result
                else:
                    logger.warning(f'Empty result: No.{index}')
                finish_num += 1
                logger.debug(f'======= No. {index} finished, {finish_num}/{all_num} ========')
        logger.info(f'All {all_num} wikitext downloaded.')
        return self.data

    @abc.abstractmethod
    @catch_exception
    def _parse_one(self, index: int) -> Any:
        """One job for one record.

        If works > 1, jobs are run in multi-threading, decorate method with `@catch_exception` and
        set friendly thread name at the start, so that decorator will know which thread went wrong.
        """
        pass

    def dump(self, fp):
        dump_json(self.data, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
