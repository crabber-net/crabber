import datetime
import os
import platform
from typing import Dict, List, Set


def load_usernames_from_file(filename: str) -> List[str]:
    """
    Load list of usernames from file.
    :param filename: Filename without path or extension (assumes app root and cfg)
    :return: List of usernames as they appear in file
    """
    with open(f"{os.path.join(BASE_PATH, filename)}.cfg", "r") as f:
        return [username.strip() for username in f.read().strip().splitlines()]

def load_banners() -> Dict[str, str]:
    banner_path = os.path.join(BASE_PATH, 'static', 'img', 'banners')
    banner_files = [os.path.join(banner_path, file)
                    for file in os.listdir(banner_path)
                    if os.path.splitext(file)[-1].lower() in ('.mp4', '.webm')]
    # Create dict of {banner name: banner path}
    banners = {os.path.splitext(os.path.basename(file))[0]:
               os.path.relpath(file, start='static')
               for file in banner_files}
    return banners

# Check if running on production server or local development
is_debug_server = platform.node() != 'crabbyboi'

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MOLT_CHAR_LIMIT: int = 240
MOLTS_PER_PAGE: int = 20
NOTIFS_PER_PAGE: int = 20
MINUTES_EDITABLE: int = 5
ADMINS: List[str] = load_usernames_from_file("admins")  # Users allowed to access the Tortimer page
UPLOAD_FOLDER: str = os.path.join(BASE_PATH, 'static/img/user_uploads')
ALLOWED_EXTENSIONS: Set[str] = {'png', 'jpg', 'jpeg'}
RECOMMENDED_USERS: List[str] = load_usernames_from_file("recommended_users")  # Users suggested on post-signup page
BASE_URL = "http://localhost" if is_debug_server else "https://crabber.net"
SERVER_START = round(datetime.datetime.utcnow().timestamp())  # Timestamp of when the server went up
FEATURED_MOLT_ID = 1
FEATURED_CRAB_USERNAME = 'jake'
ANIMATED_BANNERS = load_banners()
print(f'{ANIMATED_BANNERS=}')

API_DEFAULT_CRAB_LIMIT = 10
API_MAX_CRAB_LIMIT = 50
API_DEFAULT_MOLT_LIMIT = 10
API_MAX_MOLT_LIMIT = 50
API_MAX_DEVELOPER_KEYS = 5
API_MAX_ACCESS_TOKENS = 5
API_RATE_LIMIT_SECOND = 2
API_RATE_LIMIT_MINUTE = 20
API_RATE_LIMIT_HOUR = 1000
