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
    "WARRIORS": "GSW",
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
