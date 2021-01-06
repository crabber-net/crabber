import calendar
from config import *
import datetime
from extensions import db
from flask import Flask, render_template, request, redirect, session, jsonify
import models
import os
import patterns
from sqlalchemy.sql import func
import utils

app = Flask(__name__, template_folder="./templates")
app.secret_key = 'crabs are better than birds because they can cut their wings right off'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///CRABBER_DATABASE.db'  # Database location
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Max length of user-uploaded files. First number is megabytes.
db.init_app(app)

@app.route("/", methods=("GET", "POST"))
def index():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)

        following_ids = [crab.id for crab in utils.get_current_user().following] + [utils.get_current_user().id]
        molts = models.Molt.query.filter(models.Molt.author_id.in_(following_ids)) \
            .filter_by(deleted=False, is_reply=False).filter(models.Molt.author.has(deleted=False)) \
            .order_by(models.Molt.timestamp.desc()) \
            .paginate(page_n, MOLTS_PER_PAGE, False)
        return render_template('timeline-content.html' if request.args.get("ajax_content") else 'timeline.html', current_page="home", page_n=page_n,
                               molts=molts, current_user=utils.get_current_user())
    else:
        return render_template('welcome.html', current_user=utils.get_current_user(), fullwidth=True, hide_sidebar=True)


@app.route("/wild/", methods=("GET", "POST"))
def wild_west():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)
        molts = models.Molt.query.filter_by(deleted=False, is_reply=False, is_remolt=False) \
            .filter(models.Molt.author.has(deleted=False)).order_by(models.Molt.timestamp.desc()) \
            .paginate(page_n, MOLTS_PER_PAGE, False)
        return render_template('wild-west-content.html' if request.args.get("ajax_content") else 'wild-west.html', current_page="wild-west", page_n=page_n,
                               molts=molts, current_user=utils.get_current_user())
    else:
        return redirect("/login")


@app.route("/notifications/", methods=("GET", "POST"))
def notifications():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)
        notifications = utils.get_current_user().get_notifications(paginated=True, page=page_n)
        return render_template('notifications.html', current_page="notifications",
                               notifications=notifications, current_user=utils.get_current_user())
    else:
        return redirect("/login")


@app.route("/login/", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email, password = request.form.get("email").strip().lower(), request.form.get("password")
        attempted_user = models.Crab.query.filter_by(email=email, deleted=False).first()
        if attempted_user is not None:
            if attempted_user.verify_password(password):
                # Login successful
                session["current_user"] = attempted_user.id
                return redirect("/")
            else:
                return utils.show_error("Incorrect password")
        else:
            return utils.show_error("No account with that email exists")
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

        if utils.validate_email(email):
            if utils.validate_username(username):
                if len(username) in range(4, 32):
                    if patterns.username.fullmatch(username):
                        if password == confirm_password:
                            # Create user account
                            models.Crab.create_new(username=username,
                                            email=email,
                                            password=password,
                                            display_name=display_name)

                            # "Log in"
                            session["current_user"] = models.Crab.query.filter_by(username=username, deleted=False).first().id
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
    recommended_users = models.Crab.query.filter(models.Crab.username.in_(RECOMMENDED_USERS)).all()
    return render_template("signup_success.html", current_user=utils.get_current_user(),
                           recommended_users=recommended_users)


@app.route("/settings/", methods=("GET", "POST"))
def settings():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        return render_template("settings.html", current_page="settings",
                               current_user=utils.get_current_user())


@app.route("/u/<username>/", methods=("GET", "POST"))
@app.route("/user/<username>/", methods=("GET", "POST"))
def user(username):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    else:
        current_tab = request.args.get("tab", default="molts")
        this_user = models.Crab.query.filter_by(deleted=False).filter(models.Crab.username.ilike(username)).first()
        if this_user is not None:
            m_page_n = request.args.get('mp', 1, type=int)
            r_page_n = request.args.get('rp', 1, type=int)
            l_page_n = request.args.get('lp', 1, type=int)
            molts = models.Molt.query.filter_by(author=this_user, deleted=False, is_reply=False).order_by(
                models.Molt.timestamp.desc()).paginate(m_page_n, MOLTS_PER_PAGE, False)
            replies = models.Molt.query.filter_by(author=this_user, deleted=False, is_reply=True) \
                .filter(models.Molt.original_molt.has(deleted=False)).order_by(
                models.Molt.timestamp.desc()).paginate(r_page_n, MOLTS_PER_PAGE, False)
            likes = this_user.get_true_likes(paginated=True, page=l_page_n)
            return render_template('profile.html',
                                   current_page=("own-profile" if this_user == utils.get_current_user() else ""),
                                   molts=molts, current_user=utils.get_current_user(), this_user=this_user, likes=likes,
                                   current_tab=current_tab, replies=replies)
        else:
            return render_template('not-found.html', current_user=utils.get_current_user(), noun="user")


@app.route("/user/<username>/follow<tab>/", methods=("GET", "POST"))
def user_following(username, tab):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        this_user = models.Crab.query.filter_by(username=username, deleted=False).first()
        if this_user:
            followx = this_user.following if tab == "ing" else this_user.followers
            return render_template('followx.html',
                                   current_page=("own-profile" if this_user == utils.get_current_user() else ""),
                                   followx=followx,
                                   current_user=utils.get_current_user(), this_user=this_user, tab="follow" + tab)
        else:
            return render_template('not-found.html', current_user=utils.get_current_user(), noun="user")
    else:
        return redirect("/login")


@app.route("/user/<username>/status/<molt_id>/", methods=("GET", "POST"))
def molt_page(username, molt_id):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    else:
        primary_molt = models.Molt.query.filter_by(id=molt_id).first()
        ajax_content = request.args.get('ajax_content')
        if primary_molt:
            replies = models.Molt.query.filter_by(deleted=False, is_reply=True, original_molt_id=molt_id) \
                .order_by(models.Molt.timestamp.desc())
            return render_template('molt-page-replies.html' if ajax_content else 'molt-page.html', current_page="molt-page", molt=primary_molt,
                                   replies=replies, current_user=utils.get_current_user())
        else:
            return render_template('not-found.html', current_user=utils.get_current_user(), noun="molt")


@app.route("/crabtag/<crabtag>/", methods=("GET", "POST"))
def crabtags(crabtag):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        molts = models.Molt.query.filter(models.Molt.raw_tags.contains((crabtag + "\n"))).filter_by(deleted=False, is_reply=False) \
            .filter(models.Molt.author.has(deleted=False)).order_by(models.Molt.timestamp.desc())
        return render_template('crabtag.html', current_page="crabtag",
                               molts=molts, current_user=utils.get_current_user(), crabtag=crabtag)
    else:
        return redirect("/login")


@app.route("/search/", methods=("GET", "POST"))
def search():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        query = request.args.get('q')
        page_n = request.args.get('p', 1, type=int)
        ajax_content = request.args.get('ajax_content')

        if query:
            crab_results = models.Crab.query.filter_by(deleted=False) \
                .filter(db.or_(models.Crab.display_name.ilike(f'%{query}%'),
                               models.Crab.username.ilike(f'%{query}%')))
            molt_results = models.Molt.query.filter_by(deleted=False, is_reply=False) \
                .filter(models.Molt.content.ilike(f'%{query}%')) \
                .filter(models.Molt.author.has(deleted=False)).order_by(models.Molt.timestamp.desc()) \
                .paginate(page_n, MOLTS_PER_PAGE, False)

        else:
            molt_results = tuple()
            crab_results = tuple()
        return render_template('search-results.html' if ajax_content else 'search.html', current_page="search", 
                               query=query, page_n=page_n, molt_results=molt_results, 
                               crab_results=crab_results, current_user=utils.get_current_user())
    else:
        return redirect("/login")


@app.route("/stats/", methods=("GET", "POST"))
def stats():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Query follow counts for users
    sub = db.session.query(models.following_table.c.following_id, func.count(models.following_table.c.following_id).label('count')) \
        .group_by(models.following_table.c.following_id).subquery()
    most_followed = db.session.query(models.Crab, sub.c.count).outerjoin(sub, models.Crab.id == sub.c.following_id) \
        .order_by(db.desc('count')).filter(models.Crab.deleted == False).first()
    newest_user = models.Crab.query.filter_by(deleted=False).order_by(models.Crab.register_time.desc()).first()

    best_molt = db.session.query(models.Like.molt_id, func.count(models.Like.id)).filter(models.Like.molt.has(deleted=False)) \
        .filter(models.Like.crab.has(deleted=False)) \
        .filter(models.Like.molt.has(models.Molt.author.has(deleted=False))) \
        .order_by(func.count(models.Like.id).desc()).group_by(models.Like.molt_id).first()
    best_molt = models.Molt.query.filter_by(id=best_molt[0]).first(), best_molt[1]
    talked_molt = db.session.query(models.Molt.original_molt_id).filter_by(is_reply=True, deleted=False) \
        .filter(models.Molt.author.has(deleted=False)).filter(models.Molt.original_molt.has(deleted=False)) \
        .filter(models.Molt.original_molt.has(models.Molt.author.has(deleted=False))) \
        .group_by(models.Molt.original_molt_id) \
        .order_by(func.count(models.Molt.id).desc()).first()
    talked_molt = (models.Molt.query.filter_by(id=talked_molt[0]).first(),)
    stats_dict = dict(users=models.Crab.query.filter_by(deleted=False).count(), 
                      mini_stats=[
                          dict(number=models.Molt.query.count(),
                               label="molts sent"),
                          dict(number=models.Molt.query.filter_by(deleted=True).count(),
                               label="molts deleted",
                               sublabel="what are they hiding?"),
                          dict(number=models.Like.query.count(),
                               label="likes given"),
                          dict(number=models.TrophyCase.query.count(),
                               label="trophies awarded")
                      ],
                      crab_king=most_followed,
                      baby_crab=newest_user,
                      best_molt=best_molt,
                      talked_molt=talked_molt)
    return render_template('stats.html', current_user=utils.get_current_user(), stats=stats_dict,
                           current_page='stats')

@app.route("/debug/")
def debug():
    return "You're not supposed to be here. <a href='https://xkcd.com/838/'>This incident will be reported.</a>"

# This wise tortoise, the admin control panel
@app.route("/tortimer/", methods=("GET", "POST"))
def tortimer():
    if utils.get_current_user().username in ADMINS:
        if request.method == "POST":
            action = request.form.get("user_action")
            if request.form.get("target") == "crab":
                target: models.Crab = models.Crab.query.filter_by(id=request.form.get("crab_id")).first()
            else:
                target: models.Molt = models.Molt.query.filter_by(id=request.form.get("molt_id")).first()
            if action == "verify":
                target.verified = True
                db.session.commit()
                return utils.show_message(f"Verified @{target.username}")
            elif action == "delete":
                target.delete()
                return utils.show_message(f"Deleted @{target.username}")
            elif action == "restore":
                target.restore()
                return utils.show_message(f"Restored @{target.username}")
            elif action == "award":
                if request.form.get("award_title"):
                    try:
                        target.award(title=request.form.get("award_title"))
                        return utils.show_message(f"Awarded @{target.username}: {request.form.get('award_title')}")
                    except models.NotFoundInDatabase:
                        return utils.show_error(f"Unable to find trophy with title: {request.form.get('award_title')}")
                else:
                    return utils.show_error(f"No award title found.")

            # PRG pattern
            return redirect(request.url)

        else:
            crab_page_n = request.args.get('pc', 1, type=int)
            molt_page_n = request.args.get('pm', 1, type=int)
            crabs = models.Crab.query \
                .order_by(models.Crab.register_time.desc()) \
                .paginate(crab_page_n, MOLTS_PER_PAGE, False)
            molts = models.Molt.query.order_by(models.Molt.timestamp.desc()) \
                .paginate(molt_page_n, MOLTS_PER_PAGE, False)
            return render_template('tortimer.html', crabs=crabs, molts=molts, current_user=utils.get_current_user(),
                                   crab_page_n=crab_page_n, molt_page_n=molt_page_n)
    else:
        return error_404(BaseException)


@app.route("/ajax_request/<request_type>/")
def ajax_request(request_type):
    if request_type == "unread_notif":
        if request.args.get("crab_id"):
            crab = models.Crab.query.filter_by(id=request.args.get("crab_id")).first()
            if crab:
                return str(crab.unread_notifications)
        return "Crab not found. Did you specify 'crab_id'?"
    if request_type == "molts_since":
        if request.args.get("timestamp"):
            if request.args.get("crab_id"):
                crab = models.Crab.query.filter_by(id=request.args.get("crab_id")).first()
                following_ids = [crab.id for crab in crab.following]
                new_molts = models.Molt.query.filter(models.Molt.author_id.in_(following_ids)) \
                    .filter_by(deleted=False, is_reply=False).filter(models.Molt.author.has(deleted=False)) \
                    .filter(models.Molt.timestamp > datetime.datetime.utcfromtimestamp(int(request.args.get("timestamp"))))
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

            target_user: models.Crab = models.Crab.query.filter_by(username=username).first()
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
            original_molt: models.Molt = models.Molt.query.filter_by(id=original_id, deleted=False) \
                .filter(models.Molt.author.has(deleted=False)).first()

            target_user: models.Crab = models.Crab.query.filter_by(username=username).first()
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
            molt = models.Molt.query.filter_by(id=request.args.get("id")).first()
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
                molts = models.Molt.query.filter(models.Molt.raw_mentions.contains((username + "\n"))) \
                    .filter(models.Molt.timestamp > datetime.datetime.fromtimestamp(int(since_ts))).all()
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
                localize=utils.localize,
                server_start=SERVER_START,
                current_year=now.utcnow().year,
                error=error, msg=msg, location=location)


@app.template_filter()
def commafy(value):
    return format(int(value), ',d')


@app.errorhandler(404)
def error_404(_error_msg):
    return render_template("404.html", current_page="404", current_user=utils.get_current_user())


@app.errorhandler(413)
def file_to_big(_e):
    return utils.show_error("Image must be smaller than 5 megabytes.")


@app.before_request
def before_request():
    # Make sure cookies are still valid
    if session.get("current_user"):
        if not models.Crab.query.filter_by(id=session.get("current_user"), deleted=False).all():
            # Force logout
            session["current_user"] = None
            return redirect("/login")
    # Persist session after browser is closed
    session.permanent = True


if __name__ == '__main__':
    # Start server locally.
    # If using WSGI this will not be run.
    app.run("0.0.0.0", 80, debug=True)
