from bs4 import BeautifulSoup, SoupStrainer
import requests
import lxml
import sys
import os
import re
import json

def main():
	divisions = get_teams()
	for division in divisions:
		print(divisions[division])

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
				allTeamsLinks[divisionName][link.text]["teamLink"] = link.get('href')
	return allTeamsLinks

def get_team_stats(teamName, teamLink):
	#create JSON file for given team containing stats on shots for each player
	teamLinkEx = "http://www.espn.com/mens-college-basketball/team/_/id/399/albany-great-danes"
	return "blank"

if __name__ == "__main__":
	main()