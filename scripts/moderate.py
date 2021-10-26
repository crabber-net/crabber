import os
import sys
import inspect
currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe()))
)
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from crabber import app
from extensions import db
from models import AccessToken, Bookmark, crabtag_table, Card, Crab, Crabtag, \
        DeveloperKey, following_table, Like, Molt, Trophy, TrophyCase, \
        Notification, blocking_table
from sqlalchemy import desc, func, or_

app.app_context().push()


def get_action(actions):
    while True:
        choice = input('? ').lower().strip()
        if choice in actions:
            return choice
        else:
            print('Invalid choice.')


def show_molt(molt):
    print(f'Reports: {molt.reports}')
    print(f'from @{molt.author.username}')
    print(f'aka "{molt.author.display_name}"\n')
    print(f'Content:\n"""\n{molt.content}\n"""\n\n')


reports = Molt.query \
        .filter_by(approved=False, deleted=False,
                   is_remolt=False) \
        .order_by(Molt.reports.desc(), Molt.timestamp.desc())


ACTIONS = ('a', 'c', 'b', 'd', 'w', 's', 'q')

for molt in reports:
    show_molt(molt)

    while True:
        action = get_action(ACTIONS)

        if action == 'a':
            molt.approve()
            print(f'Approved #{molt.id}')
            break
        elif action == 'd':
            molt.delete()
            print(f'Deleted #{molt.id}')
            break
        elif action == 'c':
            if molt.original_molt:
                show_molt(molt.original_molt)
        elif action == 'b':
            molt.author.ban()
            print(f'Banned #{molt.author_id}')
            break
        elif action == 'w':
            print(f'https://crabber.net/user/{molt.author.username}/status/{molt.id}/')
        elif action == 's':
            print(f'Skipping.')
            break
        elif action == 'q':
            sys.exit(0)
        else:
            raise ValueError('Invalid action')

    db.session.commit()
    print('\n')
