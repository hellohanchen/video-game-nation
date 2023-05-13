from topshot.moments.m2_load_graphql_plays import load_set_plays
from topshot.moments.m4_enrich_play_badges import enrich_plays

if __name__ == '__main__':
    load_set_plays()
    enrich_plays()
