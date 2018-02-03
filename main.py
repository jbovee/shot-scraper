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
	print(get_games("http://www.espn.com/mens-college-basketball/team/schedule/_/id/2305"))

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
			gameLinks.append(re.sub(r'\D+', 'http://www.espn.com/mens-college-basketball/game?gameId=', link.get('href')))
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
	return

def parse_shotmap():
	#parse a shotmap on the play-by-play page for a game
	#return two lists of shots (one for each team, home and away) with info for:
	# who, where, missed/made, shot #, type (jumper, 3 pt jumper, layup, dunk, etc.), game half
	return

def parse_pbp():
	#parse the first and second half play-by-plays for a game
	#return two lists of shots (one for each team, home and away) with info for:
	# who, missed/made, shot #, type (jumper, 3pt jumper, layup, dunk, etc.), game half, time, assist?, team score?
	return

if __name__ == "__main__":
	main()