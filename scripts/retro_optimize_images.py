import os
import turtle_images

user_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/img/user_uploads')
for file in os.listdir(user_uploads):
    filename = os.path.join(user_uploads, file)
    if os.path.isfile(filename):
        print(f'Optimizing: {filename}')
        turtle_images.prep_and_save(filename, os.path.splitext(filename)[0] + '.jpg')
