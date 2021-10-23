import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from crabber import app
from extensions import db
import json
from models import Trophy

app.app_context().push()

with open('trophies.json', 'r') as f:
    trophies = json.load(f)

for trophy in trophies:
    if Trophy.query.filter_by(title=trophy['title']).count() == 0:
        print(f'Adding "{trophy["title"]}" trophy')
        new_trophy = Trophy(**trophy)
        db.session.add(new_trophy)

db.session.commit()
