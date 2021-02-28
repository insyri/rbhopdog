# rbhop_api.py
import datetime
from discord.errors import InvalidData
from dotenv import load_dotenv
from enum import Enum
import json
import os
import requests
from requests.models import Response
from typing import Dict, List, Optional, Tuple, Union

from modules.utils import Incrementer

load_dotenv()
API_KEY = os.getenv("API_KEY")

URL = "https://api.strafes.net/v1/"

headers = {
    "api-key":API_KEY,
}

def fix_path(path):
    return os.path.abspath(os.path.expanduser(path))

def open_json(path):
    with open(fix_path(path)) as file:
        data = file.read()
        return json.loads(data)

def get(end_of_url, params) -> Response:
    return requests.get(URL + end_of_url, headers=headers, params=params)

class Time:
    def __init__(self, millis:int):
        self.millis = millis
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
        self.timestamp:int = timestamp
        self._date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def __str__(self):
        return self._date_str

def create_str_to_val(dict):
    str_to_val = {}
    for key, values in dict.items():
        for value in values:
            str_to_val[value] = key
    return str_to_val

_GAMES = {
    0: ["maptest"],
    1: ["bhop"],
    2: ["surf"]
}
_STR_TO_GAME = create_str_to_val(_GAMES)

class Game(Enum):
    MAPTEST = 0
    BHOP = 1
    SURF = 2

    @property
    def name(self):
        return _GAMES[self.value][0]

    def __str__(self):
        return self.name

    @staticmethod
    def contains(obj):
        return obj in Game._value2member_map_ if isinstance(obj, int) else obj in _STR_TO_GAME

setattr(Game, "__new__", lambda cls, value: super(Game, cls).__new__(cls, _STR_TO_GAME[value] if isinstance(value, str) else value))
DEFAULT_GAMES:List[Game] = [Game.BHOP, Game.SURF]

_STYLES = {
    1: ["autohop", "auto", "a"],
    2: ["scroll", "s"],
    3: ["sideways", "sw"],
    4: ["half-sideways", "hsw", "half"],
    5: ["w-only", "wonly", "wo", "w"],
    6: ["a-only", "aonly", "ao"],
    7: ["backwards", "bw"],
    8: ["faste"]
}
_STR_TO_STYLE = create_str_to_val(_STYLES)

class Style(Enum):
    AUTOHOP = 1
    SCROLL = 2
    SIDEWAYS = 3
    HSW = 4
    WONLY = 5
    AONLY = 6
    BACKWARDS = 7
    FASTE = 8

    @property
    def name(self):
        return _STYLES[self.value][0]
        
    def __str__(self):
        return self.name

    @staticmethod
    def contains(obj):
        return obj in Style._value2member_map_ if isinstance(obj, int) else obj in _STR_TO_STYLE

# This allows us to get an enum via the value, name, or name alias (ex. Style(1), Style("autohop"), Style("auto"))
setattr(Style, "__new__", lambda cls, value: super(Style, cls).__new__(cls, _STR_TO_STYLE[value] if isinstance(value, str) else value))
DEFAULT_STYLES:List[Style] = [style for style in Style if style != Style.FASTE]

class Map:
    bhop_map_pairs:List[Tuple[str, "Map"]] = []
    surf_map_pairs:List[Tuple[str, "Map"]] = []
    bhop_map_count:int = 0
    surf_map_count:int = 0
    # hash table for id -> displayname because each id is unique
    map_lookup:Dict[int, "Map"] = {}

    def __init__(self, id, displayname, creator, game, date, playcount):
        self.id:int = id
        self.displayname:str = displayname
        self.creator:str = creator
        self.game:Game = game
        self.date:Date = date
        self.playcount:int = playcount

    def __str__(self):
        return self.displayname

    @staticmethod
    def from_dict(d) -> "Map":
        return Map(
            d["ID"],
            d["DisplayName"],
            d["Creator"],
            Game(d["Game"]),
            Date(d["Date"]),
            d["PlayCount"]
        )

    @staticmethod
    def write_maps(game:Game):
        page = Incrementer(1)
        first = get("map", {
            "game":game.value,
            "page":page.increment()
        })
        map_data = first.json()
        page_count = int(first.headers["Pagination-Count"])
        while page.get() <= page_count:
            map_data += get("map", {
                "game":game.value,
                "page":page.increment()
            }).json()
        with open(fix_path(f"files/{game.name}_maps.json"), "w") as file:
            json.dump(map_data, file)

    @staticmethod
    def setup_maps():
        try:
            bhop_maps = open_json("files/bhop_maps.json")
            surf_maps = open_json("files/surf_maps.json")
        except:
            Map.write_maps(Game.BHOP)
            Map.write_maps(Game.SURF)
            bhop_maps = open_json("files/bhop_maps.json")
            surf_maps = open_json("files/surf_maps.json")

        Map.bhop_map_count = len(bhop_maps)
        Map.surf_map_count = len(surf_maps)

        Map.bhop_map_pairs.clear()
        Map.surf_map_pairs.clear()
        Map.map_lookup.clear()

        for m in bhop_maps:
            map = Map.from_dict(m)
            Map.bhop_map_pairs.append((map.displayname.lower(), map))
            Map.map_lookup[map.id] = map
        Map.bhop_map_pairs.sort(key=lambda i: i[0])

        for m in surf_maps:
            map = Map.from_dict(m)
            Map.surf_map_pairs.append((map.displayname.lower(), map))
            Map.map_lookup[map.id] = map
        Map.surf_map_pairs.sort(key=lambda i: i[0])

    @staticmethod
    def update_maps():
        Map.write_maps(Game.BHOP)
        Map.write_maps(Game.SURF)
        Map.setup_maps()

    # ls should be sorted
    # performs an iterative binary search
    # returns the first index where the item was found according to the compare function
    @staticmethod
    def _find_item(ls, compare):
        left = 0
        right = len(ls) - 1
        while left <= right:
            middle = (left + right) // 2
            res = compare(ls[middle])
            if res == 0:
                return middle
            elif res < 0:
                left = middle + 1
            else:
                right = middle - 1
        return -1

    @staticmethod
    def _compare_maps(name, map_name):
        if map_name.startswith(name):
            return 0
        elif map_name < name:
            return -1
        else:
            return 1

    @staticmethod
    def _from_name(name, ls):
        name = name.lower()
        idx = Map._find_item(ls, lambda m : Map._compare_maps(name, m[0]))
        if idx != -1:
            while idx > 0:
                if ls[idx-1][0].startswith(name):
                    idx -= 1
                else:
                    break
            return ls[idx][1]
        else:
            return None

    @staticmethod
    def from_name(map_name:str, game:Game) -> Optional["Map"]:
        if game == Game.BHOP:
            return Map._from_name(map_name, Map.bhop_map_pairs)
        elif game == Game.SURF:
            return Map._from_name(map_name, Map.surf_map_pairs)
        return None

    @staticmethod
    def from_id(map_id:int) -> "Map":
        try:
            return Map.map_lookup[map_id]
        except KeyError:
            return Map(-1, "Missing map", "", Game.BHOP, -1, -1)

Map.setup_maps()

class Rank:
    __ranks__ = ("New","Newb","Bad","Okay","Not Bad","Decent","Getting There","Advanced","Good","Great","Superb","Amazing","Sick","Master","Insane","Majestic","Baby Jesus","Jesus","Half God","God")

    def __init__(self, rank, skill, placement, user):
        self.rank:int = rank
        self.skill:float = skill
        self.placement:int = placement
        self.user:User = user
        self._rank_string = Rank.__ranks__[self.rank - 1]

    def __str__(self):
        return self._rank_string

    @staticmethod
    def from_dict(data, user:"User"):
        return Rank(
            1 + int(float(data["Rank"]) * 19),
            round(float(data["Skill"]) * 100.0, 3),
            data["Placement"],
            user
        )

class Record:
    def __init__(self, id, time, user, map, date, style, mode, game):
        self.id:int = id
        self.time:Time = time
        self.user:User = user
        self.map:Map = map
        self.date:Date = date
        self.style:Style = style
        self.mode:int = mode
        self.game:Game = game
        self.diff:float = -1.0
        self.previous_record:Record = None

    def __str__(self):
        return f"Time: {self.time}\nMap: {self.map}\nUser: {self.user}\nGame: {self.game}, style: {self.style}"

    #include user or map if they are known already
    @staticmethod
    def from_dict(d, user:"User"=None, map:Map=None) -> "Record":
        if not user:
            user = User.get_user_data(d["User"])
        if not map:
            map = Map.from_id(d["Map"])
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

    #include user or map if they are known already
    @staticmethod
    def make_record_list(records:List, user:"User"=None, map:Map=None) -> List["Record"]:
        ls = []
        id_to_user = None
        if not user:
            user_ids = set()
            for record in records:
                user_ids.add(record["User"])
            id_to_user = User.get_user_data_from_list(list(user_ids))
        for record in records:
            if not user:
                ls.append(Record.from_dict(record, user=id_to_user[record["User"]], map=map))
            else:
                ls.append(Record.from_dict(record, user=user, map=map))
        return ls

class User:
    def __init__(self):
        self.id = -1
        self.username = ""
        self.displayname = ""
        self.state = UserState.DEFAULT

    def __str__(self):
        return self.username

    @staticmethod
    def from_dict(d) -> "User":
        user = User()
        user.id = d["id"]
        user.username = d["name"]
        user.displayname = d["displayName"]
        return user

    @staticmethod
    def get_user_data(user : Union[str, int]) -> "User":
        if type(user) == int:
            res = requests.get(f"https://users.roblox.com/v1/users/{user}")
            if res.status_code == 404:
                raise InvalidData("Invalid user ID")
            try:
                data = res.json()
                return User.from_dict(data)
            except:
                raise TimeoutError("Error getting user data")
        else:
            res = requests.post("https://users.roblox.com/v1/usernames/users", data={"usernames":[user]})
            d = res.json()
            if not d:
                raise TimeoutError("Error getting user data")
            else:
                data = d["data"]
                if len(data) > 0:
                    return User.from_dict(data[0])
                else:
                    raise InvalidData("Invalid username")

    @staticmethod
    def get_user_data_from_list(users:List[int]) -> Dict[int, "User"]:
        res = requests.post("https://users.roblox.com/v1/users", data={"userIds":users})
        if res:
            user_lookup = {}
            for user_dict in res.json()["data"]:
                user = User.from_dict(user_dict)
                user_lookup[user_dict["id"]] = user
            return user_lookup
        else:
            raise TimeoutError("Error getting user data")

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

def get_recent_wrs(game:Game, style:Style) -> List[Record]:
    res = get("time/recent/wr", {
        "game":game.value,
        "style":style.value
    })
    data = res.json()
    return Record.make_record_list(data)

def get_user_wrs(user_data:User, game:Game, style:Style) -> List[Record]:
    res = get(f"time/user/{user_data.id}/wr", {
        "game":game.value,
        "style":style.value
    })
    data = res.json()
    if data:
        return Record.make_record_list(data, user=user_data)
    else:
        return []

#returns a record object of a user's time on a given map
def get_user_record(user_data:User, game:Game, style:Style, map:Map) -> Optional[Record]:
    res = get(f"time/user/{user_data.id}", {
        "game":game.value,
        "style":style.value,
        "map":map.id
    })
    data = res.json()
    if len(data) == 0:
        return None
    else:
        return Record.from_dict(data[0], user=user_data)

def total_wrs(user_data:User, game:Game, style:Style) -> int:
    res = get(f"time/user/{user_data.id}/wr", {
        "game":game.value,
        "style":style.value
    })
    data = res.json()
    if data is None:
        return 0
    else:
        return len(data)

def get_user_rank(user_data:User, game:Game, style:Style) -> Optional[Rank]:
    res = get(f"rank/{user_data.id}", {
        "game":game.value,
        "style":style.value
    })
    data = res.json()
    if data is None:
        return None
    else:
        return Rank.from_dict(data, user_data)

def find_max_pages(url, params, page_count, page_length, custom_page_length) -> int:
    params["page"] = page_count
    res = get(url, params)
    data = res.json()
    if len(data) > 0:
        converted_page_count = int(((page_count - 1) * (page_length / custom_page_length)) + ((len(data) - 1) // custom_page_length) + 1)
        return converted_page_count
    else:
        return 0

#returns 25 ranks at a given page number, page 1: top 25, page 2: 26-50, etc.
def get_ranks(game:Game, style:Style, page:int) -> Tuple[List[Rank], int]:
    params = {
        "game":game.value,
        "style":style.value,
        "page":(int((page - 1) / 2)) + 1
    }
    page_length = 25
    res = get("rank", params)
    data = res.json()
    if len(data) > 0:
        page_count = int(res.headers["Pagination-Count"])
        converted_page_count = find_max_pages("rank", params, page_count, 50, page_length)
    else:
        params["page"] = 1
        first_page_res = get("rank", params)
        if len(first_page_res.json()) == 0:
            return [], 0
        else:
            page_count = int(first_page_res.headers["Pagination-Count"])
            converted_page_count = find_max_pages("rank", params, page_count, 50, page_length)
            params["page"] = page_count
            data = get("rank", params).json()
            page = converted_page_count
    ls = []
    if page % 2 == 1:
        data = data[:25]
    elif page % 2 == 0:
        data = data[25:]
    users = []
    for i in data:
        users.append(i["User"])
    user_lookup = User.get_user_data_from_list(users)
    for i in data:
        ls.append(Rank.from_dict(i, user_lookup[i["User"]]))
    return ls, converted_page_count

# TODO: optimize this pls
def get_user_times(user_data:User, game:Optional[Game], style:Optional[Style], page:int) -> Tuple[List[Record], int]:
    if page == -1:
        i = 1
        params = {"page":i}
        if game is not None:
            params["game"] = game.value
        if style is not None:
            params["style"] = style.value
        times_ls = []
        while True:
            params["page"] = i
            res = get(f"time/user/{user_data.id}", params)
            data = res.json()
            if len(data) == 0:
                break
            else:
                times_ls += data
                i += 1
        return Record.make_record_list(times_ls, user=user_data), i - 1
    page_length = 25
    page_num, start = divmod((int(page) - 1) * page_length, 200)
    end = start + 25
    params = {"page":page_num + 1}
    if game is not None:
        params["game"] = game.value
    if style is not None:
        params["style"] = style.value
    res = get(f"time/user/{user_data.id}", params) 
    data = res.json()[start:end]
    if len(data) > 0:
        page_count = int(res.headers["Pagination-Count"])
        converted_page_count = find_max_pages(f"time/user/{user_data.id}", params, page_count, 200, page_length)
    else:
        params["page"] = 1
        first_page_res = get(f"time/user/{user_data.id}", params)
        if len(first_page_res.json()) == 0:
            return [], 0
        else:
            page_count = int(first_page_res.headers["Pagination-Count"])
            converted_page_count = find_max_pages(f"time/user/{user_data.id}", params, page_count, 200, page_length)
            page_num, start = divmod((int(converted_page_count) - 1) * page_length, 200)
            end = start + 25
            params["page"] = page_count
            data = get(f"time/user/{user_data.id}", params).json()[start:end]
            print(data)
    return Record.make_record_list(data, user=user_data), converted_page_count

def get_user_completion(user_data:User, game:Game, style:Style) -> Tuple[int, int]:
    records, _ = get_user_times(user_data, game, style, -1)
    completions = len(records)
    if game == Game.BHOP:
        return completions, Map.bhop_map_count
    elif game == Game.SURF:
        return completions, Map.surf_map_count
    else:
        return completions, 1

#records is a list of records from a given map
def sort_map(records:List):
    records.sort(key=lambda i: (i["Time"], i["Date"]))

#changes a WR's diff and previous_record in place by comparing first and second place
#times on the given map
def calculate_wr_diff(record:Record):
    res = get(f"time/map/{record.map.id}", {
        "style":record.style.value,
    })
    data = res.json()
    sort_map(data)
    if len(data) > 1:
        record.previous_record = Record.from_dict(data[1])
        record.diff = round((record.previous_record.time.millis - record.time.millis) / 1000.0, 3)

def search(ls, record):
    for i in ls:
        if record["ID"] == i["ID"]:
            return i
    return None

# returns a list of lists of wrs, each list is a unique game/style combination
def get_wrs():
    wrs = []
    for game in DEFAULT_GAMES:
        for style in DEFAULT_STYLES:
            if not (game == Game.SURF and style == Style.SCROLL):
                wrs.append(get("time/recent/wr", {
                        "game":game.value,
                        "style":style.value,
                        "whitelist":True
                    }).json())
    return wrs

def write_wrs():
    with open(fix_path("files/recent_wrs.json"), "w") as file:
        json.dump(get_wrs(), file)

def get_new_wrs() -> List[Record]:
    old_wrs = []
    try:
        old_wrs = open_json("files/recent_wrs.json")
    except FileNotFoundError:
        write_wrs()
        return []
    new_wrs = get_wrs()
    globals_ls = []
    for i in range(len(new_wrs)):
        for record in new_wrs[i]:
            match = search(old_wrs[i], record)
            if match:
                #records by the same person on the same map have the same id even if they beat it
                if record["Time"] != match["Time"]:
                    r = Record.from_dict(record)
                    r.diff = round((int(match["Time"]) - int(record["Time"])) / 1000.0, 3)
                    r.previous_record = Record.from_dict(match)
                    globals_ls.append(r)
                #we can break here because the lists are sorted in the same fashion
                else:
                    break
            else:
                r = Record.from_dict(record)
                calculate_wr_diff(r)
                globals_ls.append(r)

    #overwrite recent_wrs.json with new wrs if they exist
    if len(globals_ls) > 0:
        with open(fix_path("files/recent_wrs.json"), "w") as file:
            json.dump(new_wrs, file)
    return sorted(globals_ls, key = lambda i: i.date, reverse=True)

# TODO: optimize this to reduce unnecessary api calls
def get_map_times(style:Style, map:Map, page:int) -> Tuple[List[Record], int]:
    page_length = 25
    page_num, start = divmod((int(page) - 1) * page_length, 200)
    params = {
        "style":style.value,
        "page":page_num + 1
    }
    res = get(f"time/map/{map.id}", params)
    data = res.json()
    if len(data) > 0:
        page_count = int(res.headers["Pagination-Count"])
        params["page"] = page_count
        converted_page_count = find_max_pages(f"time/map/{map.id}", params, page_count, 200, page_length)
    else:
        params["page"] = 1
        first_page_res = get(f"time/map/{map.id}", params)
        if len(first_page_res.json()) == 0:
            return [], 0
        else:
            page_count = int(first_page_res.headers["Pagination-Count"])
            params["page"] = page_count
            converted_page_count = find_max_pages(f"time/map/{map.id}", params, page_count, 200, page_length)
            data = get(f"time/map/{map.id}", params).json()
    #add the previous and next page so that we can sort the times across pages properly
    res2data = []
    if page_num > 0:
        params["page"] = page_num
        res2 = get(f"time/map/{map.id}", params)
        res2data = res2.json()
        data = res2data + data
    if page_num + 2 <= converted_page_count:
        params["page"] = page_num + 2
        res3 = get(f"time/map/{map.id}", params)
        data += res3.json()
    sort_map(data)
    if page > converted_page_count:
        start = ((int(converted_page_count) - 1) * page_length) % 200
    start += len(res2data)
    end = start + page_length
    return Record.make_record_list(data[start:end], map=map), converted_page_count

def get_user_state(user_data:User) -> Response:
    return get(f"user/{user_data.id}", {})

def get_record_placement(record:Record) -> Tuple[int, int]:
    params = {
        "style":record.style.value,
        "page":1
    }
    first_page_res = get(f"time/map/{record.map.id}", params)
    page_count = int(first_page_res.headers["Pagination-Count"])
    completions = 0
    if page_count == 1:
        completions = len(first_page_res.json())
    else:
        params["page"] = page_count
        last_page_res = get(f"time/map/{record.map.id}", params)
        completions = len(last_page_res.json()) + (page_count - 1) * 200
    return get(f"time/{record.id}/rank", {}).json()["Rank"], completions