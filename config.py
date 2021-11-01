import datetime
from dotenv import load_dotenv
import os
import platform
from typing import List, Set

load_dotenv()


def getenv_bool(key, default=False):
    """ Retrieve boolean value from environment variable.
    """
    value = os.getenv(key, None)
    if value:
        if value.lower() in ('false', '0', 'off'):
            return False
        else:
            return True
    return default


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

DATABASE_PATH = (os.getenv('CRABBER_DATABASE')
                 or 'sqlite:///CRABBER_DATABASE.db')

GEO_PATH = os.path.join(BASE_PATH, 'GeoLite2-City.mmdb')
GEO_ENABLED = os.path.exists(GEO_PATH) and getenv_bool('GEO_ENABLED', True)

MAIL_ADDRESS = os.getenv('MAIL_ADDRESS')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_ENABLED = (MAIL_ADDRESS and MAIL_PASSWORD
                and getenv_bool('MAIL_ENABLED', False))

CDN_ENABLED = getenv_bool('CDN_ENABLED', False)
CDN_ACCESS_KEY = os.getenv('CDN_ACCESS_KEY')
CDN_SECRET_KEY = os.getenv('CDN_SECRET_KEY')
CDN_ENDPOINT = os.getenv('CDN_ENDPOINT')
CDN_SPACE_NAME = os.getenv('CDN_SPACE_NAME')

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

HCAPTCHA_ENABLED = getenv_bool('HCAPTCHA_ENABLED', False)
REGISTRATION_ENABLED = getenv_bool('REGISTRATION_ENABLED', True)

LIMITS = {  "age": 32, "pronouns": 64, "quote": 256, "jam": 256,
            "obsession": 256, "remember": 256, "emoji": 32,
            "description": 512, "website": 256, "location": 128,
            "display_name": 64  }
