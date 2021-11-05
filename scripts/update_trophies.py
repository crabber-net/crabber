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

for trophy_json in trophies:
    trophy = Trophy.query.filter_by(title=trophy_json['title']).first()
    if trophy:
        json_image = trophy_json.get('image')
        json_description = trophy_json.get('description')
        if trophy.image != json_image and json_image:
            print(f'Updating image for "{trophy.title}"')
            trophy.image = trophy_json.get('image')
        if trophy.description != trophy_json.get('description'):
            print(f'Updating description for "{trophy.title}"')
            trophy.description = trophy_json.get('description')
    else:
        # Create new trophy
        print(f'Adding "{trophy_json["title"]}" trophy')
        new_trophy = Trophy(**trophy_json)
        db.session.add(new_trophy)

db.session.commit()
