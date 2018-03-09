from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz, process
from tqdm import tqdm, trange
import requests
import lxml
import sys
import os
import re
import json
import time
import sqlite3

#allow for specifying year?
SECONDS_BETWEEN_REQUESTS = 5
DB_NAME = 'ncaam.db'

def main():
	init_database()
	conferences = get_teams()
	conn = sqlite3.connect(DB_NAME)
	cur = conn.cursor()
	customBarFormat = '{desc}{elapsed} {n_fmt}/{total_fmt}|{bar}|{postfix}'
	confBar = tqdm(list(conferences.keys()), bar_format=customBarFormat, desc="Conference")
	for c in confBar:
		confBar.set_postfix(conf=c)
		confBar.refresh()
		cur.execute("SELECT conferenceID FROM conference WHERE name=?",(c,))
		confExists = cur.fetchone()
		if not confExists:
			cur.execute("INSERT INTO conference (name) VALUES (?)",(c,))
			conn.commit()
		cur.execute("SELECT conferenceID FROM conference WHERE name=?",(c,))
		confId = cur.fetchone()[0]
		teamBar = tqdm(conferences[c].keys(), bar_format=customBarFormat, desc="Team")
		for team in teamBar:
			teamBar.set_postfix(team=team)
			teamBar.refresh()
			insert = (conferences[c][team]["teamId"],confId,team)
			cur.execute("SELECT teamID FROM team WHERE teamID=?", (conferences[c][team]["teamId"],))
			teamExists = cur.fetchone()
			if not teamExists:
				cur.execute("INSERT INTO team (teamID, conferenceID, name) VALUES (?,?,?)", insert)
				conn.commit()
			get_team_stats(conferences[c][team]['teamScheduleLink'])
		teamBar.close()
	confBar.close()
	print()
	conn.close()

def init_database():
	conn = sqlite3.connect(DB_NAME)
	cur = conn.cursor()
	cur.execute("""DROP TABLE IF EXISTS conference""")
	cur.execute("""CREATE TABLE conference
				(conferenceID INTEGER PRIMARY KEY NOT NULL,
				name TEXT)""")
	cur.execute("INSERT INTO conference (name) VALUES (?)",("Other",))

	cur.execute("""DROP TABLE IF EXISTS team""")
	cur.execute("""CREATE TABLE team
				(teamID INTEGER PRIMARY KEY NOT NULL,
				conferenceID INTEGER NOT NULL,
				name TEXT,
				FOREIGN KEY (conferenceID) REFERENCES conference(conferenceID))""")

	cur.execute("""DROP TABLE IF EXISTS player""")
	cur.execute("""CREATE TABLE player
				(playerID INTEGER PRIMARY KEY NOT NULL,
				playerName TEXT,
				teamID INTEGER NOT NULL,
				FOREIGN KEY (teamID) REFERENCES team(teamID))""")

	cur.execute("""DROP TABLE IF EXISTS game""")
	cur.execute("""CREATE TABLE game
				(gameID INTEGER PRIMARY KEY NOT NULL,
				homeTeamID INTEGER,
				awayTeamId INTEGER,
				homeTeamName TEXT,
				awayTeamName TEXT,
				gameLink TEXT,
				FOREIGN KEY (homeTeamID) REFERENCES team(teamID),
				FOREIGN KEY (awayTeamID) REFERENCES team(teamID))""")

	cur.execute("""DROP TABLE IF EXISTS shot""")
	cur.execute("""CREATE TABLE shot
				(shotID INTEGER PRIMARY KEY NOT NULL,
				gameID INTEGER NOT NULL,
				playerID INTEGER,
				playerName TEXT,
				assistID INTEGER,
				assistName TEXT,
				gamePeriod INTEGER,
				gameMinutes INTEGER,
				gameSeconds INTEGER,
				type TEXT,
				shotNumber INTEGER,
				made INTEGER,
				teamScore INTEGER,
				xPos REAL,
				yPos REAL,
				FOREIGN KEY (gameID) REFERENCES game(gameID),
				FOREIGN KEY (playerID) REFERENCES player(playerID))""")

	conn.commit()
	cur.close()

def get_teams():
	#return list of each team and link to their page on ESPN
	teamsPageLink = 'http://www.espn.com/mens-college-basketball/teams'
	time.sleep(SECONDS_BETWEEN_REQUESTS)
	teamsPage = requests.get(teamsPageLink)
	allTeamsLinks = {}
	teamLinkPattern = re.compile(r'mens-college-basketball/team/_/id/([0-9]+)/[a-z-]+')
	for division in BeautifulSoup(teamsPage.text, 'lxml').find_all('div', class_='mod-teams-list-medium'):
		divisionName = division.find('div', class_='mod-header').find('h4').text
		allTeamsLinks[divisionName] = {}
		divisionLinksDiv = division.find('div', class_='mod-content')
		for link in divisionLinksDiv.find_all('a'):
			if teamLinkPattern.search(link.get('href')):
				allTeamsLinks[divisionName][link.text] = {}
				allTeamsLinks[divisionName][link.text]["teamScheduleLink"] = 'schedule/_'.join(link.get('href').split('_'))
				allTeamsLinks[divisionName][link.text]["teamId"] = int(teamLinkPattern.search(link.get('href')).group(1))
				#note: schedule link can have team name at end, but doesn't need it
	return allTeamsLinks

def get_team_stats(teamScheduleLink):
	#some games/teams don't have the nice little court map
	#check for those and instead use just the timeline to extract shot info
	#wont have court location info
	games = get_games(teamScheduleLink)
	customBarFormat = '{desc}{elapsed} {n_fmt}/{total_fmt}|{bar}|{postfix}'
	gameBar = tqdm(games, bar_format=customBarFormat, desc="Game")
	for game in gameBar:
		parse_game(game)

def get_games(teamScheduleLink):
	#return a list of game links given a teams schedule page
	time.sleep(SECONDS_BETWEEN_REQUESTS)
	schedulePage = requests.get(teamScheduleLink)
	gameLinks = []
	gameRecapPattern = re.compile(r'ncb/recap/_/gameId/[0-9]+')
	for link in BeautifulSoup(schedulePage.text, 'lxml').find_all('a', href=True):
		if gameRecapPattern.search(link.get('href')):
			gameLinks.append(re.sub(r'\D+', 'http://www.espn.com/mens-college-basketball/playbyplay?gameId=', link.get('href')))
	return gameLinks

def parse_game(gameLink):
	#parse a given game
	conn = sqlite3.connect(DB_NAME)
	cur = conn.cursor()
	gameId = int(re.search(r'gameId=([0-9]+)',gameLink).group(1))
	cur.execute("SELECT gameID FROM game WHERE gameID=?", (gameId,))
	gameExists = cur.fetchone()
	if not gameExists:
		boxscoreLink = 'http://www.espn.com/mens-college-basketball/boxscore?gameId={}'.format(gameId)
		time.sleep(SECONDS_BETWEEN_REQUESTS)
		boxscorePage = requests.get(boxscoreLink)
		boxscoreSoup = BeautifulSoup(boxscorePage.text, 'lxml')
		time.sleep(SECONDS_BETWEEN_REQUESTS)
		gamePage = requests.get(gameLink)
		soupPage = BeautifulSoup(gamePage.text, 'lxml')
		scripts = soupPage.find_all('script', type='text/javascript')
		homeId = awayId = None
		homeIdPattern = re.compile(r'espn\.gamepackage\.homeTeamId = "([0-9]+)"')
		awayIdPattern = re.compile(r'espn\.gamepackage\.awayTeamId = "([0-9]+)"')
		for script in scripts:
			homeIdCheck = homeIdPattern.search(script.text)
			if homeIdCheck:
				homeId = int(homeIdCheck.group(1))
			awayIdCheck = awayIdPattern.search(script.text)
			if awayIdCheck:
				awayId = int(awayIdCheck.group(1))
		homeName = soupPage.select('div.team.home div.team-info-wrapper span.long-name')[0].text
		awayName = soupPage.select('div.team.away div.team-info-wrapper span.long-name')[0].text
		cur.execute("SELECT teamID FROM team WHERE teamID=?", (homeId,))
		homeExists = cur.fetchone()
		if not homeExists:
			cur.execute("INSERT INTO team (teamID, conferenceID, name) VALUES (?,?,?)", (homeId, 1, homeName))
		cur.execute("SELECT teamID FROM team WHERE teamID=?", (awayId,))
		awayExists = cur.fetchone()
		if not awayExists:
			cur.execute("INSERT INTO team (teamID, conferenceID, name) VALUES (?,?,?)", (awayId, 1, awayName))
		conn.commit()

		homeTeam = awayTeam = {}
		homeTeamLinks = [link.get('href') for link in boxscoreSoup.select('div#gamepackage-boxscore-module div.column-one td.name a')]
		awayTeamLinks = [link.get('href') for link in boxscoreSoup.select('div#gamepackage-boxscore-module div.column-two td.name a')]
		customBarFormat = '{desc}{elapsed} {n_fmt}/{total_fmt}|{bar}|{postfix}'
		homeTeamBar = tqdm(homeTeamLinks, bar_format=customBarFormat, desc="Home Team")
		for link in homeTeamBar:
			playerId = int(re.search(r'id/([0-9]+)', link).group(1))
			cur.execute("SELECT playerName FROM player WHERE playerID=?", (playerId,))
			playerExists = cur.fetchone()
			if not playerExists:
				time.sleep(SECONDS_BETWEEN_REQUESTS)
				playerPage = requests.get(link)
				playerName = BeautifulSoup(playerPage.text, 'lxml').select('div.mod-content h1')[0].text
				homeTeam[playerName] = playerId
				cur.execute("INSERT INTO player (playerID, playerName, teamID) VALUES (?,?,?)",(playerId, playerName, homeId))
			else:
				homeTeam[playerExists[0]] = playerId
		homeTeamBar.close()
		awayTeamBar = tqdm(awayTeamLinks, bar_format=customBarFormat, desc="Away Team")
		for link in awayTeamBar:
			playerId = int(re.search(r'id/([0-9]+)', link).group(1))
			cur.execute("SELECT playerName FROM player WHERE playerID=?", (playerId,))
			playerExists = cur.fetchone()
			if not playerExists:
				time.sleep(SECONDS_BETWEEN_REQUESTS)
				playerPage = requests.get(link)
				playerName = BeautifulSoup(playerPage.text, 'lxml').select('div.mod-content h1')[0].text
				awayTeam[playerName] = playerId
				cur.execute("INSERT INTO player (playerID, playerName, teamID) VALUES (?,?,?)",(playerId, playerName, awayId))
			else:
				awayTeam[playerExists[0]] = playerId
		awayTeamBar.close()
		conn.commit()

		shotmap = BeautifulSoup(gamePage.text, 'lxml').find('div', id='gamepackage-shot-chart')
		playByPlay = BeautifulSoup(gamePage.text, 'lxml').find('div', id='gamepackage-play-by-play')
		hasPbp = True if playByPlay.text.strip() else False
		hasShotmap = True if shotmap.text.strip() else False
		homePbpShots = awayPbpShots = homeShotmapShots = awayShotmapShots = None
		if hasPbp:
			homePbpShots,awayPbpShots = parse_pbp(playByPlay,homeTeam,awayTeam)
		if hasShotmap:
			homeShotmapShots,awayShotmapShots = parse_shotmap(shotmap)

		cur.execute("INSERT INTO game (gameId, homeTeamId, awayTeamId, homeTeamName, awayTeamName, gameLink) VALUES (?,?,?,?,?,?)",(gameId, homeId, awayId, homeName, awayName, gameLink))

		if hasPbp and hasShotmap:
			if len(homePbpShots) == len(homeShotmapShots):
				homeShots = [(gameId,) + homePbpShots[i] + homeShotmapShots[i] for i in range(len(homePbpShots))]
				cur.executemany("INSERT INTO shot (gameID, playerID, playerName, assistID, assistName, gamePeriod, gameMinutes, gameSeconds, type, shotNumber, made, teamScore, xPos, yPos) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
								homeShots)
				conn.commit()
			else:
				print("Home shot counts DON'T match for game: {}".format(gameLink), flush=True)
			if len(awayPbpShots) == len(awayShotmapShots):
				awayShots = [(gameId,) + awayPbpShots[i] + awayShotmapShots[i] for i in range(len(awayPbpShots))]
				cur.executemany("INSERT INTO shot (gameID, playerID, playerName, assistID, assistName, gamePeriod, gameMinutes, gameSeconds, type, shotNumber, made, teamScore, xPos, yPos) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
								awayShots)
				conn.commit()
			else:
				print("Away shot counts DON'T match for game: {}".format(gameLink), flush=True)
		elif hasPbp:
			homeShots = [(gameId,) + shot for shot in homePbpShots]
			cur.executemany("INSERT INTO shot (gameID, playerID, playerName, assistID, assistName, gamePeriod, gameMinutes, gameSeconds, type, shotNumber, made, teamScore) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", homeShots)
			awayShots = [(gameId,) + shot for shot in awayPbpShots]
			cur.executemany("INSERT INTO shot (gameID, playerID, playerName, assistID, assistName, gamePeriod, gameMinutes, gameSeconds, type, shotNumber, made, teamScore) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", awayShots)
			conn.commit()
		elif hasShotmap:
			homeShots = [(gameId,) + shot for shot in homeShotmapShots]
			cur.execute("INSERT INTO shot (gameID, xPos, yPos) VALUES (?,?,?)", homeShots)
			awayshots = [(gameId,) + shot for shot in awayShotmapShots]
			cur.execute("INSERT INTO shot (gameID, xPos, yPos) VALUES (?,?,?)", awayShots)
			conn.commit()

	conn.close()

def parse_shotmap(shotmap):
	#parse a shotmap on the play-by-play page for a game
	#return two lists of shots (one for each team, home and away) with info for:
	# who, where, missed/made, shot #, type (jumper, 3 pt jumper, layup, dunk, etc.), game half
	homeShots = shotmap.select('ul.shots.home-team li')
	awayShots = shotmap.select('ul.shots.away-team li')

	coordPattern = re.compile(r'left:([0-9.]+)|top:([0-9.]+)')
	percent = re.compile(r'\w+:([0-9.]+)')
	homeShotmapShots = awayShotmapShots = []
	for shot in homeShots:
		styles = shot.get('style').split(';')
		positions = list(filter(coordPattern.match, styles))
		coord = [float(percent.match(pos).group(1))/10 for pos in positions]
		#shooter = int(shot.get('data-shooter'))
		homeShotmapShots.append((coord[0],coord[1]))
	for shot in awayShots:
		styles = shot.get('style').split(';')
		positions = list(filter(coordPattern.match, styles))
		coord = [float(percent.match(pos).group(1))/10 for pos in positions]
		#shooter = int(shot.get('data-shooter'))
		awayShotmapShots.append((coord[0],coord[1]))
	return homeShotmapShots,awayShotmapShots

def parse_pbp(pbp,homeTeam,awayTeam):
	#parse the first and second half play-by-plays for a game
	#return two lists of shots (one for each team, home and away) with info for:
	# who, missed/made, shot #, type (jumper, 3pt jumper, layup, dunk, etc.), game half, time, assist?, team score?
	isShot = re.compile(r'layup|jumper|dunk|two point tip shot', re.IGNORECASE)
	shotPatterns = [[r'layup',r'three point jumper',r'jumper',r'dunk',r'two point tip shot'],
					['Layup','Three Point Jumper','Jumper','Dunk','Two Point Tip Shot']]
	homePbpShots = awayPbpShots = []

	gamePeriods = pbp.find('ul', class_='css-accordion').find_all('table')
	homeShotIndex = awayShotIndex = 0
	shooterId = shooterName = assistedId = assistedName = None
	madeBy = re.compile(r'(.+) (made|missed)')
	assisted = re.compile(r'Assisted by (.+)\.')

	for period in range(len(gamePeriods)):
		for play in gamePeriods[period].find_all('tr')[1:]: 
			playText = play.find('td', class_='game-details').text
			if isShot.search(playText):
				shotType = None
				if madeBy.search(playText):
					shooterName = madeBy.search(playText).group(1)
				if assisted.search(playText):
					assistedName = assisted.search(playText).group(1)
				for s in range(len(shotPatterns[0])):
					if re.search(shotPatterns[0][s], playText, re.IGNORECASE):
						shotType = shotPatterns[1][s]
						break
				made = 1 if play.get('class') else 0
				time = play.find('td', class_='time-stamp').text
				minutes,seconds = int(time.split(':')[0]),int(time.split(':')[1])
				scores = play.find('td', class_='combined-score').text
				if shooterName in homeTeam:
					shotIndex = homeShotIndex
					score = int(scores.split('-')[1].strip())
					if shooterName:
						shooterName = process.extractOne(shooterName, homeTeam.keys(), scorer=fuzz.ratio)[0]
						shooterId = homeTeam[shooterName]
					if assistedName:
						assistedName = process.extractOne(assistedName, homeTeam.keys(), scorer=fuzz.ratio)[0]
						assistedId = homeTeam[assistedName]
					homePbpShots.append((shooterId,shooterName,assistedId,assistedName,period+1,minutes,seconds,shotType,homeShotIndex,made,score))
					homeShotIndex += 1
				elif shooterName in awayTeam:
					shotIndex = awayShotIndex
					score = int(scores.split('-')[0].strip())
					if shooterName:
						shooterName = process.extractOne(shooterName, awayTeam.keys(), scorer=fuzz.ratio)[0]
						shooterId = awayTeam[shooterName]
					if assistedName:
						assistedName = process.extractOne(assistedName, awayTeam.keys(), scorer=fuzz.ratio)[0]
						assistedId = awayTeam[assistedName]
					awayPbpShots.append((shooterId,shooterName,assistedId,assistedName,period+1,minutes,seconds,shotType,awayShotIndex,made,score))
					awayShotIndex += 1

	return homePbpShots,awayPbpShots

if __name__ == "__main__":
	main()