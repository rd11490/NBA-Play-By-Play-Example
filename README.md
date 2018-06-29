## Getting the players at the start of a period:

#### Using the stats.nba API

The NBA indirectly provides the players on the court at the start of a
period through the advancedboxscorev2 endpoint. It does this by allowing
the caller to specify a start time and end time between which stats are
calculated. Because a player on the bench accumulates no stats
(in most cases) you can limit the range to only contain the first event
of a period and therefore only get the players on the court at the
start of the period. By leveraging this we can remove much of the
difficulty in determining who is on the court at a given time.

Example GET call:
```
https://stats.nba.com/stats/boxscoreadvancedv2/?gameId=0041700404&startPeriod=0&endPeriod=14&startRange=0&endRange=2147483647&rangeType=0
```


In order to use this method you need to provide set 4 parameters to non-default values:
1. gameId: The id of the game you want
2. startRange: approximately half a second before the first event of a
period in 10ths of a second (if the first event takes place at 11:43 left
in Q2, then the startRange should be `7200 + 170 - 5 = 7365`
3. startRange: approximately half a second after the first event of a
period in 10ths of a second (if the first event takes place at 11:43 left
in Q2, then the startRange should be `7200 + 170 + 5 = 7375`
4. rangeType: should always be 2


Example call:
```
https://stats.nba.com/stats/boxscoreadvancedv2/?gameId=0041700404&startPeriod=0&endPeriod=14&startRange=7300&endRange=7400&rangeType=2
```

From this call we can see that the players on the court at the start of
Q2 in game 4 of the 2018 NBA Finals were:
GSW
1. Draymond Green
2. Klay Thompson
3. Stephen Curry
4. Shaun Livingston
5. David West

CLE
1. LeBron James
2. Rodney Hood
3. Jeff Green
4. Kyle Korver
5. Larry Nance Jr.


#### Example

[Example Code](scrape_example.py)

Using Python 3.6

imports
```
import pandas as pd
import urllib3
import json
```

Set the following headers for the API calls
```
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
```

Build the urls for the play by play and the advanced box score
```
# endpoints
def play_by_play_url(game_id):
    return "https://stats.nba.com/stats/playbyplayv2/?gameId={0}&startPeriod=0&endPeriod=14".format(game_id)


def advanced_boxscore_url(game_id, start, end):
    return "https://stats.nba.com/stats/boxscoreadvancedv2/?gameId={0}&startPeriod=0&endPeriod=14&startRange={1}&endRange={2}&rangeType=2".format(game_id, start, end)
```

generate a http client
```
http = urllib3.PoolManager()
```


Function for downloading and extracting the data from a stats.nba endpoint into a dataframe
note: `results = resp['resultSets'][0]` only works because in all cases I only need the first item in the resultsSet
```
def extract_data(url):
    r = http.request('GET', url, headers=header_data)
    resp = json.loads(r.data)
    results = resp['resultSets'][0]
    headers = results['headers']
    rows = results['rowSet']
    frame = pd.DataFrame(rows)
    frame.columns = headers
    return frame
```

Function for converting the string time left in the period into total seconds elapsed
```
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

```

Given a game_id download and extract the period and time from the play by play
```
game_id = "0041700404"
frame = extract_data(play_by_play_url(game_id))

periods_and_time = frame[['PERIOD', 'PCTIMESTRING']]
periods_and_time = periods_and_time.apply(convert_time_string_to_seconds, axis=1)
```

Filter out the first period (we know the starters)
```
periods_and_time = periods_and_time[periods_and_time['PERIOD'] > 1]
```

Grab the period and time of second event in each period(the first event is always the Start of Period event
note: I know there are better ways to do this such as filtering start of period events, but this was the first I thought of.
```
times = periods_and_time.groupby(by='PERIOD').head(2).groupby(by='PERIOD').tail(1)[['PERIOD', 'TIME']].values
```


Given the period and time elapsed at the first event, extract the player
id and player name from each player on the court during that event.
```
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
```


###### Special thanks to Jason Roman of nbasense for documenting the NBA APIs

BoxScoreAdvanced:
http://nbasense.com/nba-api/Stats/Stats/Game/BoxScoreAdvanced

PlayByPlay:
http://nbasense.com/nba-api/Stats/Stats/Game/PlayByPlay