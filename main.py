from bs4 import BeautifulSoup, SoupStrainer
import requests
import lxml
import sys
import os
import re
import json

def main():
	teams = get_teams()
	'''
	for team,link in teams:
		get_team_stats(team, link)
	'''

def get_teams():
	#return list of each team and link to their page on ESPN
	teamsPage = 'http://www.espn.com/mens-college-basketball/teams'
	allTeams = requests.get(teamsPage)
	allTeamsLinks = {}
	teamLinkPattern = re.compile(r'mens-college-basketball/team/_/id/[0-9]+/[a-z-]+')
	'''
	for link in BeautifulSoup(allTeams.text, 'lxml', parse_only=SoupStrainer('a', href=True)).find_all('a'):
		if teamLinkPattern.search(link.get('href')):
			allTeamsLinks[link.text] = link.get('href')
	'''
	for division in BeautifulSoup(allTeams.text, 'lxml').find_all('div', class_='mod-teams-list-medium'):
		divisionName = division.find('div', class_='mod-header').find('h4').text
		print(divisionName)

	teamLinkEx = "http://www.espn.com/mens-college-basketball/team/_/id/399/albany-great-danes"

def get_team_stats(teamName, teamLink):
	#create JSON file for given team containing stats on shots for each player
	return "blank"

if __name__ == "__main__":
	main()