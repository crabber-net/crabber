from crabber import app
from extensions import db
from models import AccessToken, Crab, DeveloperKey, Like, Molt, Trophy, TrophyCase

app.app_context().push()
