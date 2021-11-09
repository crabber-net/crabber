""" Marks N notifications unread for user U.
"""
import os, sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from crabber import app
from extensions import db
from models import Crab

app.app_context().push()

username = input("Username: ").strip().lower()
amount = int(input("Notification count: ").strip())

crab = Crab.get_by_username(username)
if crab:
    for notification in crab.notifications[:amount]:
        notification.read = False
else:
    print("No crab found with that username.")

db.session.commit()
