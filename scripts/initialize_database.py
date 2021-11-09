import os, sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from crabber import app
from extensions import db
from models import Crab, Molt, Trophy
import json

app.app_context().push()

db.drop_all()
db.create_all()

# Create crabber account
crabber = Crab.create_new(
    username="crabber",
    email="crabberwebsite@gmail.com",
    password="fish",
    avatar="https://cdn.crabber.net/img/icon.jpg",
    display_name="Crabber",
    verified=True,
    description="Official account for website news and updates.",
)


# Instantiate trophies
with open("trophies.json", "r") as f:
    trophies = json.load(f)

for trophy in trophies:
    if Trophy.query.filter_by(title=trophy["title"]).count() == 0:
        print(f'Adding "{trophy["title"]}" trophy')
        new_trophy = Trophy(**trophy)
        db.session.add(new_trophy)

db.session.commit()
