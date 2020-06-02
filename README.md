# crabber
Twitter clone written in Python using Flask.

[Visit the official live site at crabber.net](https://crabber.net/)
![screenshot of crabber.net](https://i.imgur.com/8PvtcVF.png)

*Disclaimer: Code still needs documentation and a proper REST API.*

## Installation
1. Clone the repo  
`git clone https://github.com/jakeledoux/crabber.git`
2. Create a python3 virtual environment and install the requirements  
`pip3 install -r requirements.txt`
3. Setup the database  
`python3 initialize_database.py`
4. Add any site administrators to `admins.cfg` via their usernames

## Running
Simply run `crabber.py` in your configured environment.  
`python3 crabber.py`
