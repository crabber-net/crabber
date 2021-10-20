import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from crabber import app
from extensions import db
from models import Crab, Molt, Trophy

app.app_context().push()

db.create_all()
db.session.commit()
