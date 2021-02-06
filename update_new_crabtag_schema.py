from crabber import app
from extensions import db
from models import AccessToken, Crab, DeveloperKey, Like, Molt, Trophy, \
        TrophyCase, following_table, crabtag_table

app.app_context().push()

crabtag_table.create(bind=db.session.bind)

for molt in Molt.query:
    molt.evaluate_contents()
