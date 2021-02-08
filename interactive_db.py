from crabber import app
from extensions import db
from models import AccessToken, crabtag_table, Card, Crab, Crabtag, \
        DeveloperKey, following_table, Like, Molt, Trophy, TrophyCase
from sqlalchemy import desc, func

app.app_context().push()
