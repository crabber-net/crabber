![crabber](https://i.imgur.com/WrhXpnX.png)
A Twitter clone for crabby people.

[![](https://img.shields.io/github/languages/code-size/jakeledoux/crabber)](https://github.com/jakeledoux/crabber)
[![](https://img.shields.io/github/issues/jakeledoux/crabber)](https://github.com/jakeledoux/crabber/issues)
[![](https://img.shields.io/website?url=https%3A%2F%2Fcrabber.net)](https://crabber.net)

---

[Visit the official live site at crabber.net](https://crabber.net/)
---
p![screenshot of crabber.net](https://i.imgur.com/3Mu5lCi.png)](https://crabber.net/)

## Installation

1. Clone the repo
```bash
git clone https://github.com/jakeledoux/crabber.git
cd crabber
```
2. Create a python3 virtual environment and install the requirements  
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Setup the database  
```bash
python scripts/initialize_database.py
```
4. Add any site administrators to `admins.cfg` via their usernames
```bash
vim admins.cfg  # The only Crab-approved text editor
```

## Running

Simply run `crabber.py` in your configured environment and open `localhost` in
your browser.

```bash
python crabber.py
```

This gets you a development server but **should not** be used in production.
Install a "real" server like Apache2, Nginx, etc.

## API

### REST

Crabber has a REST API mounted at `/api/v1` using the
[crabber_api.py](crabber_api.py) blueprint. Incomplete documentation is
available [here](https://app.swaggerhub.com/apis-docs/jakeledoux/Crabber/1.0.0).

If you are interested in contributing to the documentation please create an
issue to let us know, any help is appreciated!

### Python

A Python library has been written to simplify interaction with the site's API
and make developing bots and other applications more fun.

You can find that library [here on
PyPi](https://pypi.org/project/python-crabber/) and [its repo
here](https://github.com/jakeledoux/pythone-crabber).

```bash
pip install python-crabber
```
```python3
import crabber
api = craber.API(YOUR_API_KEY,
                 YOUR_ACCESS_TOKEN)

jake = crabber.get_crab_by_username('jake')
jake.follow()
molt = jake.get_molts()[0]
molt.like()
molt.reply('Wow, you\'re so cool!')
```
