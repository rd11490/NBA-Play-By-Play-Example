import json

import pandas as pd
import urllib3

header_data = {
    'Host': 'stats.nba.com',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36',
    'Referer': 'stats.nba.com',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
}


# endpoints
def play_by_play_url(game_id):
    return "https://stats.nba.com/stats/playbyplayv2/?gameId={0}&startPeriod=0&endPeriod=14".format(game_id)


def advanced_boxscore_url(game_id, start, end):
    return "https://stats.nba.com/stats/boxscoreadvancedv2/?gameId={0}&startPeriod=0&endPeriod=14&startRange={1}&endRange={2}&rangeType=2".format(game_id, start, end)


http = urllib3.PoolManager()


def extract_data(url):
    r = http.request('GET', url, headers=header_data)
    resp = json.loads(r.data)
    results = resp['resultSets'][0]
    headers = results['headers']
    rows = results['rowSet']
    frame = pd.DataFrame(rows)
    frame.columns = headers
    return frame


def convert_time_string_to_seconds(row):
    time_string = row['PCTIMESTRING']
    period = int(row['PERIOD'])
    if period > 4:
        add = 720 * 4 + (period - 4) * (5 * 60)
    else:
        add = 720 * (period - 1)

    [min, sec] = time_string.split(":")

    min_elapsed = 11 - int(min)
    sec_elapsed = 60 - int(sec)

    row["TIME"] = (add + (min_elapsed * 60) + sec_elapsed) * 10
    return row


game_id = "0041700404"
frame = extract_data(play_by_play_url(game_id))

periods_and_time = frame[['PERIOD', 'PCTIMESTRING']]
periods_and_time = periods_and_time.apply(convert_time_string_to_seconds, axis=1)

periods_and_time = periods_and_time[periods_and_time['PERIOD'] > 1]

times = periods_and_time.groupby(by='PERIOD').head(2).groupby(by='PERIOD').tail(1)[['PERIOD', 'TIME']].values

frames = []
for t in times:
    period = t[0]
    time = t[1]
    lower = time - 9
    upper = time + 9
    frame = extract_data(advanced_boxscore_url(game_id, lower, upper))[['PLAYER_ID', 'PLAYER_NAME']]
    frame['PERIOD'] = period
    frames.append(frame)

players_on_court = pd.concat(frames)
print(players_on_court)
