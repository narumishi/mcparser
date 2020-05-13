import json
from typing import Any, List, Dict, Type, Optional  # noqas

from ..base.basic import dump_json


class Jsonable:
    """ Base class of json serializable classes.

    All json serializable attributes must be initiated an instance.
    """

    def __init__(self, **kwargs):
        self._ignored = []
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v
            else:
                print(f'"{k}" not in {self.__class__.__name__}')

    def get_repr(self, *args):
        if len(args) == 0:
            return f'{self.__class__.__name__}'
        else:
            return f'{self.__class__.__name__}({str(args).strip(",()")})'

    def __repr__(self):
        return self.get_repr()

    def to_json(self, skip_ignored=True, return_type='object'):
        """Recursively convert to json object or string.

        :param skip_ignored: if True, private attributes and keys in `_ignored` will be ignored.
        :param return_type: "json" - a json object,
                             "str" - a json string,
                             "object" (default) - filtrated dict object from __dict__ object
        :return: dict or str.
        """
        if skip_ignored:
            data = {}
            for k, v in self.__dict__.items():
                if not k.startswith('_') and k not in self._ignored:
                    data[k] = v
        else:
            data = self.__dict__
        if return_type == 'json':
            return json.loads(json.dumps(data, ensure_ascii=False, default=lambda o: o.to_json(skip_ignored)))
        elif return_type == 'str':
            return json.dumps(data, ensure_ascii=False, default=lambda o: o.to_json(skip_ignored))
        else:  # "object"
            return data

    def from_json(self, data: Dict):
        """List[Jsonable] and Dict[Jsonable] must be done in child class's from_json"""
        for k, v in data.items():
            if k not in self.__dict__:
                continue
            if hasattr(self.__dict__[k], 'from_json'):
                self.__dict__[k].from_json(v)
            else:
                self.__dict__[k] = v
        return self

    def load(self, fp):
        self.from_json(json.load(open(fp, encoding='utf8')))

    def dump(self, fp, **kwargs):
        dump_json(self.to_json(), fp, default=lambda o: o.to_json(), **kwargs)

    @staticmethod
    def convert_map(data: Dict[str, Dict], cls: Type, key_type=None):
        return dict([(key_type(k) if key_type is not None else k, cls().from_json(v)) for k, v in data.items()])

    @staticmethod
    def convert_list(data: List[Dict], cls: Type):
        return [cls().from_json(v) for v in data]

    def attributes_from_map(self, data: Dict[str, Dict], cls_map: Dict[str, Type], key_type=None):
        for attr, cls in cls_map.items():
            self.__dict__[attr] = Jsonable.convert_map(data.pop(attr, {}), cls, key_type)

    def attributes_from_list(self, data: Dict[str, List], cls_map: Dict[str, Type]):
        for attr, cls in cls_map.items():
            self.__dict__[attr] = Jsonable.convert_list(data.pop(attr, []), cls)


class GameData(Jsonable):
    def __init__(self, **kwargs):
        self.version: str = ''
        self.servants: Dict[int, Servant] = {}
        self.unavailable_svts: List[int] = []
        self.crafts: Dict[int, CraftEssential] = {}
        self.cmdCodes: Dict[int, CmdCode] = {}
        self.items: Dict[str, Item] = {}
        self.icons: Dict[str, FileResource] = {}
        self.events = Events()
        self.freeQuests: Dict[str, Quest] = {}
        self.glpk = GLPKData()
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.version)

    def from_json(self, data: Dict):
        self.attributes_from_map(data, {'servants': Servant, 'crafts': CraftEssential, 'cmdCodes': CmdCode}, int)
        self.attributes_from_map(data, {'items': Item, 'icons': FileResource, 'freeQuests': Quest})
        super(GameData, self).from_json(data)


class Servant(Jsonable):
    def __init__(self, **kwargs):
        self.no = 0
        self.mcLink = ''
        self.icon = ''
        self.info = ServantBaseInfo()
        self.treasureDevice: List[TreasureDevice] = []
        self.activeSkills: List[List[Skill]] = []
        self.passiveSkills: List[Skill] = []
        self.itemCost = ItemCost()
        self.bondPoints: List[int] = []
        self.profiles: List[SvtProfileData] = []
        self.voices: List[VoiceTable] = []
        self.bondCraft: int = -1
        self.valentineCraft: List[int] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.no, self.mcLink)

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'treasureDevice': TreasureDevice, 'passiveSkills': Skill,
                                         'profiles': SvtProfileData, 'voices': VoiceTable})
        self.activeSkills = [[Skill().from_json(skill) for skill in skills] for skills in
                             data.pop('activeSkills', [[], [], []])]
        super(Servant, self).from_json(data)


class ServantBaseInfo(Jsonable):
    def __init__(self, **kwargs):
        self._no = 0
        self.obtain = ''
        self.obtains: List[str] = []
        self.rarity = 0
        self.rarity2 = 0
        self.name = ''
        self.nameJp = ''
        self.nameEn = ''
        self.namesOther: List[str] = []
        self.namesJpOther: List[str] = []
        self.namesEnOther: List[str] = []
        self.nicknames: List[str] = []
        self.weight = ''
        self.height = ''
        self.gender = ''
        self.illustrator = ''
        self.className = ''
        self.attribute = ''
        self.isHumanoid = False
        self.isWeakToEA = False
        self.cv: List[str] = []
        self.alignments: List[str] = []
        self.traits: List[str] = []
        self.ability: Dict[str, str] = {}
        self.illust: Dict[str, str] = {}
        self.cards: List[str] = []
        self.cardHits: Dict[str, int] = {}
        self.cardHitsDamage: Dict[str, List[int]] = {}
        self.npRate: Dict[str, int] = {}
        self.atkMin = -1
        self.hpMin = -1
        self.atkMax = -1
        self.hpMax = -1
        self.atk90 = -1
        self.hp90 = -1
        self.atk100 = -1
        self.hp100 = -1
        self.starRate = 0
        self.deathRate = 0
        self.criticalRate = 0
        super().__init__(**kwargs)


class TreasureDevice(Jsonable):
    def __init__(self, **kwargs):
        self.state: Optional[str] = None
        self._openTime: Optional[str] = None
        self._openCondition: Optional[str] = None
        self._openQuest: Optional[str] = None
        self.name = ''
        self.nameJp = ''
        self.upperName = ''
        self.upperNameJp = ''
        self.color = ''
        self.category = ''
        self.rank = ''
        self.typeText = ''
        self.effects: List[Effect] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.state, self.name)

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'effects': Effect})
        super(TreasureDevice, self).from_json(data)


class Skill(Jsonable):
    def __init__(self, **kwargs):
        self.state = ''
        self._openTime: Optional[str] = None
        self._openCondition: Optional[str] = None
        self._openQuest: Optional[str] = None
        self.name = ''
        self.nameJp = ''
        self.rank = ''
        self.icon = ''
        self.cd = -1
        self.effects: List[Effect] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.name)

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'effects': Effect})
        super(Skill, self).from_json(data)


class Effect(Jsonable):
    def __init__(self, **kwargs):
        self.description = ''
        self._target: Optional[str] = None
        self._valueType = ''
        self.lvData: List = []
        super().__init__(**kwargs)


class ItemCost(Jsonable):
    def __init__(self, **kwargs):
        self.ascension: List[Dict[str, int]] = []
        self.skill: List[Dict[str, int]] = []
        self.dress: List[Dict[str, int]] = []
        # dresses here only contains those need items (In fact, only incomplete for mash)
        self.dressName: List[str] = []
        self.dressNameJp: List[str] = []
        super().__init__(**kwargs)

    def from_json(self, data: Dict):
        super(ItemCost, self).from_json(data)


class SvtProfileData(Jsonable):
    def __init__(self, **kwargs):
        self.title = ''
        self.description = ''
        self.descriptionJp = ''
        self.condition = ''
        super().__init__(**kwargs)


class VoiceTable(Jsonable):
    def __init__(self, **kwargs):
        self.section = ''
        self.table: List[VoiceRecord] = []
        super().__init__(**kwargs)

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'table': VoiceRecord})
        super(VoiceTable, self).from_json(data)

    def __repr__(self):
        return self.get_repr(self.section)


class VoiceRecord(Jsonable):
    def __init__(self, **kwargs):
        self.title = ''
        self.text = ''
        self.textJp = ''
        self.condition = ''
        self.file = ''
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.title)


class CraftEssential(Jsonable):
    def __init__(self, **kwargs):
        self.no = 0
        self.rarity = 0
        self.name = ''
        self.nameJp = ''
        self.nameOther: List[str] = []
        self.mcLink = ''
        self.icon = ''
        self.illust = ''
        self.illustrators: List[str] = []
        self.cost = 0
        self.hpMin = -1
        self.hpMax = -1
        self.atkMin = -1
        self.atkMax = -1
        self.skillIcon = ''
        self.skill = ''
        self.skillMax = ''
        self.eventIcons: List[str] = []
        self.eventSkills: List[str] = []
        self.description = ''
        self.descriptionJp = ''
        self.category = 0
        self.categoryText = ''
        self.characters: List[str] = []
        self.bond = -1
        self.valentine = -1
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.no, self.mcLink)


class CmdCode(Jsonable):
    def __init__(self, **kwargs):
        self.no = 0
        self.mcLink = ''
        self.rarity = 0
        self.name = ''
        self.nameJp = ''
        self.nameOther: List[str] = []
        self.icon = ''
        self.illust = ''
        self.illustrators: List[str] = []
        self.skillIcon = ''
        self.skill = ''
        self.description = ''
        self.descriptionJp = ''
        self.obtain = ''
        self.category = 0
        self.categoryText = ''
        self.characters: List[str] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.no, self.name)


class Item(Jsonable):
    def __init__(self, **kwargs):
        self.id = -1
        self.name = ''
        self.rarity = 0
        self.category = 0
        self.num = 0
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.name)


class Enemy(Jsonable):
    """Multiple-hp enemy"""

    def __init__(self, **kwargs):
        # list length must >=1
        self.name: List[str] = []
        self.shownName: List[str] = []
        self.className: List[str] = []
        self.rank: List[int] = []
        self.hp: List[int] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.shownName)

    def __bool__(self):
        return len(self.name) > 0


class Battle(Jsonable):
    def __init__(self, **kwargs):
        self.ap = 0
        self.placeJp = ''
        self.place = ''
        self.enemies: List[List[Enemy]] = []
        self.drops: Dict[str, int] = {}
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.place)

    def from_json(self, data: Dict):
        self.enemies = [[Enemy().from_json(ee) for ee in e] for e in data.pop('enemies', [])]
        super(Battle, self).from_json(data)


class Quest(Jsonable):
    def __init__(self, **kwargs):
        self.chapter = ''
        self.nameJp = ''
        self.name = ''
        self.level = 0
        self.bondPoint = 0
        self.experience = 0
        self.qp = 0
        self.isFree = False
        self.hasChoice = False  # more than 1 branch of different quest configuration
        self.battles: List[Battle] = []
        self.rewards: Dict[str, int] = {}
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.name)


class FileResource(Jsonable):
    def __init__(self, **kwargs):
        self.name = ''
        self.filename = None  # if name != filename, implement it
        self.url = ''
        self.save: bool = True
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.name)


class Events(Jsonable):
    def __init__(self, **kwargs):
        self.limitEvents: Dict[str, LimitEvent] = {}
        self.mainRecords: Dict[str, MainRecord] = {}
        self.exchangeTickets: Dict[str, ExchangeTicket] = {}
        super().__init__(**kwargs)

    def from_json(self, data: Dict):
        self.attributes_from_map(data, {'limitEvents': LimitEvent, 'mainRecords': MainRecord,
                                        'exchangeTickets': ExchangeTicket})
        super(Events, self).from_json(data)


class LimitEvent(Jsonable):
    def __init__(self, **kwargs):
        self.name = ''
        self.link = ''
        self.startTimeJp = ''
        self.endTimeJp = ''
        self.startTimeCn = ''
        self.endTimeCn = ''
        self.grail = 0
        self.crystal = 0
        self.grail2crystal = 0
        self.qp = 0
        self.items: Dict[str, int] = {}
        self.category = ''
        self.extra: Dict[str, str] = {}
        self.lottery: Dict[str, int] = {}
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.name)


class MainRecord(Jsonable):
    def __init__(self, **kwargs):
        self.chapter = ''
        self.title = ''
        self.fullname = ''
        self.startTimeJp = ''
        self.startTimeCn = ''
        self.drops: Dict[str, int] = {}
        self.rewards: Dict[str, int] = {}
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.chapter, self.title)


class ExchangeTicket(Jsonable):
    def __init__(self, **kwargs):
        self.days = 0
        self.monthJp = ''
        self.monthCn = ''
        self.items: List[str] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.monthCn, self.monthJp)


class GLPKData(Jsonable):
    def __init__(self, **kwargs):
        self.colNames: List[str] = []
        self.rowNames: List[str] = []
        self.coeff: List[int] = []
        self.matrix: List[List[float]] = []
        self.cnMaxColNum = 0
        super().__init__(**kwargs)
