# %matplotlib inline
from bs4 import BeautifulSoup
import requests
import pandas as pd
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import (OffsetImage, AnnotationBbox)
from math import ceil

# ## General Functions

# +
MELT_COLS = ['year', 'gender', 'team', 'opponent', 'playerNum', 'playerName', 'isMale']

REQUEST_HEADER={'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36'}
# -

# ## Polish Leagues

HEADERS = ['year', 'gender', 'team', 'opponent', 'setsPlayed', 'totalPts', 
           'serveTotal', 'servePts', 'serveErrors', 'servePtsPerSet', 
           'recTotal', 'recErrors', 'recPoor', 'recPerfect', 'recPerfectPer',
           'atkTotal', 'atkErrors', 'atkBlocked', 'atkPts', 'atkPtsPer',
           'blkPts', 'blkPtsPerSet']
YEARS = [str(year) for year in range(2008, datetime.now().year + 1)]
POL_LEAGUES = {'plusliga', 'tauronliga'}


def get_team_data(team_id: str, year: str, league: str='plusliga'):
    gender = 'male' if league == 'plusliga' else 'female'
    url = f'https://www.{league}.pl/statsTeams/tournament_1/{year}/id/{team_id}/type/teams.html'
    print(url)
    response = requests.get(url)

    print(year, league)
    soup = BeautifulSoup(response.text, 'html.parser')
    if not soup:
        print('no soup found')
        return
    table = soup.find('table', class_='rs-standings-table stats-table table table-bordered table-hover table-condensed table-striped responsive double-responsive')
    if not table: return
    
    rows = table.tbody.find_all('tr')
    if not rows: return

    team = soup.select_one('div.col-xs-12.col-sm-8.col-lg-9 h1.hidden-xs').text
    print('Team', team)

    data = []
    for row in rows[:-2]:  # ignore total and match avg rows
        cells = row.find_all(['th', 'td'])
        row_data = [year, gender, team] + [cell.get_text(strip=True) for cell in cells]
        data.append(row_data)

    return data


def get_all_team_ids(league_names: set):
    league_ids = {}
    for league in league_names:
        ids = []
        for year in YEARS:
            print('IDs for', league, 'in', year)
            year_ids = get_team_ids_from_szn(league, year)
            ids += year_ids
        league_ids[league] = list(set(ids))
    
    return league_ids


def get_team_ids_from_szn(league: str, year: str):
    url = f'https://www.{league}.pl/table/tour/{year}.html'
    response = requests.get(url)    
    soup = BeautifulSoup(response.text, 'html.parser')    
    if not soup: return []

    team_table = soup.find('table', class_='rs-standings-table table table-bordered table-hover table-condensed')
    if not team_table: return []

    teamname_anchors = team_table.find_all('a', class_='table-teamname')
    
    return [a.get('href').split('/')[3] for a in teamname_anchors]


league_ids = get_all_team_ids(POL_LEAGUES)

team_data = []
for league, ids in league_ids.items():
    tot = len(ids)
    count = 0
    for team_id in ids:
        count += 1
        print('team', count, '/', tot)
        for year in YEARS:
            d = get_team_data(team_id, year, league)
            if d: team_data.append(d)

df = pd.DataFrame(columns=HEADERS, data=team_data)

# +
df['isMale'] = df.gender.map({'Male': 1, 'Female': 0}).astype('int8')


df[['team', 'opponent', 'gender']] = df[['team', 'opponent', 'gender']].astype('string')
df.opponent = df.opponent.str.replace(' -', '')
df.opponent = df.apply(lambda row: row.opponent.replace(row.team, ''), axis=1)

int16_cols = ['year', 'setsPlayed']
df[int16_cols] = df[int16_cols].astype('int16')

int32_cols = ['totalPts', 'serveTotal', 'servePts', 'serveErrors',
              'recTotal', 'recErrors', 'recPoor', 'recPerfect',
              'atkTotal', 'atkErrors', 'atkBlocked', 'atkPts', 'blkPts']
df[int32_cols] = df[int32_cols].astype('int32')

float_cols = ['servePtsPerSet', 'recPerfectPer', 'atkPtsPer', 'blkPtsPerSet']
for col in float_cols:
    df[col] = df[col].str.replace(',', '.').astype(float)
    
df[['playerName', 'playerNum']] = np.NaN
# -

today = datetime.today().date().strftime('%Y-%m-%d')
df.to_csv(f'{today}_POLdata.csv', index=False)

melted_pol = pd.melt(df, MELT_COLS, var_name='statistic', value_name='value')

# ## OUA

# +
curr_year = datetime.now().year
YEARS = [str(x) for x in range(2009, curr_year+1)]
YEAR_STRINGS = [f'{x}-{int(x[-2:])+1}' for x in YEARS]

OUA_LEAGUES = ['wvball', 'mvball']

OUA_PLYR_HEADERS = ['year', 'gender', 'team', 'opponent', 'playerNum', 'playerName',
                   'setsPlayed', 'atkPts', 'atkErrors', 'atkTotal', 'atkPtsPer',
                   'assists',
                   'servePts', 'serveErrors', 'recErrors', 'digs',
                   'blkPts', 'blkAst', 'blkErrors', 'BHE', 'totalPts']

OUA_TEAMS = ["Queen's", 'Toronto Metropolitan', 'McMaster', 'Western', 'Guelph', 'Waterloo', 'York', 'Trent', 'RMC', 'Toronto', 'Windsor', 'Nipissing', 'Brock']

OUA_COLOURS = {"Queen's": "#FEBE10",
              'Toronto Metropolitan': "#004c9b",
              'McMaster': '#850044',
              'Western': '#4F2683',
              'Guelph': '#C20430',
              'Waterloo': '#FDD54F',
              'York': '#E31837',
              'Trent': '#154734',
              'RMC': '#ED1C24',
              'Toronto': '#1E3765',
              'Windsor': '#005596',
              'Nipissing': '#00795C',
              'Brock': '#CC0000'}


# -

def get_OUA_box_score_links(league: str, year_string: str):
    url = f'https://www.oua.ca/sports/{league}/{year_string}/schedule'

    response = requests.get(url, headers=REQUEST_HEADER)

    soup = BeautifulSoup(response.text, 'html.parser')
    if not soup:
        print('no soup found')
        return
    
    box_score_anchors = soup.find_all('a', class_='link text-nowrap btn btn-outline-secondary btn-sm my-1')

    return [a.get('href') for a in box_score_anchors if a.get('href')[-4:] == '.xml']


def get_OUA_plyr_data(url: str, year_string: str, league: str):
    year = year_string[:4]
    gender = 'Female' if league == 'wvball' else 'Male'
    isMale = 0 if gender == 'Female' else 1

    url = 'https://oua.ca' + url

    response = requests.get(url, headers=REQUEST_HEADER)

    soup = BeautifulSoup(response.text, 'html.parser')
    if not soup:
        print('no soup found')
        return

    
    sets_won = soup.find_all('span', class_='score fs-1 fw-bold')
    if not sets_won: return []
    
    home_sets_won, opp_sets_won = [int(s.text) for s in sets_won]
    sets_played = home_sets_won + opp_sets_won


    score_table = soup.find('table', class_='table table-sm table-hover mb-0')
    totalPts = []
    names = []
    for row in score_table.find_all('tr')[1:]:
        names.append(row.find('td').text.split('(')[0].strip())
        columns = row.find_all(['td', 'th'])[1:-1]
        totalPts.append(sum(int(column.text) for column in columns if column.text.isdigit()))
    home_pts, opp_pts = totalPts
    home_name, opp_name = names

    stat_tables = soup.find_all('table', class_='table')[3:-1]
    team_data = []
    for t in stat_tables:
        teamname = t.find('tr').find('h4').text.strip()
        opp = opp_name if home_name == teamname else home_name

        player_data = []
        for row in t.find_all('tr')[3:-2]:
            columns = row.find_all(['td', 'th'])
            player_row = [column.text.strip() if '\n' not in column.text.strip() else column.text.strip().split('\n')[0] for column in columns]
            player_data.append([year, gender, teamname, opp] + player_row)
        team_data.extend(player_data)
    
    return team_data


def clear_non_ints(val):
    if val.isnumeric(): return val
    else: return np.NaN


team_data = []
for league in OUA_LEAGUES:
    links = {}
    for year_string in YEAR_STRINGS:
        year_links = get_OUA_box_score_links(league, year_string)
        print(len(year_links), 'in', league, year_string)
        count = 0
        for link in year_links:
            count += 1
            if count%10 == 0: print(count)
            team_data.extend(get_OUA_plyr_data(link, year_string, league))

oua_df = pd.DataFrame(columns=OUA_PLYR_HEADERS, data=team_data)


def clean_oua_df(df):
    print(df.columns)
    print(df.team.unique())
    df.loc[df['team']=='Ryerson', 'team'] = 'Toronto Metropolitan'
    print(df.team.unique())
    
    df = df[df.team.isin(OUA_TEAMS)]

    df = df[~(df.playerNum == 'TM')]

    df['isMale'] = df.gender.map({'Male': 1, 'Female': 0}).astype('int8')
    df[['team', 'opponent', 'gender', 'playerName']] = df[['team', 'opponent', 'gender', 'playerName']].astype('string')

    df.playerNum = df.playerNum.apply(clear_non_ints)

    df = df.dropna(subset=['playerNum'])

    df = df[~(df.playerNum == np.NaN)]

    int16_cols = ['year', 'setsPlayed', 'playerNum']
    df[int16_cols] = df[int16_cols].astype('int16')

    int32_cols = ['atkPts', 'atkErrors', 'atkTotal',
                  'assists',
                  'servePts', 'serveErrors', 'recErrors', 'digs',
                  'blkPts', 'blkAst', 'blkErrors', 'BHE']
    df[int32_cols] = df[int32_cols].replace('', 0).astype('int32')

    df.atkPtsPer = df.atkPtsPer.replace('', 0).astype(float)

    df.totalPts = df.atkPts + df.blkPts + df.servePts
    
    return df


oua_df = clean_oua_df(oua_df)

today = datetime.today().date().strftime('%Y-%m-%d')
oua_df.to_csv(f'{today}_OUAdata.csv', index=False)

oua_df

melted_oua = pd.melt(oua_df, MELT_COLS, var_name='statistic', value_name='value')

# +
# get playoffs and mark matches as exhibition, reg szn, and playoffs
# make team total statistics
# -

# ## Combining Data

all_df = pd.concat([df, oua_df])

all_df

# ## Cleaning Data

# +
male_oua_data = []

league = 'mvball'
links = {}
for year_string in YEAR_STRINGS:
    year_links = get_OUA_box_score_links(league, year_string)
    print(len(year_links), 'in', league, year_string)
    count = 0
    for link in year_links:
        count += 1
        if count%10 == 0: print(count)
        male_oua_data.extend(get_OUA_plyr_data(link, year_string, league))
# -

male_oua_df = pd.DataFrame(columns=OUA_PLYR_HEADERS, data=male_oua_data)
male_oua_df = clean_oua_df(male_oua_df)

oua_df = pd.concat([oua_df[oua_df.isMale == 0], male_oua_df])

# ## Exploration

# #### Most Pts

male_oua = oua_df[oua_df.isMale == 1]
female_oua = oua_df[oua_df.isMale == 0]

men_sums = male_oua.groupby('playerName').totalPts.sum()
men_sums.sort_values(ascending=False)

fem_sums = female_oua.groupby('playerName').totalPts.sum()
fem_sums.sort_values(ascending=False)

# #### Top 5 Point Scorers by Team, in 2023

# +
# for div in male_oua, female_oua:

df = male_oua_df
df = df[df.year == 2023]

max_pts_scored = df.groupby('playerName').totalPts.sum().max()
ylim_max = max_pts_scored*1.1

team_sums = df.groupby('team').totalPts.sum()
teams = sorted(df.team.unique(), key=lambda team: team_sums.get(team, 0), reverse=True)

num_teams = len(teams)
cols = 3
rows = ceil(num_teams/3)
fig, axis = plt.subplots(rows, cols, figsize=(12, 20))
fig.suptitle('Top 5 Point Scorers per Team', fontsize=16, fontweight='bold')

curr_col = 0
for i, team in enumerate(teams):
    team_df = df[df.team == team]
    team_color = OUA_COLOURS.get(team, '#FFFFFF')

    vals = team_df.groupby('playerName').totalPts.sum().sort_values(ascending=False)
    vals = vals[:5]
    
    curr_row = i//cols+1
    curr_col = 1 if curr_col == cols else curr_col + 1
    
    ax = axis[curr_row-1, curr_col-1]
    
    ax.bar(vals.index, vals.values, color=team_color)
    ax.text(0.95, 0.95, team, transform=ax.transAxes, ha='right', va='top', fontweight='bold', color=team_color, fontsize=12)
    ax.set_ylim(0, ylim_max)
    ax.tick_params(axis='x', rotation=45, labelsize=7)

for c in range(curr_col+1, cols+1):
    plt.delaxes(axis[rows-1, c-1])
    
# add OUA logo
logo = mpimg.imread("OUA_logo.png")
ax = plt.axes([0.85, 0.93, 0.09, 0.09], frameon=True)  # Change the numbers in this array to position your image [left, bottom, width, height])
ax.imshow(logo)
ax.axis('off')  # get rid of the ticks and ticklabels
    
plt.tight_layout()
plt.subplots_adjust(top=0.95)
