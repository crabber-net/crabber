import datetime
from extensions import db
import models


def get_current_user():
    """
    Retrieves the object of the currently logged-in user by ID.
    :return: The logged in user
    """
    return models.Crab.query.filter_by(id=session.get("current_user"), deleted=False).first()


def get_pretty_age(dt: datetime.datetime) -> str:
    """
    Converts datetime to pretty twitter-esque age string.
    :param dt:
    :return: Age string
    """
    now: datetime.datetime = datetime.datetime.utcnow()
    delta = now - dt

    if delta.total_seconds() < 60:  # Less than a minute
        # Return number of seconds
        return f"{round(delta.seconds)}s"
    elif delta.total_seconds() / 60 < 60:  # Less than an hour
        # Return number of minutes
        return f"{round(delta.seconds / 60)}m"
    elif delta.seconds / 60 / 60 < 24 and delta.days == 0:  # Less than a day
        # Return number of hours
        return f"{round(delta.seconds / 60 / 60)}h"
    elif dt.year == now.year:  # Same year as now
        # Return day and month
        return localize(dt).strftime("%b %e")
    else:
        # Return day month, year
        return localize(dt).strftime("%b %e, %Y")


def allowed_file(filename: str) -> bool:
    """
    Verifies filename specified is valid and in `ALLOWED_EXTENSIONS`.
    :param filename: Filename sans-path to check
    :return: Whether it's valid
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def localize(dt: datetime.datetime) -> datetime.datetime:
    """
    Localizes datetime to user's timezone
    https://www.youtube.com/watch?v=-5wpm-gesOY

    :param dt: datetime to localize
    :return: Localized datetime
    """
    current_user = get_current_user()
    if current_user:
        new_dt = dt + current_user.timedelta
    else:
        # Defaults to Chicago time
        new_dt = dt + datetime.timedelta(hours=-6)

    # Daylight Saving
    if new_dt.month in range(4, 11) or (new_dt.month == 3 and new_dt.day >= 8):
        new_dt += datetime.timedelta(hours=1)
    return new_dt
