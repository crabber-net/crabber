import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from crabber import app
from extensions import db
from models import (
    Card,
)
from sqlalchemy import desc, func, or_
from sqlalchemy.sql import expression

app.app_context().push()

blanks = Card.query.filter_by(ready=True, failed=False).filter(
    Card.title == expression.null()
)

print(f"Found {blanks.count()} blank cards.")
for card in blanks:
    card.ready = False
    card.failed = True

db.session.commit()
print("Removed.")
