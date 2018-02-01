from bs4 import BeautifulSoup as bs, SoupStrainer as ss
import requests
import lxml
import sys
import os
import re
import json

def main():
	teams = get_teams()
	for team,link in teams:
		get_team_stats(team, link)

def get_teams():
	#return list of each team and link to their page on ESPN

def get_team_stats(teamName, teamLink):
	#create JSON file for given team containing stats on shots for each player

if __name__ == "__main__":
	main()