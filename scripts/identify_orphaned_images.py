import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from crabber import app
from extensions import db
from models import AccessToken, Crab, DeveloperKey, Like, Molt, Trophy, TrophyCase
import os
import sys

app.app_context().push()


# List all images
user_upload_path = os.path.join('img', 'user_uploads')
image_path = os.path.join('static', user_upload_path)
images = [os.path.join(user_upload_path, image)
          for image in os.listdir(image_path)
          if os.path.isfile(os.path.join(image_path, image))]

# Filter by images unless --all flag is provided
if '--all' not in sys.argv:
    images = filter(lambda file: os.path.splitext(file)[1].lower() in ('.png',
                                                                       '.jpg',
                                                                       '.jpeg'),
                    images)

# Find all Molt images
for molt in Molt.query.filter(Molt.image != None):
    if molt.image in images:
        images.remove(molt.image)

# Find all Crab images
for crab in Crab.query:
    for image in (crab.avatar, crab.banner):
        if image is not None:
            if image.startswith(user_upload_path):
                if image in images:
                    images.remove(image)

for image in images:
    # Convert to absolute paths
    image = os.path.join(image_path, os.path.split(image)[-1])
    print(image)

