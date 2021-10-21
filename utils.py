from config import *
from crabatar import Crabatar
import crabber
import datetime
import extensions
from flask import redirect, request
import geoip2.database
from geoip2.errors import AddressNotFoundError
from sqlalchemy import func
import json
import models
import patterns
import random
import turtle_images
import uuid
from werkzeug.wrappers import Response

db = extensions.db
geo_reader = geoip2.database.Reader(os.path.join(BASE_PATH, 'GeoLite2-City.mmdb'))


def show_error(error_msg: str, redirect_url=None, preserve_arguments=False) \
        -> Response:
    """
    Redirect user to current page with error message alert
    :param error_msg: Message to display to user
    :param redirect_url: Location to redirect user to. Will default to current
        location.
    :param preserve_arguments: Whether to preserve prior url args.
    :return: Response to return to user
    """
    target_url = redirect_url or request.path
    args = ''
    if preserve_arguments:
        args = '&'.join([f'{key}={value}'
                         for key, value in request.args.items()
                         if key != 'error'])
    return redirect(f'{target_url}?error={error_msg}&{args}')


def show_message(misc_msg: str, redirect_url=None, preserve_arguments=False) \
        -> Response:
    """
    Redirect user to current page with misc message alert
    :param misc_msg: Message to display to user
    :param redirect_url: Location to redirect user to. Will default to current
        location.
    :param preserve_arguments: Whether to preserve prior url args.
    :return: Response to return to user
    """
    target_url = redirect_url or request.path
    args = ''
    if preserve_arguments:
        args = '&'.join([f'{key}={value}'
                         for key, value in request.args.items()
                         if key != 'msg'])
    return redirect(f'{target_url}?msg={misc_msg}&{args}')


def get_current_user():
    """
    Retrieves the object of the currently logged-in user by ID.
    :return: The logged in user
    """
    crab = crabber.session.get('current_user_object')
    if not crab:
        crab = models.Crab.get_by_ID(crabber.session.get('current_use'))
        crabber.session['current_user_object'] = crab
    return crab


def validate_username(username: str) -> bool:
    """
    Validates `username` hasn't already been used by another (not deleted) user.
    :param username: Username to validate
    :return: Whether it's been taken
    """
    return not models.Crab.query.filter_by(deleted=False) \
            .filter(func.lower(models.Crab.username) == func.lower(username)) \
            .count()


def validate_email(email: str) -> bool:
    """
    Validates `email` hasn't already been used by another (not deleted) user.
    :param email: Email to validate
    :return: Whether it's been taken
    """
    return not models.Crab.query.filter_by(email=email, deleted=False).all()


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
    molt_id = request.form.get('molt_id')

    if action == "change_avatar":
        # User has uploaded file
        if 'file' in request.files:
            img = request.files['file']
            # Filename is blank, meaning no actual file was provided.
            if img.filename == '':
                return show_error("No image was selected")
            # File exists and filename passes pattern verification
            elif img and allowed_file(img.filename):
                filename = str(uuid.uuid4()) + ".jpg"
                location = os.path.join(crabber.app.config['UPLOAD_FOLDER'], filename)
                turtle_images.prep_and_save(img, location)
                current_user = get_current_user()
                current_user.avatar = "img/user_uploads/" + filename
                db.session.commit()
                return redirect(request.path)
            else:
                return show_error("File must be either a jpg, jpeg, or png")
        return show_error("There was an error uploading your image")

    # User is attempting to change their profile banner
    elif action == "change_banner":
        if 'file' in request.files:
            img = request.files['file']
            # Filename is blank, meaning no actual file was provided.
            if img.filename == '':
                return show_error("No image was selected")
            # File exists and filename passes pattern verification
            elif img and allowed_file(img.filename):
                filename = str(uuid.uuid4()) + ".jpg"
                location = os.path.join(crabber.app.config['UPLOAD_FOLDER'], filename)
                turtle_images.prep_and_save(img, location)
                current_user = get_current_user()
                current_user.banner = "img/user_uploads/" + filename
                db.session.commit()
                return redirect(request.path)
            else:
                return show_error("File must be either a jpg, jpeg, or png")
        return show_error("There was an error uploading your image")

    # Submit new molt
    elif action in ('submit_molt', 'submit_quote_molt', 'submit_reply_molt'):
        if request.form.get('molt_content') or request.files.get('molt-media'):
            img_attachment = None
            # Handle uploaded images
            if request.files.get("molt-media"):
                img = request.files['molt-media']
                if img.filename != '':
                    if img and allowed_file(img.filename):
                        img_attachment = upload_image(img)
                        if img_attachment is None:
                            return show_error('The image you\'re attempting ' \
                                              'to upload is either corrupted ' \
                                              'or not a valid image file.')

            if action == 'submit_molt':
                new_molt = get_current_user().molt(
                    request.form.get('molt_content'),
                    image=img_attachment,
                    platform=request.user_agent.platform,
                    browser=request.user_agent.browser,
                    address=request.remote_addr
                )
                return redirect(f'/user/{get_current_user().username}/status/{new_molt.id}')
            elif action == 'submit_quote_molt':
                target_molt = models.Molt.query \
                        .filter_by(id=molt_id, deleted=False) \
                        .filter(models.Molt.author.has(deleted=False,
                                                       banned=False)) \
                        .first()
                if target_molt:
                    quote = target_molt.quote(
                        get_current_user(),
                        request.form.get('molt_content'),
                        image=img_attachment,
                        platform=request.user_agent.platform,
                        browser=request.user_agent.browser,
                        address=request.remote_addr
                    )
                    return redirect(f'/user/{get_current_user().username}/status/{quote.id}')
                else:
                    return show_error('The Molt you\'re attempting to quote '
                                      'no longer exists.')
            elif action == 'submit_reply_molt':
                target_molt = models.Molt.query \
                        .filter_by(id=molt_id, deleted=False) \
                        .filter(models.Molt.author.has(deleted=False,
                                                       banned=False)) \
                        .first()
                if target_molt:
                    reply = target_molt.reply(
                        get_current_user(),
                        request.form.get('molt_content'),
                        image=img_attachment,
                        platform=request.user_agent.platform,
                        browser=request.user_agent.browser,
                        address=request.remote_addr
                    )
                    return redirect(f'/user/{get_current_user().username}/status/{reply.id}')
                else:
                    return show_error('The Molt you\'re attempting to reply to '
                                      'no longer exists.')
        else:
            return show_error('Molts require either text or an image.')

    elif action == "block":
        target_user = models.Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().block(target_user)

    elif action == "unblock":
        target_user = models.Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().unblock(target_user)

    elif action == "follow":
        target_user = models.Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().follow(target_user)

    elif action == "unfollow":
        target_user = models.Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().unfollow(target_user)

    elif action == "submit_molt_edit":
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        new_content = request.form.get('molt_content')
        if target_molt.author == get_current_user():
            if target_molt.editable:
                if new_content:
                    if new_content != target_molt.content:
                        target_molt.edit(content=new_content)
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
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        target_molt.remolt(get_current_user(),
                           platform=request.user_agent.platform,
                           browser=request.user_agent.browser,
                           address=request.remote_addr)

    elif action == "report_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        target_molt.report()

    elif action == "bookmark_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        if not get_current_user().has_bookmarked(target_molt):
            get_current_user().bookmark(target_molt)

    elif action == "unbookmark_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        if get_current_user().has_bookmarked(target_molt):
            get_current_user().unbookmark(target_molt)

    elif action == "like_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        if get_current_user().has_liked(target_molt):
            target_molt.unlike(get_current_user())
        else:
            target_molt.like(get_current_user())

    elif action == "pin_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        if target_molt.author is get_current_user():
            target_molt.author.pin(target_molt)

    elif action == "unpin_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()
        if target_molt.author is get_current_user():
            target_molt.author.unpin()

    elif action == "delete_molt" and molt_id is not None:
        target_molt = models.Molt.query.filter_by(id=molt_id).first()

        if target_molt.author.id == get_current_user().id:
            target_molt.delete()

    elif action == "update_description":
        target_user = models.Crab.query.filter_by(id=request.form.get('user_id')).first()
        if target_user == get_current_user():
            disp_name = request.form.get('display_name').strip()
            desc = request.form.get('description').strip()
            location = request.form.get('location')
            website = request.form.get('website')
            if location:
                location = location.strip()
            if website:
                website = website.strip()

            # Bio JSON assembly
            new_bio = target_user.bio
            for key, value in request.form.items():
                if "bio." in key:
                    if value.strip():
                        new_bio[key.split(".")[1].strip()] = value.strip()

            current_user = get_current_user()
            current_user.display_name = disp_name
            current_user.description = desc
            if location:
                current_user.location = location
            if website:
                if not website.startswith('http'):
                    website = 'http://' + website
                current_user.website = website
            current_user.raw_bio = json.dumps(new_bio)
            db.session.commit()
            if request.form.get('page') == "settings":
                return show_message("Changes saved.")

    elif action == "update_account":
        target_user = get_current_user()
        new_email = request.form.get('email').strip()
        new_username = request.form.get('username').strip()
        if validate_email(new_email) or target_user.email == new_email:
            if validate_username(new_username) \
            or target_user.username == new_username:
                if len(new_username) in range(4, 32):
                    if patterns.username.fullmatch(new_username):
                        if not patterns.only_underscores.fullmatch(new_username):
                            target_user.email = new_email
                            target_user.username = new_username
                            db.session.commit()
                            return show_message('Changes saved.')
                        else:
                            return show_error('Only underscores? Really? Think '
                                              'of something better.')
                    else:
                        return show_error('Username must only contain letters, '
                                          'numbers, and underscores')
                else:
                    return show_error('Username must be at least 4 characters '
                                      'and less than 32')
            else:
                return show_error('That username is taken')
        else:
            return show_error(
                'An account with that email address already exists'
            )

    elif action == "change_password":
        target_user = get_current_user()
        old_password = request.form.get('old-password')
        new_password = request.form.get('new-password')
        confirm_password = request.form.get('confirm-password')

        if target_user.verify_password(old_password):
            if new_password == confirm_password:
                if new_password:
                    target_user.change_password(new_password)
                    return show_message('Your password has been changed.')
                else:
                    return show_error('Password cannot be blank.')
            else:
                return show_error('New passwords don\'t match.')
        else:
            return show_error('Incorrect current password.')

    elif action == "update_general_settings":
        target_user = get_current_user()
        new_timezone = request.form.get('timezone')
        new_lastfm = request.form.get('lastfm').strip()
        if patterns.timezone.fullmatch(new_timezone):
            target_user.timezone = new_timezone
            target_user.lastfm = new_lastfm
            db.session.commit()
            return show_message("Changes saved.")
        else:
            return show_error("That timezone is invalid, you naughty dog")

    # PRG pattern
    return redirect(request.url)

def get_current_user():
    """
    Retrieves the object of the currently logged-in user by ID.
    :return: The logged in user
    """
    return models.Crab.query.filter_by(id=crabber.session.get("current_user"), deleted=False).first()


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


def allowed_file(filename: str) -> bool:
    """
    Verifies filename specified is valid and in `ALLOWED_EXTENSIONS`.
    :param filename: Filename sans-path to check
    :return: Whether it's valid
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

def upload_image(image_file):
    """ Saves image file and returns new location.
    """
    filename = str(uuid.uuid4()) + '.jpg'
    location = os.path.join(crabber.app.config['UPLOAD_FOLDER'], filename)
    try:
        turtle_images.prep_and_save(image_file, location)
        return 'img/user_uploads/' + filename
    except turtle_images.UnidentifiedImageError:
        return None


def hexID(digits=6):
    """ An insecure unique identifier to disambiguate multiple instances of
        automatically generated content on a single page.
    """
    hex_chars = '0123456789ABCDEF'
    hex_digits = [random.choice(hex_chars) for _ in range(digits)]
    return ''.join(hex_digits)


def make_crabatar(username: str):
    crabatar = Crabatar(username)
    return upload_image(crabatar.get_avatar_bytes(format='JPEG'))


def is_banned(ip_addr: str) -> bool:
    ''' Check if IP address is blacklisted or belongs to blacklisted areas.
    '''
    # IP blacklisted
    if ip_addr in BLACKLIST_IP:
        return True

    try:
        location = geo_reader.city(ip_addr)

        # Postal code blacklisted
        if location.postal.code in BLACKLIST_POST_CODE:
            return True

        # City blacklisted
        if location.city.geoname_id in BLACKLIST_CITY_ID:
            return True
    except AddressNotFoundError:
        return False

    return False
