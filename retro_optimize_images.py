import os
import turtle_images

for file in os.listdir("static/img/user_uploads"):
    filename = os.path.join("static/img/user_uploads", file)
    if os.path.isfile(filename):
        print(f"Optimizing: {filename}")
        turtle_images.prep_and_save(filename, os.path.splitext(filename)[0] + ".jpg")