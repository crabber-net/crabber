import calendar
import config
from crab_mail import CrabMail
import datetime
from flask import (
    abort,
    escape,
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    send_from_directory,
    session,
)
from flask_hcaptcha import hCaptcha
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import models
import os
import patterns
from typing import Iterable, Tuple, Union
import utils
from werkzeug.middleware.profiler import ProfilerMiddleware


def create_app():
    """Initialize flask app."""
    app = Flask(__name__, template_folder="./templates")
    app.secret_key = config.SECRET_KEY
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_PATH
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = config.DEBUG_QUERIES
    app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB
    app.config["HCAPTCHA_SITE_KEY"] = os.getenv("HCAPTCHA_SITE_KEY")
    app.config["HCAPTCHA_SECRET_KEY"] = os.getenv("HCAPTCHA_SECRET_KEY")
    app.config["HCAPTCHA_ENABLED"] = config.HCAPTCHA_ENABLED
    app.config["PROFILER_ENABLED"] = os.getenv("PROFILER_ENABLED")

    register_extensions(app)
    limiter = register_blueprints(app)

    return app, limiter


def register_extensions(app):
    """Registers flask extensions."""
    from extensions import db

    db.init_app(app)


def register_blueprints(app):
    """Registers flask blueprints."""
    import crabber_api
    import crabber_rss

    # Rate-limit site
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=[
            f"{config.SITE_RATE_LIMIT_MINUTE}/minute",
            f"{config.SITE_RATE_LIMIT_SECOND}/second",
        ],
    )
    # Exempt API from site-limits
    limiter.exempt(crabber_api.API)

    # Rate-limit API
    api_limiter = Limiter(app, key_func=crabber_api.get_api_key)
    api_limiter.limit(
        f"{config.API_RATE_LIMIT_SECOND}/second;"
        f"{config.API_RATE_LIMIT_MINUTE}/minute;"
        f"{config.API_RATE_LIMIT_HOUR}/hour"
    )(crabber_api.API)

    # Register API V1 blueprint
    app.register_blueprint(crabber_api.API, url_prefix="/api/v1")
    # Register RSS blueprint
    app.register_blueprint(crabber_rss.RSS, url_prefix="/rss")

    return limiter


app, limiter = create_app()
captcha = hCaptcha(app)

if app.config["PROFILER_ENABLED"]:
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, profile_dir="wsgi_profiler")

if config.MAIL_ENABLED:
    mail = CrabMail(config.MAIL_ADDRESS, config.MAIL_PASSWORD)


@limiter.request_filter
def _endpoint_whitelist():
    """Exempts static files from being rate-limited.

    This is a workaround for a bug with Flask-Limiter == 1.4 and Flask >=
    2.0.
    """
    return request.endpoint == "static"


@app.route("/.well-known/<file>")
def crabcoin(file):
    resp = send_from_directory("static", f"crabcoin/{file}")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp


@app.route("/robots.txt")
def robots():
    return "We <3 robots!"


@app.route("/legal/TOS/")
def terms_of_service():
    with app.open_resource("static/legal/tos.txt", "rb") as f:
        contents = f.read().decode("utf-8")
        return render_template(
            "plaintext.html", title="Terms of Service", content=contents
        )


@app.route("/", methods=("GET", "POST"))
def index():
    current_user = utils.get_current_user()

    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    if current_user is not None:
        page_n = request.args.get("p", 1, type=int)

        if request.args.get("ajax_json"):
            blocks = {}
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"timeline-ajax-{block}.html",
                    current_page="home",
                    page_n=page_n,
                )
            return jsonify(blocks)
        else:
            if request.args.get("ajax_content"):
                molts = current_user.query_timeline().paginate(
                    page_n, config.MOLTS_PER_PAGE, False
                )

                return render_template(
                    "timeline-content.html",
                    current_page="home",
                    page_n=page_n,
                    molts=molts,
                )
            else:
                return render_template(
                    "timeline.html",
                    current_page="home",
                    page_n=page_n,
                )
    else:
        featured_molt = models.Molt.query.filter_by(id=config.FEATURED_MOLT_ID).first()
        featured_user = models.Crab.query.filter_by(
            username=config.FEATURED_CRAB_USERNAME
        ).first()
        return render_template(
            "welcome.html",
            featured_molt=featured_molt,
            featured_user=featured_user,
            fullwidth=True,
            current_page="welcome",
            hide_sidebar=True,
        )


@app.route("/wild/", methods=("GET", "POST"))
def wild_west():
    current_user = utils.get_current_user()

    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    if current_user is not None:
        page_n = request.args.get("p", 1, type=int)
        # Ajax page switching
        if request.args.get("ajax_json"):
            blocks = dict()
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"wild-west-ajax-{block}.html",
                    current_page="wild-west",
                    page_n=page_n,
                )
            return jsonify(blocks)
        else:
            # Ajax content loading
            if request.args.get("ajax_content"):
                molts = current_user.query_wild()
                molts = molts.paginate(page_n, config.MOLTS_PER_PAGE, False)
                return render_template(
                    "wild-west-content.html",
                    current_page="wild-west",
                    page_n=page_n,
                    molts=molts,
                )
            # Page skeleton
            else:
                return render_template(
                    "wild-west.html",
                    current_page="wild-west",
                    page_n=page_n,
                )
    else:
        return redirect("/login")


@app.route("/notifications/", methods=("GET", "POST"))
def notifications():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get("current_user") is not None:
        page_n = request.args.get("p", 1, type=int)
        notifications = utils.get_current_user().get_notifications(
            paginated=True, page=page_n
        )
        if request.args.get("ajax_json"):
            blocks = dict()
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"notifications-ajax-{block}.html",
                    current_page="notifications",
                    notifications=notifications,
                )
            return jsonify(blocks)
        else:
            return render_template(
                "notifications.html",
                current_page="notifications",
                notifications=notifications,
            )
    else:
        return redirect("/login")


@app.route("/login/", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email, password = request.form.get("email").strip().lower(), request.form.get(
            "password"
        )
        attempted_user: models.Crab = models.Crab.query.filter_by(
            email=email, deleted=False
        ).first()
        if attempted_user is not None:
            if attempted_user.verify_password(password):
                if not attempted_user.banned:
                    # Login successful
                    session["current_user"] = attempted_user.id
                    session["current_user_ts"] = attempted_user.register_timestamp
                    return redirect("/")
                else:
                    return utils.show_error(
                        "The account you're attempting to access has been banned."
                    )
            else:
                return utils.show_error("Incorrect password.")
        else:
            return utils.show_error("No account with that email exists.")
    elif session.get("current_user"):
        return redirect("/")
    else:
        login_failed = request.args.get("failed") is not None
        return render_template(
            "login.html",
            current_page="login",
            hide_sidebar=True,
            login_failed=login_failed,
        )


@app.route("/forgotpassword/", methods=("GET", "POST"))
def forgot_password():
    email_sent = False
    if request.method == "POST":
        crab_email = request.form.get("email")
        crab = models.Crab.get_by_email(crab_email)
        if crab and config.MAIL_ENABLED:
            token = crab.generate_password_reset_token()

            # Send email
            body = render_template("password-reset-email.html", crab=crab, token=token)
            if mail.send_mail(crab_email, subject="Reset your password", body=body):
                email_sent = True
            else:
                return utils.show_error(
                    "There was a problem sending your email. Please try again."
                )
        else:
            # Crab not found, still displaying "email sent" for security
            # purposes
            email_sent = True
    elif session.get("current_user"):
        return redirect("/")
    return render_template(
        "forgot-password.html",
        current_page="forgot-password",
        hide_sidebar=True,
        email_sent=email_sent,
    )


@app.route("/resetpassword/", methods=("GET", "POST"))
def reset_password():
    email = request.args.get("email")
    token = request.args.get("token")
    crab = models.Crab.get_by_email(email)
    if crab:
        if crab.verify_password_reset_token(token):
            if request.method == "POST":
                new_pass = request.form.get("password")
                confirm_pass = request.form.get("confirm-password")
                if new_pass == confirm_pass:
                    crab.change_password(new_pass)
                    crab.clear_password_reset_token()
                    return utils.show_message(
                        "Password changed successfully.", redirect_url="/login"
                    )
                else:
                    return utils.show_error(
                        "Passwords do not match.", preserve_arguments=True
                    )
            elif session.get("current_user"):
                return redirect("/")
            else:
                return render_template(
                    "reset-password.html",
                    current_page="reset-password",
                    hide_sidebar=True,
                )
    return utils.show_error(
        "Password reset link is either invalid or expired.", redirect_url="/login"
    )


@app.route("/delete-account/", methods=("GET", "POST"))
def delete_account():
    current_user = utils.get_current_user()

    if request.method == "POST":
        password = request.form.get("password")
        if current_user.verify_password(password):
            current_user.delete()
            session["current_user"] = None
            return redirect("/account-deleted")
        else:
            return utils.show_error("Password incorrect", preserve_arguments=True)
    else:
        if current_user:
            return render_template(
                "delete-account.html", current_page="delete-account", hide_sidebar=True
            )
        else:
            return redirect("/")


@app.route("/account-deleted/")
def account_deleted():
    return render_template(
        "account-deleted.html", current_page="account-deleted", hide_sidebar=True
    )


@app.route("/signup/", methods=("GET", "POST"))
def signup():
    if config.REGISTRATION_ENABLED:
        if request.method == "POST":
            # Validate data
            form = request.form
            email = form.get("email").strip().lower()
            username = form.get("username").strip()
            display_name = form.get("display-name").strip()
            password = form.get("password").strip()
            confirm_password = form.get("confirm-password").strip()

            form_items = {k: v for k, v in request.form.items() if "password" not in k}

            if utils.validate_email(email):
                if utils.validate_username(username):
                    if len(username) in range(3, 32):
                        if patterns.username.fullmatch(username):
                            if not patterns.only_underscores.fullmatch(username):
                                if password == confirm_password:
                                    if password:
                                        if captcha.verify():
                                            # Use referral code if available
                                            referral_code = form.get(
                                                "referral-code"
                                            ).strip()
                                            referrer = None
                                            if referral_code:
                                                referrer = models.ReferralCode.use(
                                                    referral_code
                                                )

                                            # Create user account
                                            models.Crab.create_new(
                                                username=username,
                                                email=email,
                                                password=password,
                                                display_name=display_name,
                                                referrer=referrer,
                                            )

                                            # "Log in"
                                            current_user = models.Crab.query.filter_by(
                                                username=username,
                                                deleted=False,
                                                banned=False,
                                            ).first()
                                            session["current_user"] = current_user.id
                                            session[
                                                "current_user_ts"
                                            ] = current_user.register_timestamp

                                            # Redirect on success
                                            return redirect("/signupsuccess")
                                        else:
                                            return utils.show_error(
                                                "Captcha verification failed",
                                                new_arguments=form_items,
                                            )
                                    else:
                                        return utils.show_error(
                                            "Password cannot be blank",
                                            new_arguments=form_items,
                                        )
                                else:
                                    return utils.show_error(
                                        "Passwords do not match",
                                        new_arguments=form_items,
                                    )
                            else:
                                return utils.show_error(
                                    "Username cannot be ONLY underscores",
                                    new_arguments=form_items,
                                )
                        else:
                            return utils.show_error(
                                "Username must only contain letters, numbers, and "
                                "underscores",
                                new_arguments=form_items,
                            )
                    else:
                        return utils.show_error(
                            "Username must be between 3 and 32 characters",
                            new_arguments=form_items,
                        )
                else:
                    return utils.show_error(
                        "That username is taken", new_arguments=form_items
                    )
            else:
                return utils.show_error(
                    "An account with that email address already exists",
                    new_arguments=form_items,
                )

        elif session.get("current_user"):
            return redirect("/")
        else:
            signup_failed = request.args.get("failed") is not None
            error_msg = request.args.get("error_msg")
            return render_template(
                "signup.html",
                current_page="signup",
                hide_sidebar=True,
                signup_failed=signup_failed,
                error_msg=error_msg,
                referral_code=request.args.get("referral-code"),
            )
    else:
        return render_template(
            "registration-closed.html",
            current_page="registration-closed",
            hide_sidebar=True,
        )


@app.route("/logout/")
def logout():
    session["current_user"] = None
    return redirect("/login")


@app.route("/signupsuccess/", methods=("GET", "POST"))
def signupsuccess():
    if request.method == "POST":
        return utils.common_molt_actions()

    current_user = utils.get_current_user()
    recommended_users = models.Crab.query.filter(
        models.Crab.username.in_(config.RECOMMENDED_USERS)
    ).all()
    if current_user.referrer and current_user.referrer not in recommended_users:
        recommended_users.append(current_user.referrer)
    recommended_users.append
    return render_template(
        "signup_success.html",
        recommended_users=recommended_users,
    )


@app.route("/settings/", methods=("GET", "POST"))
def settings():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        # Handle style preferences
        if request.form.get("user_action") == "style_settings":
            current_user = utils.get_current_user()

            spooky_mode = request.form.get("spooky_mode") == "on"
            light_mode = request.form.get("light_mode") == "on"
            dyslexic_mode = request.form.get("dyslexic_mode") == "on"
            comicsans_mode = request.form.get("comicsans_mode") == "on"

            current_user.set_preference("spooky_mode", spooky_mode)
            current_user.set_preference("light_mode", light_mode)
            current_user.set_preference("dyslexic_mode", dyslexic_mode)
            current_user.set_preference("comicsans_mode", comicsans_mode)
            return "Saved preferences.", 200
        # Everything else
        else:
            return utils.common_molt_actions()

    # Display page
    elif session.get("current_user") is not None:
        if request.args.get("ajax_json"):
            blocks = dict()
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"settings-ajax-{block}.html",
                    current_page="settings",
                )
            return jsonify(blocks)
        else:
            return render_template(
                "settings.html",
                current_page="settings",
            )
    else:
        return redirect("/login")


@app.route("/u/<username>/", methods=("GET", "POST"))
@app.route("/user/<username>/", methods=("GET", "POST"))
def user(username):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    else:
        current_user = utils.get_current_user()
        current_tab = request.args.get("tab", default="molts")
        this_user = models.Crab.get_by_username(username)

        # Check if blocked (if logged in)
        current_user_is_blocked = False
        if current_user and this_user:
            current_user_is_blocked = this_user.is_blocking(current_user)

        if this_user is None or current_user_is_blocked:
            return render_template("not-found.html", noun="user")
        else:
            social_title = f"{this_user.display_name} on Crabber"
            m_page_n = request.args.get("molts-p", 1, type=int)
            r_page_n = request.args.get("replies-p", 1, type=int)
            l_page_n = request.args.get("likes-p", 1, type=int)

            if request.args.get("ajax_json"):
                blocks = dict()
                for block in ("title", "heading", "body"):
                    blocks[block] = render_template(
                        f"profile-ajax-{block}.html",
                        current_page=(
                            "own-profile" if this_user == current_user else ""
                        ),
                        this_user=this_user,
                        current_tab=current_tab,
                    )
                return jsonify(blocks)
            elif request.args.get("ajax_section"):
                section = request.args.get("ajax_section")
                hex_ID = request.args.get("hex_ID")

                molts = replies = likes = None

                if section == "molts":
                    # TODO: Expand threads automatically
                    molts = this_user.query_profile_molts(current_user)
                    if current_user:
                        molts = current_user.filter_molt_query(molts)
                    molts = molts.paginate(m_page_n, config.MOLTS_PER_PAGE, False)
                elif section == "replies":
                    replies = this_user.query_profile_replies(current_user)
                    if current_user:
                        replies = current_user.filter_molt_query(replies)
                    replies = replies.paginate(r_page_n, config.MOLTS_PER_PAGE, False)
                elif section == "likes":
                    likes = this_user.query_likes()
                    if current_user:
                        likes = current_user.filter_molt_query(likes)
                    likes = likes.paginate(l_page_n, config.MOLTS_PER_PAGE)
                return render_template(
                    f"profile-ajax-tab-{section}.html",
                    current_page=("own-profile" if this_user == current_user else ""),
                    molts=molts,
                    this_user=this_user,
                    likes=likes,
                    current_tab=current_tab,
                    replies=replies,
                    hexID=hex_ID,
                )
            else:
                return render_template(
                    "profile.html",
                    current_page=("own-profile" if this_user == current_user else ""),
                    this_user=this_user,
                    current_tab=current_tab,
                    m_page_n=m_page_n,
                    r_page_n=r_page_n,
                    l_page_n=l_page_n,
                    social_title=social_title,
                )


@app.route("/user/<username>/follow<tab>/", methods=("GET", "POST"))
def user_following(username, tab):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get("current_user") is not None:
        this_user = models.Crab.get_by_username(username)
        if this_user is None:
            return render_template("not-found.html", noun="user")
        elif this_user.banned:
            return render_template(
                "not-found.html",
                message="This user has been banned.",
            )
        else:
            followx = None
            if tab == "ing":
                followx = this_user.following
            elif tab == "ers":
                followx = this_user.followers
            elif tab == "ers_you_know":
                followx = utils.get_current_user().get_mutuals_for(this_user)
            return render_template(
                "followx.html",
                current_page=(
                    "own-profile" if this_user == utils.get_current_user() else ""
                ),
                followx=followx,
                this_user=this_user,
                tab="follow" + tab,
            )
    else:
        return redirect("/login")


@app.route("/user/<username>/status/<molt_id>/", methods=("GET", "POST"))
def molt_page(username, molt_id):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    else:
        primary_molt = models.Molt.get_by_ID(molt_id)
        ajax_content = request.args.get("ajax_content")
        current_user = utils.get_current_user()

        # Check if blocked (if logged in)
        is_blocked = False
        if current_user and primary_molt:
            is_blocked = primary_molt.author.is_blocking(
                current_user
            ) or primary_molt.author.is_blocked_by(current_user)

        if (
            primary_molt is None
            or is_blocked
            or primary_molt.author.username != username
        ):
            social_title = "Unavailable Post"
            return render_template("not-found.html", noun="molt")
        elif primary_molt.author.banned:
            social_title = "Unavailable Post"
            return render_template(
                "not-found.html",
                message="The author of this Molt has been banned.",
            )
        else:
            social_title = f"{primary_molt.author.display_name}'s post on Crabber"
            replies = primary_molt.query_replies()
            if current_user:
                replies = current_user.filter_molt_query(replies)
            return render_template(
                "molt-page-replies.html" if ajax_content else "molt-page.html",
                current_page="molt-page",
                molt=primary_molt,
                replies=replies,
                social_title=social_title,
            )


@app.route("/user/<username>/status/<molt_id>/quotes/", methods=("GET", "POST"))
def molt_quotes_page(username, molt_id):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    else:
        primary_molt = models.Molt.get_by_ID(molt_id)
        quotes = primary_molt.query_quotes()
        return render_template(
            "quotes.html",
            current_page="molt-page",
            molt=primary_molt,
            quotes=quotes,
        )


@app.route("/crabtag/<crabtag>/", methods=("GET", "POST"))
def crabtags(crabtag):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get("current_user") is not None:
        page_n = request.args.get("p", 1, type=int)
        if request.args.get("ajax_json"):
            blocks = dict()
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"crabtag-ajax-{block}.html",
                    current_page="crabtag",
                    crabtag=crabtag,
                    page_n=page_n,
                )
            return jsonify(blocks)
        else:
            molts = models.Molt.query_with_tag(crabtag)
            molts = utils.get_current_user().filter_molt_query(molts)
            molts = molts.paginate(page_n, config.MOLTS_PER_PAGE, False)
            return render_template(
                (
                    "crabtag-content.html"
                    if request.args.get("ajax_content")
                    else "crabtag.html"
                ),
                current_page="crabtag",
                page_n=page_n,
                molts=molts,
                crabtag=crabtag,
            )
    else:
        return redirect("/login")


@app.route("/bookmarks/", methods=("GET", "POST"))
def bookmarks():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get("current_user") is not None:
        current_user = utils.get_current_user()
        page_n = request.args.get("p", 1, type=int)
        bookmarks = current_user.query_bookmarks()
        bookmarks = utils.get_current_user().filter_molt_query(bookmarks)
        bookmarks = bookmarks.paginate(page_n, config.MOLTS_PER_PAGE, False)
        if request.args.get("ajax_json"):
            blocks = dict()
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"bookmarks-ajax-{block}.html",
                    current_page="bookmarks",
                    page_n=page_n,
                    bookmarks=bookmarks,
                )
            return jsonify(blocks)
        else:
            return render_template(
                "bookmarks-content.html"
                if request.args.get("ajax_content")
                else "bookmarks.html",
                current_page="bookmarks",
                page_n=page_n,
                bookmarks=bookmarks,
            )
    else:
        return redirect("/login")


@app.route("/search/", methods=("GET", "POST"))
def search():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get("current_user") is not None:
        query = request.args.get("q")
        page_n = request.args.get("p", 1, type=int)
        ajax_content = request.args.get("ajax_content")

        if request.args.get("ajax_json"):
            blocks = dict()
            for block in ("title", "heading", "body"):
                blocks[block] = render_template(
                    f"search-ajax-{block}.html",
                    current_page="search",
                    query=query,
                    page_n=page_n,
                )
            return jsonify(blocks)
        else:
            if query:
                crab_results = models.Crab.search(query)
                crab_results = (
                    utils.get_current_user().filter_user_query_by_not_blocked(
                        crab_results
                    )
                )
                molt_results = models.Molt.search(query)
                molt_results = utils.get_current_user().filter_molt_query(molt_results)
                molt_results = molt_results.paginate(
                    page_n, config.MOLTS_PER_PAGE, False
                )
            else:
                molt_results = tuple()
                crab_results = tuple()

            return render_template(
                "search-results.html" if ajax_content else "search.html",
                current_page="search",
                query=query,
                page_n=page_n,
                molt_results=molt_results,
                crab_results=crab_results,
            )
    else:
        return redirect("/login")


@app.route("/stats/", methods=("GET", "POST"))
def stats():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    current_user = utils.get_current_user()

    # Query follow counts for users
    most_followed = models.Crab.query_most_popular()
    most_referrals = models.Crab.query_most_referrals()
    newest_user = models.Crab.query_all().order_by(models.Crab.register_time.desc())

    if current_user:
        most_followed = current_user.filter_user_query_by_not_blocked(most_followed)
        most_referrals = current_user.filter_user_query_by_not_blocked(most_referrals)
        newest_user = current_user.filter_user_query_by_not_blocked(newest_user)

    most_followed = most_followed.first()
    most_referrals = most_referrals.first()
    newest_user = newest_user.first()

    best_molt = models.Molt.query_most_liked()
    talked_molt = models.Molt.query_most_replied()

    if current_user:
        best_molt = current_user.filter_molt_query(best_molt)
        talked_molt = current_user.filter_molt_query(talked_molt)

    best_molt = best_molt.first()
    talked_molt = talked_molt.first()

    trendy_tag = (models.Crabtag.query_most_popular().first() or (None,))[0]
    if trendy_tag:
        trendy_tag_molts = models.Molt.order_query_by_likes(
            models.Molt.query_with_tag(trendy_tag)
        )
        if current_user:
            trendy_tag_molts = current_user.filter_molt_query(trendy_tag_molts)
        trendy_tag_molts = trendy_tag_molts.limit(3).all()
    else:
        trendy_tag_molts = list()

    stats_dict = dict(
        users=models.Crab.active_user_count(),
        mini_stats=[
            dict(number=models.Molt.total_count(), label="molts sent"),
            dict(
                number=models.Molt.deleted_count(),
                label="molts deleted",
                sublabel="what are they hiding?",
            ),
            dict(number=models.Like.total_count(), label="likes given"),
            dict(number=models.TrophyCase.total_count(), label="trophies awarded"),
        ],
        crab_king=most_followed,
        party_starter=most_referrals,
        baby_crab=newest_user,
        best_molt=best_molt,
        talked_molt=talked_molt,
        trendy_tag=trendy_tag,
        trendy_tag_molts=trendy_tag_molts,
    )

    if request.args.get("ajax_json"):
        blocks = dict()
        for block in ("title", "heading", "body"):
            blocks[block] = render_template(
                f"stats-ajax-{block}.html",
                stats=stats_dict,
                current_page="stats",
            )
        return jsonify(blocks)
    else:
        return render_template(
            "stats.html",
            stats=stats_dict,
            current_page="stats",
        )


@app.route("/debug/")
@app.route("/admin/")
@app.route("/secret/")
def secret():
    return (
        "You're not supposed to be here."
        '<a href="https://xkcd.com/838/">'
        "    This incident will be reported."
        "</a>"
    )


@app.route("/developer/", methods=("GET", "POST"))
def developer():
    current_user = utils.get_current_user()
    access_tokens = models.AccessToken.query.filter_by(
        crab=current_user, deleted=False
    ).all()
    developer_keys = models.DeveloperKey.query.filter_by(
        crab=current_user, deleted=False
    ).all()
    if request.method == "POST":
        action = request.form.get("user_action")

        if action == "create_developer_key":
            if len(developer_keys) < config.API_MAX_DEVELOPER_KEYS:
                models.DeveloperKey.create(current_user)
                return utils.show_message("Created new developer key.")
            else:
                return utils.show_error(
                    f"You are only allowed {config.API_MAX_DEVELOPER_KEYS} "
                    "developer keys."
                )
        elif action == "create_access_token":
            if len(access_tokens) < config.API_MAX_ACCESS_TOKENS:
                models.AccessToken.create(current_user)
                return utils.show_message("Created access token.")
            else:
                return utils.show_error(
                    f"You are only allowed {config.API_MAX_ACCESS_TOKENS} "
                    "access tokens."
                )
        elif action == "delete_developer_key":
            key_id = request.form.get("developer_key_id")
            if key_id:
                key = models.DeveloperKey.query.filter_by(id=key_id).first()
                if key:
                    key.delete()
                    return utils.show_message("Developer key deleted.")
        elif action == "delete_access_token":
            key_id = request.form.get("access_token_id")
            if key_id:
                key = models.AccessToken.query.filter_by(id=key_id).first()
                if key:
                    key.delete()
                    return utils.show_message("Access token deleted.")

        # PRG pattern
        return redirect(request.url)
    else:
        return render_template(
            "developer.html",
            access_tokens=access_tokens,
            developer_keys=developer_keys,
        )


# This wise tortoise, the admin control panel
@app.route("/tortimer/", methods=("GET", "POST"))
def tortimer():
    return "Deprecated."


# The new moderation panel
@app.route("/moderation/", methods=("GET", "POST"))
def moderation():
    if request.method == "POST":
        return utils.moderation_actions()
    else:
        current_user = utils.get_current_user()
        if current_user and current_user.is_moderator:
            viewing = request.args.get("viewing")
            if viewing == "user":
                username = request.args.get("username")
                crab = models.Crab.get_by_username(username, include_invalidated=True)
                return render_template(
                    "moderation-crab.html",
                    crab=crab,
                    current_page="moderation-panel",
                )
            elif viewing == "molt":
                molt_id = request.args.get("molt_id")
                molt = models.Molt.get_by_ID(molt_id, include_invalidated=True)
                return render_template(
                    "moderation-molt.html",
                    molt=molt,
                    current_page="moderation-panel",
                )
            elif viewing == "queue":
                queue = models.Molt.query_reported().limit(10)
                return render_template(
                    "moderation-queue.html",
                    queue=queue,
                    current_page="moderation-panel",
                )
            elif viewing == "logs":
                page_n = request.args.get("p", 1, type=int)
                logs = models.ModLog.query.order_by(
                    models.ModLog.timestamp.desc()
                ).paginate(page_n, 50, False)
                return render_template(
                    "moderation-logs.html",
                    logs=logs,
                    current_page="moderation-panel",
                    page_n=page_n,
                    hide_sidebar=True,
                    extra_width=True,
                )
            else:
                return render_template(
                    "moderation.html",
                    current_page="moderation-panel",
                )
        else:
            return error_404(None)


@app.route("/ajax_request/<request_type>/")
def ajax_request(request_type):
    if request_type == "unread_notif":
        if request.args.get("crab_id"):
            crab = models.Crab.get_by_ID(id=request.args.get("crab_id"))
            if crab:
                return str(crab.unread_notifications)
        return "Crab not found. Did you specify 'crab_id'?"
    if request_type == "molts_since":
        if request.args.get("timestamp"):
            if request.args.get("crab_id"):
                timestamp = datetime.datetime.utcfromtimestamp(
                    int(request.args.get("timestamp"))
                )
                crab = models.Crab.get_by_ID(id=request.args.get("crab_id"))
                new_molts = crab.query_timeline().filter(
                    models.Molt.timestamp > timestamp
                )
                return str(new_molts.count())

            else:
                return "Crab not found. Did you specify 'crab_id'?"

        return "Did not specify 'timestamp'"


@app.route("/api/v0/<action>/", methods=("GET", "POST"))
def api_v0(_action):
    return "Deprecated."


# GLOBAL FLASK TEMPLATE VARIABLES GO HERE
@app.context_processor
def inject_global_vars():
    current_user = utils.get_current_user()
    if current_user:
        spooky_mode = current_user.get_preference("spooky_mode", False)
        light_mode = current_user.get_preference("light_mode", False)
        dyslexic_mode = current_user.get_preference("dyslexic_mode", False)
        comicsans_mode = current_user.get_preference("comicsans_mode", False)
    else:
        spooky_mode = light_mode = dyslexic_mode = comicsans_mode = False
    error = request.args.get("error")
    msg = request.args.get("msg")
    location = request.path
    now = datetime.datetime.utcnow()
    return dict(
        get_fast_molt=models.Molt.get_fast_molt,
        current_user=current_user,
        patterns=patterns,
        user_agent=utils.parse_user_agent() if config.is_debug_server else None,
        sprite_url=config.SPRITE_URL,
        limits=config.LIMITS,
        MOLT_CHAR_LIMIT=config.MOLT_CHAR_LIMIT,
        BASE_URL=config.BASE_URL,
        TIMESTAMP=round(calendar.timegm(now.utctimetuple())),
        IS_WINDOWS=os.name == "nt",
        localize=utils.localize,
        server_start=config.SERVER_START,
        current_year=now.utcnow().year,
        error=error,
        msg=msg,
        location=location,
        uuid=utils.hexID,
        referrer=request.referrer,
        spooky_mode=spooky_mode,
        light_mode=light_mode,
        dyslexic_mode=dyslexic_mode,
        comicsans_mode=comicsans_mode,
        trending_crabtags=models.Crabtag.get_trending(),
        is_debug_server=config.is_debug_server,
        admins=config.ADMINS,
        moderators=config.MODERATORS,
    )


@app.template_filter()
def pluralize(value: Union[Iterable, int], grammar: Tuple[str, str] = ("", "s")):
    """Returns singular or plural string depending on length/value of `value`."""
    count = value if isinstance(value, int) else len(value)
    return grammar[count != 1]


@app.template_filter()
def rich_content(value: str, **kwargs):
    """Render content as HTML for site.

    Parse content string (including embeds, tags, and mentions) and render it as rich
    HTML.
    """
    return utils.parse_rich_content(value, **kwargs)


@app.template_filter()
def social_link(value: str, key: str) -> str:
    """Formats string as social link if possible (Returns safe HTML)."""
    return utils.social_link(value, key)


@app.template_filter()
def commafy(value):
    """Returns string of value with commas seperating the thousands places."""
    return format(int(value), ",d")


@app.template_filter()
def alt_text(url, fallback_text=None):
    """Attempts to get the alt text for a given image url."""
    text = models.ImageDescription.get_alt(url)
    text = text or (
        fallback_text if fallback_text is not None else "No description provided."
    )
    return escape(text)


@app.template_filter()
def string_escape(value):
    """Escapes string to fit in quotations."""
    return value.replace("'", "\\'").replace('"', '\\"')


@app.template_filter()
def pretty_url(url, length=35):
    return utils.pretty_url(url, length)


@app.template_filter()
def debug_log(value):
    print(value)
    return ""


@app.template_filter()
def format_dob(dob: str):
    """Format ISO-8601 as current age in years.

    Any other strings will be passed through.
    """
    return utils.format_dob(dob)


@app.template_filter()
def pretty_age(time: Union[datetime.datetime, int]):
    """Converts datetime to pretty twitter-esque age string."""
    if isinstance(time, int):
        time: datetime.datetime = datetime.datetime.fromtimestamp(time)
    return utils.get_pretty_age(time)


@app.template_filter()
def url_root(url, length=35):
    """Returns the root address of a URL."""
    match = patterns.url_root.match(url)
    if match:
        url = match.group(1)
    if len(url) > length:
        url = f"{url[:length - 3]}..."
    return url


@app.errorhandler(403)
def error_403(_error_msg):
    return render_template("403.html"), 403


@app.errorhandler(404)
def error_404(_error_msg):
    return (
        render_template(
            "404.html",
            current_page="404",
        ),
        404,
    )


@app.errorhandler(413)
def file_too_big(_e):
    return utils.show_error("Image must be smaller than 5 megabytes.")


@app.before_request
def before_request():
    # Check if remote address is banned
    if utils.is_banned(request.remote_addr):
        if request.endpoint != "static":
            return abort(403)

    # Make sure cookies are still valid
    if session.get("current_user"):
        crab_id = session.get("current_user")
        crab = models.Crab.get_security_overview(crab_id)
        current_user_ts = session.get("current_user_ts")

        # Account deleted or banned
        if crab is None or crab.banned or crab.deleted:
            # Force logout
            session["current_user"] = None

            if crab and crab.banned:
                return utils.show_error(
                    "The account you were logged into has been banned.", "/login"
                )
            return utils.show_error(
                "The account you were logged into no longer exists.", "/login"
            )
        # Potential database rollback or exploit
        elif int(crab.register_time.timestamp()) != current_user_ts:
            if current_user_ts:
                # Force logout
                session["current_user"] = None

                return utils.show_error(
                    "Your cookies are invalidated or corrupted. Please attempt"
                    " to log in again.",
                    "/login",
                )
            else:
                session["current_user_ts"] = crab.register_timestamp
    # Persist session after browser is closed
    session.permanent = True


if __name__ == "__main__":
    # Start server locally.
    # If using WSGI this will not be run.
    port = os.getenv("PORT") or 80
    app.run("0.0.0.0", port, debug=True)
