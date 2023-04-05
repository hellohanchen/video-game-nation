import csv
import json
import os
import pathlib


def store_player_name_list(size):
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "result/players_2.json"), 'r') as player_file:
        players = json.load(player_file)['players']
        i = 0
        while i < len(players):
            with open(os.path.join(pathlib.Path(__file__).parent.resolve(), "resource/player_names_" + str(i) + ".csv"), 'w', newline='') as output_file:
                writer = csv.writer(output_file)
                writer.writerow(["playerName"])
                for player in players[i:i+size]:
                    writer.writerow([player['name'].replace(' ', '%20')])

            i = i + size
