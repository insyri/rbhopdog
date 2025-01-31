# strafes_base.py
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

def create_str_to_val(dict : Dict[Any, List[str]]):
    str_to_val = {}
    for key, values in dict.items():
        for value in values:
            str_to_val[value] = key
    return str_to_val

GAME_ENUM = {
    0: ["maptest"],
    1: ["bhop"],
    2: ["surf"]
}
_STR_TO_GAME = create_str_to_val(GAME_ENUM)

class Game(Enum):
    MAPTEST = 0
    BHOP = 1
    SURF = 2

    @property
    def name(self):
        return GAME_ENUM[self.value][0]

    def __str__(self):
        return self.name

    @staticmethod
    def contains(obj) -> bool:
        return obj in Game._value2member_map_ if isinstance(obj, int) else obj in _STR_TO_GAME

setattr(Game, "__new__", lambda cls, value: super(Game, cls).__new__(cls, _STR_TO_GAME[value] if isinstance(value, str) else value))
DEFAULT_GAMES:List[Game] = [Game.BHOP, Game.SURF]

STYLE_ENUM = {
    1: ["autohop", "auto", "a"],
    2: ["scroll", "s"],
    3: ["sideways", "sw"],
    4: ["half-sideways", "hsw", "half"],
    5: ["w-only", "wonly", "wo", "w"],
    6: ["a-only", "aonly", "ao"],
    7: ["backwards", "bw"],
    8: ["faste"],
    9: ["sustain", "sus"]
}
_STR_TO_STYLE = create_str_to_val(STYLE_ENUM)

class Style(Enum):
    AUTOHOP = 1
    SCROLL = 2
    SIDEWAYS = 3
    HSW = 4
    WONLY = 5
    AONLY = 6
    BACKWARDS = 7
    FASTE = 8
    SUSTAIN = 9

    @property
    def name(self):
        return STYLE_ENUM[self.value][0]
        
    def __str__(self):
        return self.name

    @staticmethod
    def contains(obj):
        return obj in Style._value2member_map_ if isinstance(obj, int) else obj in _STR_TO_STYLE

# This allows us to get an enum via the value, name, or name alias (ex. Style(1), Style("autohop"), Style("auto"))
setattr(Style, "__new__", lambda cls, value: super(Style, cls).__new__(cls, _STR_TO_STYLE[value] if isinstance(value, str) else value))
DEFAULT_STYLES:List[Style] = [style for style in Style if style != Style.FASTE and style != Style.SUSTAIN]

class Time:
    def __init__(self, millis):
        self.millis : int = millis
        self._time_str = Time.format_time(millis)

    def __str__(self):
        return self._time_str

    @staticmethod
    def format_time(time):
        if time > 86400000:
            return ">1 day"
        millis = Time.format_helper(time % 1000, 3)
        seconds = Time.format_helper((time // 1000) % 60, 2)
        minutes = Time.format_helper((time // (1000 * 60)) % 60, 2)
        hours = Time.format_helper((time // (1000 * 60 * 60)) % 24, 2)
        if hours == "00":
            return minutes + ":" + seconds + "." + millis
        else:
            return hours + ":" + minutes + ":" + seconds

    @staticmethod
    def format_helper(time, digits):
        time = str(time)
        while len(time) < digits:
            time = "0" + time
        return time

class Date:
    def __init__(self, timestamp):
        self.timestamp : int = timestamp
        self._date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def __str__(self):
        return self._date_str

class Map:

    def __init__(self, id, displayname, creator, game, date, playcount):
        self.id : int = id
        self.displayname : str = displayname
        self.creator : str = creator
        self.game : Game = game
        self.date : Date = date
        self.playcount : int = playcount

    def __str__(self):
        return self.displayname

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other : "Map"):
        return self.id == other.id

    @staticmethod
    def from_dict(d) -> "Map":
        return Map(
            d["ID"],
            d["DisplayName"].replace(u'\u200a', ' '),
            d["Creator"],
            Game(d["Game"]),
            Date(d["Date"]),
            d["PlayCount"]
        )

class UserState(Enum):
    DEFAULT = 0
    WHITELISTED = 1
    BLACKLISTED = 2
    PENDING = 3

    @property
    def name(self):
        return super().name.lower()
        
    def __str__(self):
        return self.name

class User:
    def __init__(self):
        self.id = -1
        self.username = ""
        self.displayname = ""
        self.state = UserState.DEFAULT

    def __str__(self):
        return self.username

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    @staticmethod
    def from_dict(d) -> "User":
        user = User()
        user.id = d["id"]
        user.username = d["name"]
        user.displayname = d["displayName"]
        return user

class Rank:
    __ranks__ = ("New","Newb","Bad","Okay","Not Bad","Decent","Getting There","Advanced","Good","Great","Superb","Amazing","Sick","Master","Insane","Majestic","Baby Jesus","Jesus","Half God","God")

    def __init__(self, rank, skill, placement, user):
        self.rank : int = rank
        self.skill : float = skill
        self.placement : int = placement
        self.user : User = user
        self._rank_string = Rank.__ranks__[self.rank - 1]

    def __str__(self):
        return self._rank_string

    @staticmethod
    def from_dict(data, user : User):
        return Rank(
            1 + int(float(data["Rank"]) * 19),
            round(float(data["Skill"]) * 100.0, 3),
            data["Placement"],
            user
        )

class Record:
    def __init__(self, id, time, user, map, date, style, mode, game):
        self.id : int = id
        self.time : Time = time
        self.user : User = user
        self.map : Map = map
        self.date : Date = date
        self.style : Style = style
        self.mode : int = mode
        self.game : Game = game
        self.diff : float = -1.0
        self.previous_record: Optional[Record] = None

    def __str__(self):
        return f"Time: {self.time}\nMap: {self.map}\nUser: {self.user}\nGame: {self.game}, style: {self.style}"
    
    @staticmethod
    def from_dict(d, user : User, map : Map) -> "Record":
        return Record(
            d["ID"],
            Time(d["Time"]),
            user,
            map,
            Date(d["Date"]),
            Style(d["Style"]),
            d["Mode"],
            Game(d["Game"])
        )
