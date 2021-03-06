## **Note: Script still works, however I just discovered a much larger, more complete, and neater dataset was very recently put up by the NCAA and Sportradar on Google Cloud/BigQuery [link](https://console.cloud.google.com/launcher/details/ncaa-bb-public/ncaa-basketball). Discovered due to [a post on reddit.com/r/dataisbeautiful by user /u/minimaxir](https://www.reddit.com/r/dataisbeautiful/comments/837qnu/heat_map_of_1058383_basketball_shots_from_ncaa/)**

# Shot Scraper
Parsing play by play and shot location info from ESPN for NCAA Men's College Basketball

**Warning:** I've implemented a five second delay before each page request, in order to not bombard any servers. With about 350 conference teams and an average of 30 games per team, this script can take a very long time to run.
I highly recommend not running it on a personal computer. Some sort of virtual machine, either local or cloud (AWS was my choice), that can be left on for a long time would be much better suited to the task.

## About
A Python script to crawl through games for all NCAA Men's College Basketball conference teams, parsing shot information from play by plays and shotmaps.

## Setup
Written in Python 3

Required packages can be found in `requirements.txt` and installed using `pip install -r requirements.txt`

## Future
Just some ideas I have for future improvements/additions

- Wrap whole process in a single function and add arguments
  - Argument for specifying season/year
  - Updating database vs initializing
- Add some type of log keeping for when shotmap count and play by play count don't match, and other errors
  - Maybe by using decorators?
- Add check to make sure game has ended (checking for 'Final' near top of page). Games still being played don't look any different from just the url perspective
- Format to work as in installable python package?
