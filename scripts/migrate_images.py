import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from interactive_db import *
import re

user_uploads = re.compile(r'img\/(user_uploads\/[\w-]+\.\w{3,4})')


def migrate_image_url(old_url):
    match = user_uploads.match(old_url)
    if match:
        new_url = f'https://cdn.crabber.net/{match.group(1)}'
        print(f'{old_url} >>> {new_url}')
        return new_url
    print('skipping')
    return old_url


num_crabs = Crab.query_all().count()
digits = len(str(num_crabs))
current_crab = 0
for crab in Crab.query_all():
    current_crab += 1
    print(f'{current_crab:{digits}d}/{num_crabs}')
    crab.avatar = migrate_image_url(crab.avatar)
    crab.banner = migrate_image_url(crab.banner)
    print()

    if current_crab % 1000 == 0:
        db.session.commit()

db.session.commit()

num_molts = Molt.query_all().count()
digits = len(str(num_molts))
current_molt = 0
for molt in Molt.query_all():
    current_molt += 1
    print(f'{current_molt:{digits}d}/{num_molts}')
    if molt.image:
        molt.image = migrate_image_url(molt.image)
    print()

    if current_molt % 1000 == 0:
        db.session.commit()

db.session.commit()
