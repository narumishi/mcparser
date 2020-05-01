import json
from typing import Any, List, Dict, Type  # noqas


class Jsonable:
    """ Base class of json serializable classes.

    All json serializable attributes must be initiated an instance.
    """

    def to_json(self):
        data = dict()
        for k, v in self.__dict__.items():
            if hasattr(v, 'to_json') and callable(v.to_json):
                data[k] = v.to_json()
            else:
                data[k] = v
        return data

    def from_json(self, data: Dict):
        """It's WRONG!"""
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
    def __init__(self):
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

    def from_json(self, data: Dict):
        self.attributes_from_map(data,
                                 {'servants': Servant, 'crafts': CraftEssential, 'cmdCodes': CmdCode, 'items': Item,
                                  'icons': GameIcon, 'freeQuests': Quest})
        super(GameData, self).from_json(data)


class Servant(Jsonable):
    def __init__(self):
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

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'treasureDevice': TreasureDevice, 'passiveSkills': Skill,
                                         'profiles': SvtProfileData})
        self.activeSkills = [[Skill().from_json(skill) for skill in skills] for skills in
                             data.pop('activeSkills', [[], [], []])]
        super(Servant, self).from_json(data)


class ServantBaseInfo(Jsonable):
    def __init__(self):
        self.obtain = ''
        self.rarity = 0
        self.rarity2 = 0
        self.weight = ''
        self.height = ''
        self.gender = ''
        self.illustrator = ''
        self.className = ''
        self.attribute = ''
        self.isHumanoid = False
        self.isWeakToEA = False
        self.name = ''
        self.nameJp = ''
        self.nameEn = ''
        self.illustName = ''
        self.nicknames: List[str] = []
        self.cv: List[str] = []
        self.alignments: List[str] = []
        self.traits: List[str] = []
        self.ability: Dict[str, str] = {}
        self.illust: List[Dict[str, str]] = []
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


class TreasureDevice(Jsonable):
    def __init__(self):
        self.enhanced = False
        self.state = ''
        self.openTime = ''
        self.openCondition = ''
        self.opeQuest = ''
        self.name = ''
        self.nameJp = ''
        self.upperName = ''
        self.upperNameJp = ''
        self.color = ''
        self.category = ''
        self.rank = ''
        self.typeText = ''
        self.effects: List[Effect] = []

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'effects': Effect})
        super(TreasureDevice, self).from_json(data)


class Skill(Jsonable):
    def __init__(self):
        self.state = ''
        self.openTime = ''
        self.openCondition = ''
        self.openQuest = ''
        self.enhanced = False
        self.name = ''
        self.nameJp = ''
        self.rank = ''
        self.icon = ''
        self.cd = -1
        self.effects: List[Effect] = []

    def from_json(self, data: Dict):
        self.attributes_from_list(data, {'effects': Effect})
        super(Skill, self).from_json(data)


class Effect(Jsonable):
    def __init__(self):
        self.description = ''
        self.target = ''
        self.valueType = ''
        self.lvData: List = []


class ItemCost(Jsonable):
    def __init__(self):
        self.ascension: List[List[Item]] = []
        self.skill: List[List[Item]] = []
        self.dress: List[List[Item]] = []
        self.dressName: List[str] = []
        self.dressNameJp: List[str] = []

    def from_json(self, data: Dict):
        for key in ('ascension', 'skill', 'dress'):
            self.__dict__[key] = [[Item().from_json(i) for i in ii] for ii in data.pop(key, [])]
            pass
        super(ItemCost, self).from_json(data)


class SvtProfileData(Jsonable):
    def __init__(self):
        self.profile = ''
        self.profileJp = ''
        self.condition = ''


class CraftEssential(Jsonable):
    def __init__(self):
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


class CmdCode(Jsonable):
    def __init__(self):
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


class Item(Jsonable):
    def __init__(self):
        self.id = -1
        self.name = ''
        self.rarity = 0
        self.category = 0
        self.num = 0


class Enemy(Jsonable):
    def __init__(self):
        self.name = ''
        self.shownName = ''
        self.className = ''
        self.rank = 0
        self.hp = 0


class Battle(Jsonable):
    def __init__(self):
        self.ap = 0
        self.placeJp = ''
        self.placeCn = ''
        self.enemies: List[List[Enemy]] = []

    def from_json(self, data: Dict):
        self.enemies = [[Enemy().from_json(i) for i in ii] for ii in data.pop('enemies', [])]
        super(Battle, self).from_json(data)


class Quest(Jsonable):
    def __init__(self):
        self.chapter = ''
        self.nameJp = ''
        self.nameCn = ''
        self.level = 0
        self.bondPoint = 0
        self.experience = 0
        self.qp = 0
        self.battles: List[Battle] = []


class GameIcon(Jsonable):
    def __init__(self):
        self.filename = ''
        self.url = ''


class Events(Jsonable):
    def __init__(self):
        self.limitEvents: Dict[str, LimitEvent] = {}
        self.mainRecords: Dict[str, MainRecord] = {}
        self.exchangeTickets: Dict[str, ExchangeTicket] = {}

    def from_json(self, data: Dict):
        self.attributes_from_map(data, {'limitEvents': LimitEvent, 'mainRecords': MainRecord,
                                        'exchangeTickets': ExchangeTicket})
        super(Events, self).from_json(data)


class LimitEvent(Jsonable):
    def __init__(self):
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


class MainRecord(Jsonable):
    def __init__(self):
        self.chapter = ''
        self.title = ''
        self.fullname = ''
        self.startTimeJp = ''
        self.startTimeCn = ''
        self.drops: Dict[str, int] = {}
        self.rewards: Dict[str, int] = {}


class ExchangeTicket(Jsonable):
    def __init__(self):
        self.days = 0
        self.monthJp = ''
        self.monthCn = ''
        self.items: List[str] = []


class GLPKData(Jsonable):
    def __init__(self):
        self.colNames: List[str] = []
        self.rowNames: List[str] = []
        self.coeff: List[int] = []
        self.matrix: List[List[float]] = []
        self.cnMaxColNum = 0
