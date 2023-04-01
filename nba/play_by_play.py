#!/usr/bin/env python

# example: 0020901003

from nba_api.live.nba.endpoints import PlayByPlay

pbp = PlayByPlay('0022201118')

pbp_data = pbp.get_dict()

print(pbp_data)
