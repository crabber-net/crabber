import datetime
import os
from typing import List, Set


def load_usernames_from_file(filename: str) -> List[str]:
    """
    Load list of usernames from file.
    :param filename: Filename without path or extension (assumes app root and cfg)
    :return: List of usernames as they appear in file
    """
    with open(f"{os.path.join(BASE_PATH, filename)}.cfg", "r") as f:
        return [username.strip() for username in f.read().strip().splitlines()]


BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MOLT_CHAR_LIMIT: int = 240
MOLTS_PER_PAGE: int = 20
NOTIFS_PER_PAGE: int = 20
MINUTES_EDITABLE: int = 5
ADMINS: List[str] = load_usernames_from_file("admins")  # Users allowed to access the Tortimer page
UPLOAD_FOLDER: str = os.path.join(BASE_PATH, 'static/img/user_uploads')
ALLOWED_EXTENSIONS: Set[str] = {'png', 'jpg', 'jpeg'}
RECOMMENDED_USERS: List[str] = load_usernames_from_file("recommended_users")  # Users suggested on post-signup page
BASE_URL = "http://localhost" if os.name == "nt" else "https://crabber.net"
SERVER_START = round(datetime.datetime.utcnow().timestamp())  # Timestamp of when the server went up