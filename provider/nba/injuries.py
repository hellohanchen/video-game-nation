import time

import requests
from bs4 import BeautifulSoup

url = "https://www.espn.com/nba/injuries"


def load_injuries():
    response = requests.get(url, headers={"Connection": "keep-alive", "Accept": "*/*", "User-Agent": "PostmanRuntime/7.34.0"})
    time.sleep(1)
    soup = BeautifulSoup(response.content)
    # all records
    records = soup.find_all(class_='Table__TBODY')

    result = {}
    for team in records:
        for player in team.contents:
            player_name = player.contents[0].contents[0].contents[0]
            status = player.contents[3].contents[0].contents[0]
            result[player_name] = status

    return result


if __name__ == '__main__':
    print(load_injuries())
