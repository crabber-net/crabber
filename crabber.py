import calendar
import datetime
from extensions import db
from flask import Flask, render_template, request, redirect, escape, session, url_for, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
import json
import models
import os
from passlib.hash import sha256_crypt
import re
import requests
from sqlalchemy.sql import func
import sys
import turtle_images
from typing import List, Set
import utils
import uuid
from werkzeug.wrappers import Response


# HELPER FUNCS #########################################################################################################

def localize(dt: datetime.datetime) -> datetime.datetime:
    """
    Localizes datetime to user's timezone
    https://www.youtube.com/watch?v=-5wpm-gesOY

    :param dt: datetime to localize
    :return: Localized datetime
    """
    current_user = get_current_user()
    if current_user:
        new_dt = dt + current_user.timedelta
    else:
        # Defaults to Chicago time
        new_dt = dt + datetime.timedelta(hours=-6)

    # Daylight Saving
    if new_dt.month in range(4, 11) or (new_dt.month == 3 and new_dt.day >= 8):
        new_dt += datetime.timedelta(hours=1)
    return new_dt


def show_error(error_msg: str) -> Response:
    """
    Redirect user to current page with error message alert
    :param error_msg: Message to display to user
    :return: Response to return to user
    """
    return redirect(f"{request.path}?error={error_msg}")


def show_message(misc_msg: str) -> Response:
    """
    Redirect user to current page with misc message alert
    :param misc_msg: Message to display to user
    :return: Response to return to user
    """
    return redirect(f"{request.path}?msg={misc_msg}")


def get_pretty_age(dt: datetime.datetime) -> str:
    """
    Converts datetime to pretty twitter-esque age string.
    :param dt:
    :return: Age string
    """
    now: datetime.datetime = datetime.datetime.utcnow()
    delta = now - dt

    if delta.total_seconds() < 60:  # Less than a minute
        # Return number of seconds
        return f"{round(delta.seconds)}s"
    elif delta.total_seconds() / 60 < 60:  # Less than an hour
        # Return number of minutes
        return f"{round(delta.seconds / 60)}m"
    elif delta.seconds / 60 / 60 < 24 and delta.days == 0:  # Less than a day
        # Return number of hours
        return f"{round(delta.seconds / 60 / 60)}h"
    elif dt.year == now.year:  # Same year as now
        # Return day and month
        return localize(dt).strftime("%b %e")
    else:
        # Return day month, year
        return localize(dt).strftime("%b %e, %Y")


def get_current_user():
    """
    Retrieves the object of the currently logged-in user by ID.
    :return: The logged in user
    """
    return Crab.query.filter_by(id=session.get("current_user"), deleted=False).first()


def validate_username(username: str) -> bool:
    """
    Validates `username` hasn't already been used by another (not deleted) user.
    :param username: Username to validate
    :return: Whether it's been taken
    """
    return not Crab.query.filter_by(deleted=False).filter(Crab.username.like(username)).all()


def validate_email(email: str) -> bool:
    """
    Validates `email` hasn't already been used by another (not deleted) user.
    :param email: Email to validate
    :return: Whether it's been taken
    """
    return not Crab.query.filter_by(email=email, deleted=False).all()


def allowed_file(filename: str) -> bool:
    """
    Verifies filename specified is valid and in `ALLOWED_EXTENSIONS`.
    :param filename: Filename sans-path to check
    :return: Whether it's valid
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def common_molt_actions() -> Response:
    """
    Sorts through potential actions in POST form data and executes them.
    :return: Redirect response to same page. See PRG pattern.
    """
    action = request.form.get('user_action')
    molt_id = request.form.get('molt_id')  # Can very well be none.

    if action == "change_avatar":
        if 'file' in request.files:
            img = request.files['file']
            if img.filename == '':
                return show_error("No image was selected")
            elif img and allowed_file(img.filename):
                filename = str(uuid.uuid4()) + ".jpg"
                location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                turtle_images.prep_and_save(img, location)
                current_user = get_current_user()
                current_user.avatar = "img/user_uploads/" + filename
                db.session.commit()
                return redirect(request.path)
            else:
                return show_error("File must be either a jpg, jpeg, or png")
        return show_error("There was an error uploading your image")

    elif action == "change_banner":
        if 'file' in request.files:
            img = request.files['file']
            if img.filename == '':
                return show_error("No image was selected")
            elif img and allowed_file(img.filename):
                filename = str(uuid.uuid4()) + ".jpg"
                location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                turtle_images.prep_and_save(img, location)
                current_user = get_current_user()
                current_user.banner = "img/user_uploads/" + filename
                db.session.commit()
                return redirect(request.path)
            else:
                return show_error("File must be either a jpg, jpeg, or png")
        return show_error("There was an error uploading your image")

    # Submit new molt
    elif action == "submit_molt":
        if request.form.get('molt_content'):
            img_attachment = None
            # Handle uploaded images
            if request.files.get("molt-media"):
                img = request.files['molt-media']
                if img.filename != '':
                    if img and allowed_file(img.filename):
                        filename = str(uuid.uuid4()) + ".jpg"
                        location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        turtle_images.prep_and_save(img, location)
                        img_attachment = "img/user_uploads/" + filename
            get_current_user().molt(request.form.get('molt_content'), image=img_attachment)
        else:
            return show_error("Molts cannot be devoid of text")

    elif action == "follow":
        target_user = Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().follow(target_user)

    elif action == "unfollow":
        target_user = Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().unfollow(target_user)

    elif action == "submit_reply_molt":
        target_molt = Molt.query.filter_by(id=molt_id).first()
        if request.form.get('molt_content'):
            img_attachment = None
            # Handle uploaded images
            if request.files.get("molt-media"):
                img = request.files['molt-media']
                if img.filename != '':
                    if img and allowed_file(img.filename):
                        filename = str(uuid.uuid4()) + os.path.splitext(img.filename)[1]
                        location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        img.save(location)
                        img_attachment = "img/user_uploads/" + filename
            reply = target_molt.reply(get_current_user(), request.form.get('molt_content'), image=img_attachment)
            return redirect(f'/user/{get_current_user().username}/status/{reply.id}')

    elif action == "submit_molt_edit":
        target_molt = Molt.query.filter_by(id=molt_id).first()
        new_content = request.form.get('molt_content')
        if target_molt.author == get_current_user():
            if target_molt.editable:
                if new_content:
                    if new_content != target_molt.content:
                        target_molt.edit(new_content)
                        return redirect(f'/user/{get_current_user().username}/status/{target_molt.id}')
                    else:
                        return show_error("No changes were made")
                else:
                    return show_error("Molt text cannot be blank")
            else:
                return show_error("Molt is no longer editable (must be less than 5 minutes old)")
        else:
            return show_error("You can't edit Molts that aren't yours")

    elif action == "remolt_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()
        target_molt.remolt(get_current_user())

    elif action == "like_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()
        if get_current_user().has_liked(target_molt):
            target_molt.unlike(get_current_user())
        else:
            target_molt.like(get_current_user())

    elif action == "pin_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()
        if target_molt.author is get_current_user():
            target_molt.author.pin(target_molt)

    elif action == "unpin_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()
        if target_molt.author is get_current_user():
            target_molt.author.unpin()

    elif action == "delete_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()

        if target_molt.author.id == get_current_user().id:
            target_molt.delete()

    elif action == "update_description":
        target_user = Crab.query.filter_by(id=request.form.get('user_id')).first()
        if target_user == get_current_user():
            disp_name = request.form.get('display_name').strip()
            desc = request.form.get('description').strip()
            location = request.form.get('location').strip()

            # Bio JSON assembly
            new_bio = dict() 
            for key, value in request.form.items():
                if "bio." in key:
                    if value.strip():
                        new_bio[key.split(".")[1].strip()] = value.strip()
            
            current_user = get_current_user()
            current_user.display_name = disp_name
            current_user.description = desc
            current_user.location = location
            current_user.raw_bio = json.dumps(new_bio)
            db.session.commit()
            if request.form.get('page') == "settings":
                return show_message("Changes saved.")

    elif action == "update_account":
        target_user = get_current_user()
        new_email = request.form.get('email').strip()
        new_username = request.form.get('username').strip()
        if validate_email(new_email) or target_user.email == new_email:
            if validate_username(new_username) or target_user.username == new_username:
                if len(new_username) in range(4, 32):
                    if username_pattern.fullmatch(new_username):
                        target_user.email = new_email
                        target_user.username = new_username
                        db.session.commit()
                        return show_message("Changes saved.")
                    else:
                        return show_error("Username must only contain letters, numbers, and underscores")
                else:
                    return show_error("Username must be at least 4 characters and less than 32")
            else:
                return show_error("That username is taken")
        else:
            return show_error("An account with that email address already exists")

    elif action == "update_general_settings":
        target_user = get_current_user()
        new_timezone = request.form.get('timezone')
        new_lastfm = request.form.get('lastfm').strip()
        if timezone_pattern.fullmatch(new_timezone):
            target_user.timezone = new_timezone
            target_user.lastfm = new_lastfm
            db.session.commit()
            return show_message("Changes saved.")
        else:
            return show_error("That timezone is invalid, you naughty dog")

    # PRG pattern
    return redirect(request.url)


def load_usernames_from_file(filename: str) -> List[str]:
    """
    Load list of usernames from file.
    :param filename: Filename without path or extension (assumes app root and cfg)
    :return: List of usernames as they appear in file
    """
    with open(f"{os.path.join(BASE_PATH, filename)}.cfg", "r") as f:
        return [username.strip() for username in f.read().strip().splitlines()]


# GENERAL CONFIG #######################################################################################################
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MOLT_CHAR_LIMIT: int = 240
MOLTS_PER_PAGE: int = 20
NOTIFS_PER_PAGE: int = 20
MINUTES_EDITABLE: int = 5
ADMINS: List[str] = load_usernames_from_file("admins")  # Users allowed to access the Tortimer page
UPLOAD_FOLDER: str = os.path.join(BASE_PATH, 'static/img/user_uploads')
ALLOWED_EXTENSIONS: Set[str] = {'png', 'jpg', 'jpeg'}
RECOMMENDED_USERS: List[str] = load_usernames_from_file("recommended_users")  # Users suggested on post-signup page
BASE_URL = "http://localhost" if os.name == "nt" else "https://crabber.net"
SERVER_START = round(datetime.datetime.utcnow().timestamp())  # Timestamp of when the server went up

# Regex patterns #######################################################################################################
mention_pattern = re.compile(
    r'(?:^|\s)(?<!\\)@([\w]{1,32})(?!\w)')
tag_pattern = re.compile(
    r'(?:^|\s)(?<!\\)%([\w]{1,16})(?!\w)')
username_pattern = re.compile(
    r'^\w+$')
spotify_pattern = re.compile(
    r'(https?://open\.spotify\.com/(?:embed/)?(\w+)/(\w+))(?:\S+)?')
youtube_pattern = re.compile(
    r'(?:https?://)?(?:www.)?(?:youtube\.com/watch\?(?:[^&]+&)*v=|youtu\.be/)(\S{11})')
giphy_pattern = re.compile(
    r'https://(?:media\.)?giphy\.com/\S+[-/](\w{13,21})(?:\S*)')
ext_img_pattern = re.compile(
    r'(https://\S+\.(gif|jpe?g|png))(?:\s|$)')
ext_link_pattern = re.compile(
    r'(?<!href=[\'"])(https?://\S+)')
ext_md_link_pattern = re.compile(
    r'\[([^\]\(\)]+)\]\((http[^\]\(\)]+)\)')
timezone_pattern = re.compile(
    r'^-?(1[0-2]|0[0-9]).\d{2}$')

# APP CONFIG ###########################################################################################################
app = Flask(__name__, template_folder="./templates")
app.secret_key = 'crabs are better than birds because they can cut their wings right off'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///CRABBER_DATABASE.db'  # Database location
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Max length of user-uploaded files. First number is megabytes.
db.init_app(app)

# WEBSITE ROUTING ######################################################################################################

@app.route("/", methods=("GET", "POST"))
def index():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)

        following_ids = [crab.id for crab in get_current_user().following] + [get_current_user().id]
        molts = Molt.query.filter(Molt.author_id.in_(following_ids)) \
            .filter_by(deleted=False, is_reply=False).filter(Molt.author.has(deleted=False)) \
            .order_by(Molt.timestamp.desc()) \
            .paginate(page_n, MOLTS_PER_PAGE, False)
        return render_template('timeline-content.html' if request.args.get("ajax_content") else 'timeline.html', current_page="home", page_n=page_n,
                               molts=molts, current_user=get_current_user())
    else:
        return render_template('welcome.html', current_user=get_current_user(), fullwidth=True, hide_sidebar=True)


@app.route("/wild/", methods=("GET", "POST"))
def wild_west():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)
        molts = Molt.query.filter_by(deleted=False, is_reply=False, is_remolt=False) \
            .filter(Molt.author.has(deleted=False)).order_by(Molt.timestamp.desc()) \
            .paginate(page_n, MOLTS_PER_PAGE, False)
        return render_template('wild-west-content.html' if request.args.get("ajax_content") else 'wild-west.html', current_page="wild-west", page_n=page_n,
                               molts=molts, current_user=get_current_user())
    else:
        return redirect("/login")


@app.route("/notifications/", methods=("GET", "POST"))
def notifications():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)
        notifications = get_current_user().get_notifications(paginated=True, page=page_n)
        return render_template('notifications.html', current_page="notifications",
                               notifications=notifications, current_user=get_current_user())
    else:
        return redirect("/login")


@app.route("/login/", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email, password = request.form.get("email").strip().lower(), request.form.get("password")
        attempted_user = Crab.query.filter_by(email=email, deleted=False).first()
        if attempted_user is not None:
            if attempted_user.verify_password(password):
                # Login successful
                session["current_user"] = attempted_user.id
                return redirect("/")
            else:
                return show_error("Incorrect password")
        else:
            return show_error("No account with that email exists")
    elif session.get("current_user"):
        return redirect("/")
    else:
        login_failed = request.args.get("failed") is not None
        return render_template("login.html", current_page="login", hide_sidebar=True, login_failed=login_failed)


@app.route("/signup/", methods=("GET", "POST"))
def signup():
    if request.method == "POST":
        # Validate data
        form = request.form
        email = form.get("email").strip().lower()
        username = form.get("username").strip()
        display_name = form.get("display-name").strip()
        password = form.get("password").strip()
        confirm_password = form.get("confirm-password").strip()

        if validate_email(email):
            if validate_username(username):
                if len(username) in range(4, 32):
                    if username_pattern.fullmatch(username):
                        if password == confirm_password:
                            # Create user account
                            Crab.create_new(username=username,
                                            email=email,
                                            password=password,
                                            display_name=display_name)

                            # "Log in"
                            session["current_user"] = Crab.query.filter_by(username=username, deleted=False).first().id
                            # Redirect to let the user know it succeeded
                            return redirect("/signupsuccess")
                        else:
                            return redirect("/signup?failed&error_msg=Passwords do not match")
                    else:
                        return redirect("/signup?failed&error_msg=Username must only contain \
                                        letters, numbers, and underscores")
                else:
                    return redirect("/signup?failed&error_msg=Username must be at least 4 characters and less than 32")
            else:
                return redirect("/signup?failed&error_msg=That username is taken")
        else:
            return redirect("/signup?failed&error_msg=An account with that email address already exists")

    elif session.get("current_user"):
        return redirect("/")
    else:
        signup_failed = request.args.get("failed") is not None
        error_msg = request.args.get("error_msg")
        return render_template("signup.html", current_page="signup", hide_sidebar=True,
                               signup_failed=signup_failed, error_msg=error_msg)


@app.route("/logout/")
def logout():
    session["current_user"] = None
    return redirect("/login")


@app.route("/signupsuccess/")
def signupsuccess():
    recommended_users = Crab.query.filter(Crab.username.in_(RECOMMENDED_USERS)).all()
    return render_template("signup_success.html", current_user=get_current_user(),
                           recommended_users=recommended_users)


@app.route("/settings/", methods=("GET", "POST"))
def settings():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        return render_template("settings.html", current_page="settings",
                               current_user=get_current_user())


@app.route("/u/<username>/", methods=("GET", "POST"))
@app.route("/user/<username>/", methods=("GET", "POST"))
def user(username):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    else:
        current_tab = request.args.get("tab", default="molts")
        this_user = Crab.query.filter_by(deleted=False).filter(Crab.username.ilike(username)).first()
        if this_user is not None:
            m_page_n = request.args.get('mp', 1, type=int)
            r_page_n = request.args.get('rp', 1, type=int)
            l_page_n = request.args.get('lp', 1, type=int)
            molts = Molt.query.filter_by(author=this_user, deleted=False, is_reply=False).order_by(
                Molt.timestamp.desc()).paginate(m_page_n, MOLTS_PER_PAGE, False)
            replies = Molt.query.filter_by(author=this_user, deleted=False, is_reply=True) \
                .filter(Molt.original_molt.has(deleted=False)).order_by(
                Molt.timestamp.desc()).paginate(r_page_n, MOLTS_PER_PAGE, False)
            likes = this_user.get_true_likes(paginated=True, page=l_page_n)
            return render_template('profile.html',
                                   current_page=("own-profile" if this_user == get_current_user() else ""),
                                   molts=molts, current_user=get_current_user(), this_user=this_user, likes=likes,
                                   current_tab=current_tab, replies=replies)
        else:
            return render_template('not-found.html', current_user=get_current_user(), noun="user")


@app.route("/user/<username>/follow<tab>/", methods=("GET", "POST"))
def user_following(username, tab):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        this_user = Crab.query.filter_by(username=username, deleted=False).first()
        if this_user:
            followx = this_user.following if tab == "ing" else this_user.followers
            return render_template('followx.html',
                                   current_page=("own-profile" if this_user == get_current_user() else ""),
                                   followx=followx,
                                   current_user=get_current_user(), this_user=this_user, tab="follow" + tab)
        else:
            return render_template('not-found.html', current_user=get_current_user(), noun="user")
    else:
        return redirect("/login")


@app.route("/user/<username>/status/<molt_id>/", methods=("GET", "POST"))
def molt_page(username, molt_id):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    else:
        primary_molt = Molt.query.filter_by(id=molt_id).first()
        ajax_content = request.args.get('ajax_content')
        if primary_molt:
            replies = Molt.query.filter_by(deleted=False, is_reply=True, original_molt_id=molt_id) \
                .order_by(Molt.timestamp.desc())
            return render_template('molt-page-replies.html' if ajax_content else 'molt-page.html', current_page="molt-page", molt=primary_molt,
                                   replies=replies, current_user=get_current_user())
        else:
            return render_template('not-found.html', current_user=get_current_user(), noun="molt")


@app.route("/crabtag/<crabtag>/", methods=("GET", "POST"))
def crabtags(crabtag):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        molts = Molt.query.filter(Molt.raw_tags.contains((crabtag + "\n"))).filter_by(deleted=False, is_reply=False) \
            .filter(Molt.author.has(deleted=False)).order_by(Molt.timestamp.desc())
        return render_template('crabtag.html', current_page="crabtag",
                               molts=molts, current_user=get_current_user(), crabtag=crabtag)
    else:
        return redirect("/login")


@app.route("/search/", methods=("GET", "POST"))
def search():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        query = request.args.get('q')
        page_n = request.args.get('p', 1, type=int)
        ajax_content = request.args.get('ajax_content')

        if query:
            crab_results = Crab.query.filter_by(deleted=False) \
                .filter(db.or_(Crab.display_name.ilike(f'%{query}%'),
                               Crab.username.ilike(f'%{query}%')))
            molt_results = Molt.query.filter_by(deleted=False, is_reply=False) \
                .filter(Molt.content.ilike(f'%{query}%')) \
                .filter(Molt.author.has(deleted=False)).order_by(Molt.timestamp.desc()) \
                .paginate(page_n, MOLTS_PER_PAGE, False)

        else:
            molt_results = tuple()
            crab_results = tuple()
        return render_template('search-results.html' if ajax_content else 'search.html', current_page="search", 
                               query=query, page_n=page_n, molt_results=molt_results, 
                               crab_results=crab_results, current_user=get_current_user())
    else:
        return redirect("/login")


@app.route("/stats/", methods=("GET",))
def stats():
    # Query follow counts for users
    sub = db.session.query(following_table.c.following_id, func.count(following_table.c.following_id).label('count')) \
        .group_by(following_table.c.following_id).subquery()
    most_followed = db.session.query(Crab, sub.c.count).outerjoin(sub, Crab.id == sub.c.following_id) \
        .order_by(db.desc('count')).filter(Crab.deleted == False).first()
    newest_user = Crab.query.filter_by(deleted=False).order_by(Crab.register_time.desc()).first()

    best_molt = db.session.query(Like.molt_id, func.count(Like.id)).filter(Like.molt.has(deleted=False)) \
        .filter(Like.crab.has(deleted=False)) \
        .filter(Like.molt.has(Molt.author.has(deleted=False))) \
        .order_by(func.count(Like.id).desc()).group_by(Like.molt_id).first()
    best_molt = Molt.query.filter_by(id=best_molt[0]).first(), best_molt[1]
    talked_molt = db.session.query(Molt.original_molt_id).filter_by(is_reply=True, deleted=False) \
        .filter(Molt.author.has(deleted=False)).filter(Molt.original_molt.has(deleted=False)) \
        .filter(Molt.original_molt.has(Molt.author.has(deleted=False))) \
        .group_by(Molt.original_molt_id) \
        .order_by(func.count(Molt.id).desc()).first()
    talked_molt = (Molt.query.filter_by(id=talked_molt[0]).first(),)
    stats_dict = dict(users=Crab.query.filter_by(deleted=False).count(), 
                      mini_stats=[
                          dict(number=Molt.query.count(),
                               label="molts sent"),
                          dict(number=Molt.query.filter_by(deleted=True).count(),
                               label="molts deleted",
                               sublabel="what are they hiding?"),
                          dict(number=Like.query.count(),
                               label="likes given"),
                          dict(number=TrophyCase.query.count(),
                               label="trophies awarded")
                      ],
                      crab_king=most_followed,
                      baby_crab=newest_user,
                      best_molt=best_molt,
                      talked_molt=talked_molt)
    return render_template('stats.html', current_user=get_current_user(), stats=stats_dict,
                           current_page='stats')

@app.route("/debug/")
def debug():
    return "You're not supposed to be here. <a href='https://xkcd.com/838/'>This incident will be reported.</a>"

# This wise tortoise, the admin control panel
@app.route("/tortimer/", methods=("GET", "POST"))
def tortimer():
    if get_current_user().username in ADMINS:
        if request.method == "POST":
            action = request.form.get("user_action")
            if request.form.get("target") == "crab":
                target: Crab = Crab.query.filter_by(id=request.form.get("crab_id")).first()
            else:
                target: Molt = Molt.query.filter_by(id=request.form.get("molt_id")).first()
            if action == "verify":
                target.verified = True
                db.session.commit()
                return show_message(f"Verified @{target.username}")
            elif action == "delete":
                target.delete()
                return show_message(f"Deleted @{target.username}")
            elif action == "restore":
                target.restore()
                return show_message(f"Restored @{target.username}")
            elif action == "award":
                if request.form.get("award_title"):
                    try:
                        target.award(title=request.form.get("award_title"))
                        return show_message(f"Awarded @{target.username}: {request.form.get('award_title')}")
                    except NotFoundInDatabase:
                        return show_error(f"Unable to find trophy with title: {request.form.get('award_title')}")
                else:
                    return show_error(f"No award title found.")

            # PRG pattern
            return redirect(request.url)

        else:
            crab_page_n = request.args.get('pc', 1, type=int)
            molt_page_n = request.args.get('pm', 1, type=int)
            crabs = Crab.query \
                .order_by(Crab.register_time.desc()) \
                .paginate(crab_page_n, MOLTS_PER_PAGE, False)
            molts = Molt.query.order_by(Molt.timestamp.desc()) \
                .paginate(molt_page_n, MOLTS_PER_PAGE, False)
            return render_template('tortimer.html', crabs=crabs, molts=molts, current_user=get_current_user(),
                                   crab_page_n=crab_page_n, molt_page_n=molt_page_n)
    else:
        return error_404(BaseException)


@app.route("/ajax_request/<request_type>/")
def ajax_request(request_type):
    if request_type == "unread_notif":
        if request.args.get("crab_id"):
            crab = Crab.query.filter_by(id=request.args.get("crab_id")).first()
            if crab:
                return str(crab.unread_notifications)
        return "Crab not found. Did you specify 'crab_id'?"
    if request_type == "molts_since":
        if request.args.get("timestamp"):
            if request.args.get("crab_id"):
                crab = Crab.query.filter_by(id=request.args.get("crab_id")).first()
                following_ids = [crab.id for crab in crab.following]
                new_molts = Molt.query.filter(Molt.author_id.in_(following_ids)) \
                    .filter_by(deleted=False, is_reply=False).filter(Molt.author.has(deleted=False)) \
                    .filter(Molt.timestamp > datetime.datetime.utcfromtimestamp(int(request.args.get("timestamp"))))
                return str(new_molts.count())

            else:
                return "Crab not found. Did you specify 'crab_id'?"

        return "Did not specify 'timestamp'"


@app.route("/api/v0/<action>/", methods=('GET', 'POST'))
def api_v0(action):
    if request.method == "POST":
        # Submit molt
        if action == "molt":
            username = request.form.get("username")
            password = request.form.get("password")
            content = request.form.get("content")

            target_user: Crab = Crab.query.filter_by(username=username).first()
            if target_user:
                if target_user.verify_password(password):
                    if content:
                        new_molt = target_user.molt(content)
                        return jsonify(new_molt.dict())
                    else:
                        return "No content provided", 400
                else:
                    return "Incorrect password", 400
            else:
                return "No such user found", 400
        # Reply to molt
        elif action == "reply":
            username = request.form.get("username")
            password = request.form.get("password")
            content = request.form.get("content")
            original_id = request.form.get("original_id")
            original_molt: Molt = Molt.query.filter_by(id=original_id, deleted=False) \
                .filter(Molt.author.has(deleted=False)).first()

            target_user: Crab = Crab.query.filter_by(username=username).first()
            if target_user:
                if target_user.verify_password(password):
                    if content:
                        if original_molt:
                            new_molt = original_molt.reply(target_user, content)
                            return jsonify(new_molt.dict())
                        else:
                            return "No molt found with that ID", 400
                    else:
                        return "No content provided", 400
                else:
                    return "Incorrect password", 400
            else:
                return "No such user found", 400

        return jsonify("Blah!")
    elif request.method == "GET":
        # Test API
        if action == "test":
            return jsonify("Test success!")
        # Get molt content
        elif action == "molt":
            molt = Molt.query.filter_by(id=request.args.get("id")).first()
            if molt:
                if molt.deleted:
                    return "Molt has been deleted", 400
                else:
                    return jsonify(molt.dict())
            else:
                return "Molt not found", 400
        # Get molts mentioning user
        elif action == "mentions":
            username = request.args.get("username")
            since_ts = request.args.get("since", 0)
            if username:
                molts = Molt.query.filter(Molt.raw_mentions.contains((username + "\n"))) \
                    .filter(Molt.timestamp > datetime.datetime.fromtimestamp(int(since_ts))).all()
                return jsonify([molt.dict() for molt in molts])
            else:
                return "Username not provided", 400
    return "What were you trying to do?", 400


# GLOBAL FLASK VARIABLES GO HERE
@app.context_processor
def inject_global_vars():
    error = request.args.get("error")
    msg = request.args.get("msg")
    location = request.path
    now = datetime.datetime.utcnow()
    return dict(MOLT_CHAR_LIMIT=MOLT_CHAR_LIMIT,
                TIMESTAMP=round(calendar.timegm(now.utctimetuple())),
                IS_WINDOWS=os.name == "nt",
                localize=localize,
                server_start=SERVER_START,
                current_year=now.utcnow().year,
                error=error, msg=msg, location=location)


@app.template_filter()
def commafy(value):
    return format(int(value), ',d')


@app.errorhandler(404)
def error_404(_error_msg):
    return render_template("404.html", current_page="404", current_user=get_current_user())


@app.errorhandler(413)
def file_to_big(_e):
    return show_error("Image must be smaller than 5 megabytes.")


@app.before_request
def before_request():
    # Make sure cookies are still valid
    if session.get("current_user"):
        if not Crab.query.filter_by(id=session.get("current_user"), deleted=False).all():
            # Force logout
            session["current_user"] = None
            return redirect("/login")
    # Persist session after browser is closed
    session.permanent = True


if __name__ == '__main__':
    # Start server locally
    app.run("0.0.0.0", 80, debug=True)
