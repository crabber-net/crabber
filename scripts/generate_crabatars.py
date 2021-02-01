import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from crabber import app
from extensions import db
from models import Crab
import utils

app.app_context().push()

boring_crabs = Crab.query.filter_by(avatar='img/avatar.jpg').all()
if boring_crabs:
    for crab in boring_crabs:
        crab.avatar = utils.make_crabatar(crab.username)
    db.session.commit()
    print(f'Successfully updated {len(boring_crabs)} Crabs\' avatars.')
else:
    print('No changes necessary.')
