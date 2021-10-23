![crabber](https://i.imgur.com/DOqc5s8.png)
A Twitter clone for crabby people.

[![](https://img.shields.io/github/languages/code-size/jakeledoux/crabber)](https://github.com/jakeledoux/crabber)
[![](https://img.shields.io/github/issues/jakeledoux/crabber)](https://github.com/jakeledoux/crabber/issues)
[![](https://img.shields.io/website?url=https%3A%2F%2Fcrabber.net)](https://crabber.net)

---

[Visit the official live site at crabber.net](https://crabber.net/)
---
## Screenshots
### Dark Mode
[![screenshot of crabber.net dark mode](https://i.imgur.com/TvRZkRk.png)](https://crabber.net/)
### Light Mode
[![screenshot of crabber.net light mode](https://i.imgur.com/fge3egY.png)](https://crabber.net/)

## Advantages

Beyond the novelty of "twitter but crab" as Crabber user @tuna so eloquently put
it, there *are* a number of advantages Crabber has over Twitter. Here are a few:

* Completely open-source and a light codebase. If you have problems you can fix
    those problems yourself and even host your own instance of the site.
* The ability to edit posts for up to five minutes after they are posted.
* A full, open REST API with an officially maintained Python client. There are
    no paywalls or massive hoops to jump through in order to use this unlike
    Twitter's API.
* Much greater privacy and absolutely no tracking.
* No sponsored posts or other advertisements (or anything else relating to
    finance).
* Proper rules and moderation preventing misinformation and hate speech.
    *(Admittedly, this is simply impossible for Twitter due to its astounding
    scale. They still lack this nonetheless.)*
* Better user page and bio customization.

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
3. (**Optional**) Download the GeoLite2 City database from [MaxMind]
(https://dev.maxmind.com/geoip/geolite2-free-geolocation-data?lang=en) 
saved as `GeoLite2-City.mmdb` in the project root to enable location bans.
4. (**Optional**)  Create a `mail_conf.json` file in the root of the project 
with the fields `address` and `password` to enable server mail for password
resets.
```json
{
    "address": "example@aol.com",
    "password": "a_secure_password"
}
```
5. Set up the database
```bash
python scripts/initialize_database.py
```
6. Add any site administrators to `admins.cfg` via their usernames
```bash
vim admins.cfg  # The only Crab-approved text editor
```
7. *(Optional)* If you want OpenGraph cards you need to set up a cron job that
   runs `fetch_cards.py` periodically.
```bash
crontab -e
```
This will open your crontab file in $EDITOR. If you're not sure how crontabs
work, add this line:
```
* * * * * cd CRABBERDIRECTORY && venv/bin/python3 fetch_cards.py
```
This will run `fetch_cards.py` in your Crabber virtual environment once every
minute. To run every five minutes change the first asterisk to `0/5`. Learn
about crontabs if you wish to make further adjustments.

## Captcha

Crabber has the option of using an invisible captcha on the signup page to
help prevent bots and spam, to enable this set the `HCAPTCHA_ENABLED` to `True`
and set the `HCAPTCHA_SITE_KEY` variable to your site key and the 
`HCAPTCHA_SECRET_KEY` to your secret key respectfully.

## Running

Simply run `crabber.py` in your configured environment and open `localhost` in
your browser, you can specify a port for the development server to run on by
setting the `PORT` environment variable, it defaults to port 80 if not set.

```
PORT=1024 python crabber.py
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
