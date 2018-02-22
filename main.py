from bs4 import BeautifulSoup, SoupStrainer
import requests
import lxml
import sys
import os
import re
import json

#allow for specifying year?

def main():
	'''
	divisions = get_teams()
	for division in divisions:
		print(divisions[division])
	'''

def get_teams():
	#return list of each team and link to their page on ESPN
	teamsPageLink = 'http://www.espn.com/mens-college-basketball/teams'
	teamsPage = requests.get(teamsPageLink)
	allTeamsLinks = {}
	teamLinkPattern = re.compile(r'mens-college-basketball/team/_/id/[0-9]+/[a-z-]+')
	for division in BeautifulSoup(teamsPage.text, 'lxml').find_all('div', class_='mod-teams-list-medium'):
		divisionName = division.find('div', class_='mod-header').find('h4').text
		allTeamsLinks[divisionName] = {}
		divisionLinksDiv = division.find('div', class_='mod-content')
		for link in divisionLinksDiv.find_all('a'):
			if teamLinkPattern.search(link.get('href')):
				allTeamsLinks[divisionName][link.text] = {}
				allTeamsLinks[divisionName][link.text]["teamScheduleLink"] = 'schedule/_'.join(link.get('href').split('_'))
				#note: schedule link can have team name at end, but doesn't need it
	return allTeamsLinks

def get_team_stats(teamName, teamScheduleLink):
	#create JSON file for given team containing stats on shots for each player
	#return internal JSON for team

	#some games/teams don't have the nice little court map
	#check for those and instead use just the timeline to extract shot info
	#wont have court location info
	teamEx = "http://www.espn.com/mens-college-basketball/team/schedule/_/id/2305"
	scheduleEx = "http://www.espn.com/mens-college-basketball/team/schedule/_/id/2305"
	gameRecapEx = "http://www.espn.com/ncb/recap/_/gameId/400989186"
	gameSummaryEx = "http://www.espn.com/mens-college-basketball/game?gameId=400989186"
	pbpEx = "http://www.espn.com/mens-college-basketball/playbyplay?gameId=400989186"
	return "blank"

def get_games(teamScheduleLink):
	#return a list of game links given a teams schedule page
	schedulePage = requests.get(teamScheduleLink)
	gameLinks = []
	gameRecapPattern = re.compile(r'ncb/recap/_/gameId/[0-9]+')
	for link in BeautifulSoup(schedulePage.text, 'lxml').find_all('a', href=True):
		if gameRecapPattern.search(link.get('href')):
			gameLinks.append(re.sub(r'\D+', 'http://www.espn.com/mens-college-basketball/playbyplay?gameId=', link.get('href')))
	return gameLinks

def parse_game(gameLink):
	#parse a given game
	#return a JSON element containing shot info for each player
	#include players who didn't take shots
	#list of all players can be found in button dropdown
	#<div class="team away/home">
	#	<div data-behavior="button_dropdown">
	#		<ul class="playerfilter">
	#			<li>...
	gamePage = requests.get(gameLink)
	shotmap = BeautifulSoup(gamePage.text, 'lxml').find('div', id='gamepackage-shot-chart')
	playByPlay = BeautifulSoup(gamePage.text, 'lxml').find('div', id='gamepackage-play-by-play')
	return

def parse_shotmap(shotmap):
	#parse a shotmap on the play-by-play page for a game
	#return two lists of shots (one for each team, home and away) with info for:
	# who, where, missed/made, shot #, type (jumper, 3 pt jumper, layup, dunk, etc.), game half
	homeShots = shotmap.select('ul.shots.home-team li')
	awayShots = shotmap.select('ul.shots.away-team li')

	coordPattern = re.compile(r'left:([0-9.]+)|top:([0-9.]+)')
	percent = re.compile(r'\w+:([0-9.]+)')
	homeCoord = []
	awayCoord = []
	for shot in homeShots:
		styles = shot.get('style').split(';')
		positions = list(filter(coordPattern.match, styles))
		coord = [float(percent.match(pos).group(1)) for pos in positions]
		shooter = int(shot.get('data-shooter'))
		homeCoord.append([shooter,coord[0],coord[1]])
	return

def parse_pbp(pbp):
	#parse the first and second half play-by-plays for a game
	#return two lists of shots (one for each team, home and away) with info for:
	# who, missed/made, shot #, type (jumper, 3pt jumper, layup, dunk, etc.), game half, time, assist?, team score?
	isShot = re.compile(r'layup|jumper|dunk|two point tip shot', re.IGNORECASE)
	shotPatterns = [[r'layup',r'three point jumper',r'jumper',r'dunk',r'two point tip shot'],
					['Layup','Three Point Jumper','Jumper','Dunk','Two Point Tip Shot']]
	homeTeam = {}
	awayTeam = {}
	homePbpShots = []
	awayPbpShots = []
	homeList = BeautifulSoup(game.text, 'lxml').select('div.team.home ul.playerfilter li')
	awayList = BeautifulSoup(game.text, 'lxml').select('div.team.away ul.playerfilter li')
	for player in homeList[1:]:
		homeTeam[player.select('a')[0].text] = int(player.get('data-playerid'))
	for player in awayList[1:]:
		awayTeam[player.select('a')[0].text] = int(player.get('data-playerid'))

	gamePeriods = pbp.find('ul', class_='css-accordion').find_all('table')
	homeShotIndex = awayShotIndex = 0

	for period in range(len(gamePeriods)):
		for play in gamePeriods[period].find_all('tr')[1:]: 
			playText = play.find('td', class_='game-details').text
			if isShot.search(playText):
				shotType = None
				shooter = re.match(r'(.+) (made|missed)', playText).group(1)
				for s in range(len(shotPatterns[0])):
					if re.search(shotPatterns[0][s], playText, re.IGNORECASE):
						shotType = shotPatterns[1][s]
						break
				made = True if play.get('class') else False
				time = play.find('td', class_='time-stamp').text
				minutes,seconds = int(time.split(':')[0]),int(time.split(':')[1])
				scores = play.find('td', class_='combined-score').text
				if shooter in homeTeam:
					shotIndex = homeShotIndex
					score = int(scores.split('-')[1].strip())
					homePbpShots.append([shotIndex,period+1,minutes,seconds,shooter,shotType,score,made])
					homeShotIndex += 1
				elif shooter in awayTeam:
					shotIndex = awayShotIndex
					score = int(scores.split('-')[0].strip())
					awayPbpShots.append([shotIndex,period+1,minutes,seconds,shooter,shotType,score,made])
					awayShotIndex += 1

	#for each play
	#	check if is a shot
	#		typically has words 'made', 'makes', 'missed', 'misses'
	#		has type of shot ('jumper', 'three point jumper', 'layup', 'dunk', etc)
	#		made shots always have 'scoring-play' class (free throws do too though. either filter out or also collect)
	#	store index as 'shot#' to pair with shot map
	#	get player name
	#	time of shot?
	#	check for assists, and by who?
	#	team score after shot?
	return (homePbpShots, awayPbpShots)

if __name__ == "__main__":
	main()