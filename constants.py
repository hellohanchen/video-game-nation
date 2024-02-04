from enum import Enum

import pytz

TEAM_TRICODES = {
    "ATLANTA": "ATL",
    "HAWKS": "ATL",
    "ATL": "ATL",
    "BOSTON": "BOS",
    "CELTICS": "BOS",
    "BOS": "BOS",
    "BROOKLYN": "BKN",
    "NETS": "BKN",
    "BKN": "BKN",
    "CHARLOTTE": "CHA",
    "HORNETS": "CHA",
    "CHA": "CHA",
    "CHICAGO": "CHI",
    "BULLS": "CHI",
    "CHI": "CHI",
    "CLEVELAND": "CLE",
    "CAVALIERS": "CLE",
    "CLE": "CLE",
    "DALLAS": "DAL",
    "MAVERICKS": "DAL",
    "DAL": "DAL",
    "DENVER": "DEN",
    "NUGGETS": "DEN",
    "DEN": "DEN",
    "DETROIT": "DET",
    "PISTONS": "DET",
    "DET": "DET",
    "GOLDEN STATE": "GSW",
    "GOLDENSTATE": "GSW",
    "WARRIORS": "GSW",
    "WARRIOR": "GSW",
    "GSW": "GSW",
    "HOUSTON": "HOU",
    "ROCKETS": "HOU",
    "HOU": "HOU",
    "INDIANA": "IND",
    "PACERS": "IND",
    "IND": "IND",
    "LA CLIPPERS": "LAC",
    "CLIPPERS": "LAC",
    "LAC": "LAC",
    "LA LAKERS": "LAL",
    "LAKERS": "LAL",
    "LAL": "LAL",
    "MEMPHIS": "MEM",
    "GRIZZLIES": "MEM",
    "MEM": "MEM",
    "MIAMI": "MIA",
    "HEAT": "MIA",
    "MIA": "MIA",
    "MILWAUKEE": "MIL",
    "BUCKS": "MIL",
    "MIL": "MIL",
    "MINNESOTA": "MIN",
    "TIMBERWOLVES": "MIN",
    "MIN": "MIN",
    "NEW ORLEANS": "NOP",
    "PELICANS": "NOP",
    "NOP": "NOP",
    "NEW YORK": "NYK",
    "KNICKS": "NYK",
    "NYK": "NYK",
    "OKLAHOMA CITY": "OKC",
    "THUNDER": "OKC",
    "OKC": "OKC",
    "ORLANDO": "ORL",
    "MAGIC": "ORL",
    "ORL": "ORL",
    "PHILADELPHIA": "PHI",
    "76ERS": "PHI",
    "PHI": "PHI",
    "PHOENIX": "PHX",
    "SUNS": "PHX",
    "PHX": "PHX",
    "PORTLAND": "POR",
    "TRAIL BLAZERS": "POR",
    "POR": "POR",
    "SACRAMENTO": "SAC",
    "KINGS": "SAC",
    "SAC": "SAC",
    "SAN": "SAS",
    "ANTONIO": "SAS",
    "SPURS": "SAS",
    "SAS": "SAS",
    "TORONTO": "TOR",
    "RAPTORS": "TOR",
    "TOR": "TOR",
    "WASHINGTON": "WAS",
    "WIZARDS": "WAS",
    "WIZARD": "WAS",
    "WASH": "WAS",
    "UTAH": "UTA",
    "JAZZ": "UTA",
    "UTA": "UTA"
}

EMPTY_PLAYER_COLLECTION = {
    "dunk": 0,
    "three_pointer": 0,
    "badge": 0,
    "debut": 0,
    "assist": 0,
    "steal": 0,
    "block_shot": 0,
    "jump_shot": 0,
    "hook_shot": 0,
    "handle": 0,
    "layup": 0,
    "reel": 0,
    "team": 0
}

# Get the timezone object for New York
TZ_ET = pytz.timezone('America/New_York')
# Get the timezone object for Los_angeles
TZ_PT = pytz.timezone('America/Los_Angeles')

STATS_SCORE = {
    'points': 1.0,
    'threePointersMade': 1.0,
    'reboundsDefensive': 1.0,
    'reboundsOffensive': 2.0,
    'assists': 2.0,
    'steals': 2.5,
    'blocks': 2.5,
    'fieldGoalsMissed': -0.5,
    'freeThrowsMissed': -0.5,
    'turnovers': -2.0,
    'foulsPersonal': -1.5,
    'win': 3.0,
    'doubleDouble': 3.0,
    'tripleDouble': 6.0,
    'quadrupleDouble': 12.0,
    'fiveDouble': 24.0
}
STATS_PLAY_TYPE = {
    'points': 'dunk',
    'threePointersMade': 'three_pointer',
    'reboundsDefensive': 'badge',
    'reboundsOffensive': 'debut',
    'assists': 'assist',
    'steals': 'steal',
    'blocks': 'block_shot',
    'fieldGoalsMissed': 'jump_shot',
    'freeThrowsMissed': 'hook_shot',
    'turnovers': 'handle',
    'foulsPersonal': 'layup',
    "win": "team"
}

NBA_TEAMS = {
    "ATL": 1610612737,
    "BOS": 1610612738,
    "BKN": 1610612751,
    "CHA": 1610612766,
    "CHI": 1610612741,
    "CLE": 1610612739,
    "DAL": 1610612742,
    "DEN": 1610612743,
    "DET": 1610612765,
    "GSW": 1610612744,
    "HOU": 1610612745,
    "IND": 1610612754,
    "LAC": 1610612746,
    "LAL": 1610612747,
    "MEM": 1610612763,
    "MIA": 1610612748,
    "MIL": 1610612749,
    "MIN": 1610612750,
    "NOP": 1610612740,
    "NYK": 1610612752,
    "OKC": 1610612760,
    "ORL": 1610612753,
    "PHI": 1610612755,
    "PHX": 1610612756,
    "POR": 1610612757,
    "SAC": 1610612758,
    "SAS": 1610612759,
    "TOR": 1610612761,
    "UTA": 1610612762,
    "WAS": 1610612764
}

NBA_TEAM_IDS = {
    1610612737: "ATL",
    1610612738: "BOS",
    1610612751: "BKN",
    1610612766: "CHA",
    1610612741: "CHI",
    1610612739: "CLE",
    1610612742: "DAL",
    1610612743: "DEN",
    1610612765: "DET",
    1610612744: "GSW",
    1610612745: "HOU",
    1610612754: "IND",
    1610612746: "LAC",
    1610612747: "LAL",
    1610612763: "MEM",
    1610612748: "MIA",
    1610612749: "MIL",
    1610612750: "MIN",
    1610612740: "NOP",
    1610612752: "NYK",
    1610612760: "OKC",
    1610612753: "ORL",
    1610612755: "PHI",
    1610612756: "PHX",
    1610612757: "POR",
    1610612758: "SAC",
    1610612759: "SAS",
    1610612761: "TOR",
    1610612762: "UTA",
    1610612764: "WAS",
}


class GameDateStatus(Enum):
    INIT = 0
    PRE_GAME = 1
    IN_GAME = 2
    POST_GAME = 3
    NO_GAME = 4


INVALID_ID: int = 0
