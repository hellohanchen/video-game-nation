from topshot.moments.m2_load_graphql_plays import load_set_plays
from topshot.moments.m4_enrich_play_badges import enrich_plays
from topshot.moments.m5_group_by_player import group_play_by_player

if __name__ == '__main__':
    load_set_plays()
    enrich_plays()
    group_play_by_player()
