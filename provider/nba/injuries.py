import time

import requests
from bs4 import BeautifulSoup

espn_url = "https://www.espn.com/nba/injuries"
cbs_url = "https://www.cbssports.com/nba/injuries/"


def load_injuries():
    response = requests.get(cbs_url, headers={"Connection": "keep-alive", "Accept": "*/*", "User-Agent": "PostmanRuntime/7.34.0"})
    time.sleep(1)
    soup = BeautifulSoup(response.content)
    # cbs teams
    teams = soup.find_all(class_='TableBase')

    result = {}
    for team in teams:
        for player in team.contents[1].contents[0].contents[0].contents[2].contents:
            player_name = player.contents[0].contents[1].contents[0].contents[0].contents[0]
            status = player.contents[4].contents[0].strip()
            if status.startswith('Expected to be out until'):
                status = f"OUT"
            elif status.startswith('Out for the season'):
                status = f"OUT"
            result[player_name] = status

    response = requests.get(espn_url, headers={"Connection": "keep-alive", "Accept": "*/*", "User-Agent": "PostmanRuntime/7.34.0"})
    soup = BeautifulSoup(response.content)
    # espn teams
    records = soup.find_all(class_='Table__TBODY')
    for team in records:
        for player in team.contents:
            player_name = player.contents[0].contents[0].contents[0]
            if player_name not in result:
                status = player.contents[3].contents[0].contents[0]
                result[player_name] = status

    return result


if __name__ == '__main__':
    print(load_injuries())
