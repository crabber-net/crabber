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
    db.or_(
        Card.title == expression.null(),
        Card.title.like("404 %"),
        Card.title.like("403 %"),
        Card.title.like("500 %"),
    )
)

print(f"Found {blanks.count()} blank cards.")
blanks.update({"ready": False, "failed": True}, synchronize_session=False)
db.session.commit()
print("Removed.")
