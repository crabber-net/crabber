import datetime
import os
import platform
from typing import List, Set


def load_lines_from_file(filename: str) -> List[str]:
    """ Loads lines from file into a list of strings.
        :param filename: Filename without path or extension (assumes app root
         location and cfg extension)
        :return: List of strings as they appear in file
    """
    with open(f"{os.path.join(BASE_PATH, filename)}.cfg", "r") as f:
        return [line.strip() for line in f.read().strip().splitlines()]


# Check if running on production server or local development
is_debug_server = platform.node() != 'crabbyboi'

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MOLT_CHAR_LIMIT: int = 280
MOLTS_PER_PAGE: int = 20
NOTIFS_PER_PAGE: int = 20
MINUTES_EDITABLE: int = 5
MUTED_WORDS_CHAR_LIMIT: int = 2048
ADMINS: List[str] = load_lines_from_file("admins")  # Users allowed to access the Tortimer page
UPLOAD_FOLDER: str = os.path.join(BASE_PATH, 'static/img/user_uploads')
ALLOWED_EXTENSIONS: Set[str] = {'png', 'jpg', 'jpeg'}
RECOMMENDED_USERS: List[str] = load_lines_from_file("recommended_users")  # Users suggested on post-signup page
BASE_URL = "http://localhost" if is_debug_server else "https://crabber.net"
SERVER_START = round(datetime.datetime.utcnow().timestamp())  # Timestamp of when the server went up
FEATURED_MOLT_ID = 1
FEATURED_CRAB_USERNAME = 'jake'
BLACKLIST_IP = load_lines_from_file('blacklist-ip')
BLACKLIST_POST_CODE = load_lines_from_file('blacklist-post-code')
BLACKLIST_CITY_ID = load_lines_from_file('blacklist-city')

GEO_PATH = os.path.join(BASE_PATH, 'GeoLite2-City.mmdb')
GEO_ENABLED = os.path.exists(GEO_PATH)

MAIL_JSON = os.path.join(BASE_PATH, 'mail_conf.json')
MAIL_ENABLED = os.path.exists(MAIL_JSON)

SITE_RATE_LIMIT_MINUTE = 200
SITE_RATE_LIMIT_SECOND = 10

API_RATE_LIMIT_SECOND = 2
API_RATE_LIMIT_MINUTE = 20
API_RATE_LIMIT_HOUR = 1000

API_DEFAULT_CRAB_LIMIT = 10
API_MAX_CRAB_LIMIT = 50
API_DEFAULT_MOLT_LIMIT = 10
API_MAX_MOLT_LIMIT = 50
API_MAX_DEVELOPER_KEYS = 5
API_MAX_ACCESS_TOKENS = 5

RSS_MOLT_LIMIT = 50

HCAPTCHA_ENABLED = False

LIMITS = {  "age": 4, "pronouns": 30, "quote": 140, "jam": 140, 
            "obsession": 256, "remember": 256, "emoji": 30, 
            "description": 140, "website": 140, "location": 140, 
            "display_name": 64  }
