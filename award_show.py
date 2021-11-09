""" This script checks for and awards time-based trophies (e.g. "one year") and
    is to be run once a day at the beginning of each day.
"""
from crabber import app
from datetime import datetime
from extensions import db
import logging
from models import Crab, Trophy, TrophyCase

# Prepare database connection
app.app_context().push()

# Setup logging
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler("award_show.log")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

# Get "constant" variables
today = datetime.utcnow().date()

logger.info("Beginning award show.")
# Iterate through users
for crab in Crab.query_all():
    logger.info(f"Checking trophies for @{crab.username}")
    # Get per-crab variables here
    signup_date = crab.register_time.date()
    year_difference = today.year - signup_date.year
    is_anniversary = today.month == signup_date.month and today.day == signup_date.day

    # Trophy checks go here ###################################################

    # Anniversary trophies
    if is_anniversary:
        if year_difference == 1:
            logger.info(f'Awarding "One Year" to @{crab.username}')
            crab.award(title="One Year")

db.session.commit()
