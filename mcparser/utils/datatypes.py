import json
from typing import Any, List, Dict, Type, Optional  # noqas


class Jsonable:
    """ Base class of json serializable classes.

    All json serializable attributes must be initiated an instance.
    """

    def __init__(self, **kwargs):
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

    def to_json(self, hide_private=True):
        """Recursively convert to json object rather than string.

        :param hide_private: if True, private attributes will be ignored.
        :return: json object(dict).
        """
        # TODO: more efficient way to convert to json object
        if hide_private:
            data = {}
            for k, v in self.__dict__.items():
                if not k.startswith('_'):
                    data[k] = v
        else:
            data = self.__dict__
        return json.loads(json.dumps(data, ensure_ascii=False, default=lambda o: o.to_json()))

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
        ensure_ascii = kwargs.pop('ensure_ascii', False)
        indent = kwargs.pop('indent', 2)
        json.dump(self.to_json(), open(fp, 'w', encoding='utf8'), ensure_ascii=ensure_ascii, indent=indent, **kwargs)

    def attributes_from_map(self, data: Dict[str, Dict], cls_map: Dict[str, Type]):
        for attr, cls in cls_map.items():
            self.__dict__[attr] = dict([(k, cls().from_json(v)) for k, v in data.pop(attr, {}).items()])

    def attributes_from_list(self, data: Dict[str, List], cls_map: Dict[str, Type]):
        for attr, cls in cls_map.items():
            self.__dict__[attr] = [cls().from_json(v) for v in data.pop(attr, [])]


class GameData(Jsonable):
    def __init__(self, **kwargs):
        self.version: str = ''
        self.servants: Dict[str, Servant] = {}
        self.unavailable_svts: List[int] = []
        self.crafts: Dict[str, CraftEssential] = {}
        self.cmdCodes: Dict[str, CmdCode] = {}
        self.items: Dict[str, Item] = {}
        self.icons: Dict[str, GameIcon] = {}
        self.events = Events()
        self.freeQuests: Dict[str, Quest] = {}
        self.glpk = GLPKData()
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.version)

    def from_json(self, data: Dict):
        self.attributes_from_map(data,
                                 {'servants': Servant, 'crafts': CraftEssential, 'cmdCodes': CmdCode, 'items': Item,
                                  'icons': GameIcon, 'freeQuests': Quest})
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
        self.bondCraft: int = -1
        self.valentineCraft: List[int] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.no, self.mcLink)

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'treasureDevice': TreasureDevice, 'passiveSkills': Skill,
                                         'profiles': SvtProfileData})
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
        self.illustName = ''
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
        self.illust: List[GameIcon] = []
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
        self.openTime: Optional[str] = None
        self.openCondition: Optional[str] = None
        self.openQuest: Optional[str] = None
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
        self.openTime: Optional[str] = None
        self.openCondition: Optional[str] = None
        self.openQuest: Optional[str] = None
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
        self.target: Optional[str] = None
        self.valueType = ''
        self.lvData: List = []
        super().__init__(**kwargs)


class ItemCost(Jsonable):
    def __init__(self, **kwargs):
        self.ascension: List[List[Item]] = []
        self.skill: List[List[Item]] = []
        self.dress: List[List[Item]] = []
        self.dressName: List[str] = []
        self.dressNameJp: List[str] = []
        super().__init__(**kwargs)

    def from_json(self, data: Dict):
        for key in ('ascension', 'skill', 'dress'):
            self.__dict__[key] = [[Item().from_json(i) for i in ii] for ii in data.pop(key, [])]
            pass
        super(ItemCost, self).from_json(data)


class SvtProfileData(Jsonable):
    def __init__(self, **kwargs):
        self.profile = ''
        self.profileJp = ''
        self.condition = ''
        super().__init__(**kwargs)


class CraftEssential(Jsonable):
    def __init__(self, **kwargs):
        self.no = 0
        self.rarity = 0
        self.name = ''
        self.nameJp = ''
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
        self.characters: List[str] = []
        self.bond = -1
        self.valentine = -1
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.no, self.mcLink)


class CmdCode(Jsonable):
    def __init__(self, **kwargs):
        self.no = 0
        self.rarity = 0
        self.name = ''
        self.nameJp = ''
        self.mcLink = ''
        self.icon = ''
        self.illust = ''
        self.illustrators: List[str] = []
        self.skillIcon = ''
        self.skill = ''
        self.description = ''
        self.descriptionJp = ''
        self.obtain = ''
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
    def __init__(self, **kwargs):
        self.name = ''
        self.shownName = ''
        self.className = ''
        self.rank = 0
        self.hp = 0
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.shownName)


class Battle(Jsonable):
    def __init__(self, **kwargs):
        self.ap = 0
        self.placeJp = ''
        self.placeCn = ''
        self.enemies: List[List[Enemy]] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.placeCn)

    def from_json(self, data: Dict):
        self.enemies = [[Enemy().from_json(i) for i in ii] for ii in data.pop('enemies', [])]
        super(Battle, self).from_json(data)


class Quest(Jsonable):
    def __init__(self, **kwargs):
        self.chapter = ''
        self.nameJp = ''
        self.nameCn = ''
        self.level = 0
        self.bondPoint = 0
        self.experience = 0
        self.qp = 0
        self.battles: List[Battle] = []
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.nameCn)


class GameIcon(Jsonable):
    def __init__(self, **kwargs):
        self.filename = ''
        self.url = ''
        super().__init__(**kwargs)

    def __repr__(self):
        return self.get_repr(self.filename)


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
