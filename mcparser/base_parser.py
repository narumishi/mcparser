import abc

from .utils.util import *


# noinspection PyMethodMayBeStatic
class BaseParser(metaclass=abc.ABCMeta):
    """For Svt/Craft/CmdCode parser"""

    def __init__(self):
        self.data: Dict = {}  # override to specify type

    @abc.abstractmethod
    def get_keys(self):
        pass

    @count_time
    def parse(self, _range: Iterable = None, workers=kWorkersNum):
        cls_name = self.__class__.__name__
        executor = ThreadPoolExecutor(max_workers=workers)
        all_keys = [k for k in self.get_keys() if _range is None or k in _range]
        success_keys, error_keys = [], []
        finish_num, all_num = 0, len(all_keys)

        tasks = [executor.submit(self._parse_one, key) for key in all_keys]
        for future in as_completed(tasks):
            finish_num += 1
            result = future.result()
            if result is None:
                logger.warning(f'======= {cls_name} {finish_num}/{all_num}: FAILED ========')
            else:
                key, value = result
                success_keys.append(key)
                self.data[key] = value
                logger.debug(f'======= {cls_name} {finish_num}/{all_num} success:'
                             f' No.{key} {getattr(value, "mcLink", None) or ""}')
        error_keys = [k for k in all_keys if k not in success_keys]
        logger.info(f'{cls_name}: all {all_num} wikitext parsed. {len(error_keys)} errors: {error_keys}',
                    extra=color_extra('red') if error_keys else None)
        self.data = sort_dict(self.data)
        return self.data

    @abc.abstractmethod
    @catch_exception
    def _parse_one(self, key: Any) -> MapEntry:
        """One job for one record. Return (key, result) tuple.

        If works > 1, jobs are run in multi-threading, decorate method with `@catch_exception` and
        set friendly thread name at the start, so that decorator will know which thread went wrong.
        """
        return key, "value"

    def dump(self, fp: str):
        dump_json(self.data, fp, default=lambda o: o.to_json())
        logger.info(f'{self.__class__.__name__}: dump parsed data at "{fp}"')
