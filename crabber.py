import calendar
from config import *
from crab_mail import CrabMail
import datetime
from flask import abort, Flask, jsonify, render_template, request, redirect, \
    send_from_directory, session
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
    app = Flask(__name__, template_folder="./templates")
    app.secret_key = 'crabs are better than birds because they can cut their wings right off'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///CRABBER_DATABASE.db'  # Database location
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Max length of user-uploaded files. First number is megabytes.
    app.config['HCAPTCHA_SITE_KEY'] = os.getenv('HCAPTCHA_SITE_KEY')
    app.config['HCAPTCHA_SECRET_KEY'] = os.getenv('HCAPTCHA_SECRET_KEY')
    app.config['HCAPTCHA_ENABLED'] = HCAPTCHA_ENABLED
    app.config['PROFILER_ENABLED'] = os.getenv('PROFILER_ENABLED')

    limiter = register_extensions(app)
    register_blueprints(app)

    return app, limiter


def register_extensions(app):
    from extensions import db

    db.init_app(app)


def register_blueprints(app):
    import crabber_api
    import crabber_rss

    # Rate-limit site
    limiter = Limiter(app, key_func=get_remote_address,
                      default_limits=[f'{SITE_RATE_LIMIT_MINUTE}/minute',
                                      f'{SITE_RATE_LIMIT_SECOND}/second'])
    # Exempt API from site-limits
    limiter.exempt(crabber_api.API)

    # Rate-limit API
    api_limiter = Limiter(app, key_func=crabber_api.get_api_key)
    api_limiter.limit(f'{API_RATE_LIMIT_SECOND}/second;'
                      f'{API_RATE_LIMIT_MINUTE}/minute;'
                      f'{API_RATE_LIMIT_HOUR}/hour')(crabber_api.API)

    # Register API V1 blueprint
    app.register_blueprint(crabber_api.API, url_prefix='/api/v1')
    # Register RSS blueprint
    app.register_blueprint(crabber_rss.RSS, url_prefix='/rss')


app, limiter = create_app()
captcha = hCaptcha(app)
if app.config['PROFILER_ENABLED']:
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, 
                                      profile_dir='wsgi_profiler')

if MAIL_ENABLED:
    mail = CrabMail(MAIL_JSON)


@app.route('/.well-known/<file>')
def crabcoin(file):
    resp = send_from_directory('static', f'crabcoin/{file}')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return resp


@app.route('/robots.txt')
def robots():
    return 'We <3 robots!'


@app.route("/", methods=("GET", "POST"))
def index():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)

        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(
                    f'timeline-ajax-{block}.html',
                    current_page="home",
                    page_n=page_n,
                    current_user=utils.get_current_user()
                )
            return jsonify(blocks)
        else:
            molts = utils.get_current_user() \
                .query_timeline() \
                .paginate(page_n, MOLTS_PER_PAGE, False)

            return render_template(
                'timeline-content.html' if request.args.get("ajax_content") \
                else 'timeline.html',
                current_page="home",
                page_n=page_n,
                molts=molts,
                current_user=utils.get_current_user()
            )
    else:
        featured_molt = models.Molt.query.filter_by(id=FEATURED_MOLT_ID).first()
        featured_user = models.Crab.query.filter_by(username=FEATURED_CRAB_USERNAME).first()
        return render_template('welcome.html', featured_molt=featured_molt,
                               current_user=utils.get_current_user(),
                               featured_user=featured_user, fullwidth=True,
                               current_page='welcome', hide_sidebar=True)


@app.route("/wild/", methods=("GET", "POST"))
def wild_west():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)
        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(f'wild-west-ajax-{block}.html',
                                                current_page="wild-west",
                                                page_n=page_n,
                                                current_user=utils.get_current_user())
            return jsonify(blocks)
        else:
            molts = models.Molt.query_all(include_replies=False,
                                          include_quotes=False)
            molts = utils.get_current_user().filter_molt_query(molts)
            molts = molts.paginate(page_n, MOLTS_PER_PAGE, False)
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
        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(f'notifications-ajax-{block}.html',
                                                current_page="notifications",
                                                notifications=notifications,
                                                current_user=utils.get_current_user())
            return jsonify(blocks)
        else:
            return render_template('notifications.html', current_page="notifications",
                                   notifications=notifications,
                                   current_user=utils.get_current_user())
    else:
        return redirect("/login")


@app.route("/login/", methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email, password = request.form.get('email').strip().lower(), request.form.get('password')
        attempted_user = models.Crab.query.filter_by(email=email, deleted=False).first()
        if attempted_user is not None:
            if attempted_user.verify_password(password):
                if not attempted_user.banned:
                    # Login successful
                    session['current_user'] = attempted_user.id
                    return redirect("/")
                else:
                    return utils.show_error('The account you\'re attempting to access has been banned.')
            else:
                return utils.show_error('Incorrect password.')
        else:
            return utils.show_error('No account with that email exists.')
    elif session.get('current_user'):
        return redirect('/')
    else:
        login_failed = request.args.get('failed') is not None
        return render_template('login.html', current_page='login', hide_sidebar=True, login_failed=login_failed)


@app.route("/forgotpassword/", methods=('GET', 'POST'))
def forgot_password():
    email_sent = False
    if request.method == 'POST':
        crab_email = request.form.get('email')
        crab = models.Crab.get_by_email(crab_email)
        if crab and MAIL_ENABLED:
            token = crab.generate_password_reset_token()

            # Send email
            body = render_template('password-reset-email.html',
                                   crab=crab, token=token)
            if mail.send_mail(crab_email, subject='Reset your password',
                              body=body):
                email_sent = True
            else:
                return show_error('There was a problem sending your email. '
                                  'Please try again.')
        else:
            # Crab not found, still displaying "email sent" for security
            # purposes
            email_sent = True
    elif session.get('current_user'):
        return redirect('/')
    return render_template('forgot-password.html',
                           current_page='forgot-password',
                           hide_sidebar=True, email_sent=email_sent)


@app.route("/resetpassword/", methods=('GET', 'POST'))
def reset_password():
    email = request.args.get('email')
    token = request.args.get('token')
    crab = models.Crab.get_by_email(email)
    if crab:
        if crab.verify_password_reset_token(token):
            if request.method == 'POST':
                new_pass = request.form.get('password')
                confirm_pass = request.form.get('confirm-password')
                if new_pass == confirm_pass:
                    crab.change_password(new_pass)
                    crab.clear_password_reset_token()
                    return utils.show_message('Password changed successfully.',
                                              redirect_url='/login')
                else:
                    return utils.show_error('Passwords do not match.',
                                            preserve_arguments=True)
            elif session.get('current_user'):
                return redirect('/')
            else:
                return render_template('reset-password.html',
                                       current_page='reset-password',
                                       hide_sidebar=True)
    return utils.show_error('Password reset link is either invalid or '
                            'expired.', redirect_url='/login')


@app.route("/delete-account/", methods=('GET', 'POST'))
def delete_account():
    current_user = utils.get_current_user()

    if request.method == 'POST':
        password = request.form.get('password')
        if current_user.verify_password(password):
            current_user.delete()
            session['current_user'] = None
            return redirect('/account-deleted')
        else:
            return utils.show_error('Password incorrect',
                                    preserve_arguments=True)
    else:
        if current_user:
            return render_template('delete-account.html',
                                   current_page='delete-account',
                                   hide_sidebar=True)
        else:
            return redirect('/')


@app.route("/account-deleted/")
def account_deleted():
    return render_template('account-deleted.html',
                           current_page='account-deleted',
                           hide_sidebar=True)


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
                if len(username) in range(3, 32):
                    if patterns.username.fullmatch(username):
                        if not patterns.only_underscores.fullmatch(username):
                            if password == confirm_password:
                                if password:
                                    if captcha.verify():
                                        # Create user account
                                        models.Crab.create_new(username=username,
                                                            email=email,
                                                            password=password,
                                                            display_name=display_name)

                                        # "Log in"
                                        session["current_user"] = models.Crab.query.filter_by(username=username, deleted=False, banned=False).first().id
                                        # Redirect to let the user know it succeeded
                                        return redirect("/signupsuccess")
                                    else:
                                        return redirect("/signup?failed&error_msg=Captcha verification failed")
                                else:
                                    return redirect("/signup?failed&error_msg=Password cannot be blank")
                            else:
                                return redirect("/signup?failed&error_msg=Passwords do not match")
                        else:
                            return redirect("/signup?failed&error_msg=Username cannot be ONLY underscores.")
                    else:
                        return redirect("/signup?failed&error_msg=Username must only contain \
                                        letters, numbers, and underscores")
                else:
                    return redirect("/signup?failed&error_msg=Username must be at least 3 characters and less than 32")
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
        # Handle style preferences
        if request.form.get('user_action') == 'style_settings':
            current_user = utils.get_current_user()

            light_mode = request.form.get('light_mode') == 'on'
            dyslexic_mode = request.form.get('dyslexic_mode') == 'on'
            comicsans_mode = request.form.get('comicsans_mode') == 'on'

            current_user.set_preference('light_mode', light_mode)
            current_user.set_preference('dyslexic_mode', dyslexic_mode)
            current_user.set_preference('comicsans_mode', comicsans_mode)
            return 'Saved preferences.', 200
        # Everything else
        else:
            return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(f'settings-ajax-{block}.html',
                                                current_page='settings',
                                                current_user=utils.get_current_user())
            return jsonify(blocks)
        else:
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
        current_user = utils.get_current_user()
        current_tab = request.args.get("tab", default="molts")
        this_user = models.Crab.get_by_username(username)

        # Check if blocked (if logged in)
        current_user_is_blocked = False
        if current_user and this_user:
            current_user_is_blocked = this_user.is_blocking(current_user)

        if this_user is None or current_user_is_blocked:
            return render_template('not-found.html', current_user=current_user, noun='user')
        else:
            social_title = f'{this_user.display_name} on Crabber'
            m_page_n = request.args.get('molts-p', 1, type=int)
            r_page_n = request.args.get('replies-p', 1, type=int)
            l_page_n = request.args.get('likes-p', 1, type=int)

            if request.args.get('ajax_json'):
                blocks = dict()
                for block in ('title', 'heading', 'body'):
                    blocks[block] = render_template(
                        f'profile-ajax-{block}.html',
                        current_page=("own-profile" if this_user == current_user else ""),
                        current_user=current_user,
                        this_user=this_user, likes=likes,
                        current_tab=current_tab, replies=replies
                    )
                return jsonify(blocks)
            elif request.args.get('ajax_section'):
                section = request.args.get('ajax_section')
                hex_ID = request.args.get('hex_ID')

                molts = replies = likes = None

                if section == 'molts':
                    molts = this_user.query_molts() \
                        .filter_by(is_reply=False)
                    if current_user:
                        molts = current_user.filter_molt_query(molts)
                    molts = molts.paginate(m_page_n, MOLTS_PER_PAGE, False)
                elif section == 'replies':
                    replies = this_user.query_replies()
                    if current_user:
                        replies = current_user.filter_molt_query(replies)
                    replies = replies.paginate(m_page_n, MOLTS_PER_PAGE, False)
                elif section == 'likes':
                    likes = this_user.query_likes()
                    if current_user:
                        likes = current_user.filter_molt_query(likes)
                    likes = likes.paginate(l_page_n, MOLTS_PER_PAGE)
                return render_template(f'profile-ajax-tab-{section}.html',
                                       current_page=("own-profile" if this_user == current_user else ""),
                                       molts=molts, current_user=current_user, this_user=this_user, likes=likes,
                                       current_tab=current_tab, replies=replies, hexID=hex_ID)
            else:
                return render_template('profile.html',
                                       current_page=("own-profile" if this_user == current_user else ""),
                                       current_user=current_user, this_user=this_user,
                                       current_tab=current_tab, m_page_n=m_page_n,
                                       r_page_n=r_page_n, l_page_n=l_page_n,
                                       social_title=social_title)


@app.route("/user/<username>/follow<tab>/", methods=("GET", "POST"))
def user_following(username, tab):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        this_user = models.Crab.get_by_username(username)
        if this_user is None:
            return render_template('not-found.html', current_user=utils.get_current_user(), noun="user")
        elif this_user.banned:
            return render_template('not-found.html', current_user=utils.get_current_user(),
                                   message='This user has been banned.')
        else:
            followx = None
            if tab == 'ing':
                followx = this_user.following
            elif tab == 'ers':
                followx = this_user.followers
            elif tab == 'ers_you_know':
                followx = utils.get_current_user().get_mutuals_for(this_user)
            return render_template('followx.html',
                                   current_page=("own-profile" if this_user == utils.get_current_user() else ""),
                                   followx=followx,
                                   current_user=utils.get_current_user(), this_user=this_user, tab="follow" + tab)
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
        ajax_content = request.args.get('ajax_content')
        current_user = utils.get_current_user()

        # Check if blocked (if logged in)
        is_blocked = False
        if current_user and primary_molt:
            is_blocked = primary_molt.author.is_blocking(current_user) \
                or primary_molt.author.is_blocked_by(current_user)

        if primary_molt is None \
           or is_blocked \
           or primary_molt.author.username != username:
            social_title = f'Unavailable Post'
            return render_template('not-found.html', current_user=utils.get_current_user(), noun="molt")
        elif primary_molt.author.banned:
            social_title = f'Unavailable Post'
            return render_template('not-found.html', current_user=utils.get_current_user(),
                                   message='The author of this Molt has been banned.')
        else:
            social_title = f'{primary_molt.author.display_name}\'s post on Crabber'
            replies = primary_molt.query_replies()
            if current_user:
                replies = current_user.filter_molt_query(replies)
            return render_template('molt-page-replies.html' if ajax_content else 'molt-page.html', current_page="molt-page", molt=primary_molt,
                                   replies=replies, current_user=utils.get_current_user(),
                                   social_title=social_title)


@app.route("/user/<username>/status/<molt_id>/quotes/", methods=("GET", "POST"))
def molt_quotes_page(username, molt_id):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    else:
        primary_molt = models.Molt.get_by_ID(molt_id)
        quotes = primary_molt.query_quotes()
        return render_template('quotes.html', current_page="molt-page", molt=primary_molt,
                               quotes=quotes, current_user=utils.get_current_user())


@app.route("/crabtag/<crabtag>/", methods=("GET", "POST"))
def crabtags(crabtag):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        page_n = request.args.get('p', 1, type=int)
        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(f'crabtag-ajax-{block}.html',
                                                current_page="crabtag",
                                                crabtag=crabtag,
                                                page_n=page_n,
                                                current_user=utils.get_current_user())
            return jsonify(blocks)
        else:
            molts = models.Molt.query_with_tag(crabtag)
            molts = utils.get_current_user().filter_molt_query(molts)
            molts = molts.paginate(page_n, MOLTS_PER_PAGE, False)
            return render_template('crabtag-content.html' if request.args.get("ajax_content") else 'crabtag.html', current_page="crabtag", page_n=page_n,
                                   molts=molts, current_user=utils.get_current_user(), crabtag=crabtag)
    else:
        return redirect("/login")


@app.route("/bookmarks/", methods=("GET", "POST"))
def bookmarks():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return utils.common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        current_user = utils.get_current_user()
        page_n = request.args.get('p', 1, type=int)
        bookmarks = current_user.query_bookmarks()
        bookmarks = utils.get_current_user().filter_molt_query(bookmarks)
        bookmarks = bookmarks.paginate(page_n, MOLTS_PER_PAGE, False)
        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(f'bookmarks-ajax-{block}.html',
                                                current_page='bookmarks',
                                                page_n=page_n, bookmarks=bookmarks,
                                                current_user=utils.get_current_user())
            return jsonify(blocks)
        else:
            return render_template('bookmarks-content.html' if request.args.get('ajax_content') else 'bookmarks.html',
                                   current_page='bookmarks', page_n=page_n,
                                   bookmarks=bookmarks, current_user=utils.get_current_user())
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

        if request.args.get('ajax_json'):
            blocks = dict()
            for block in ('title', 'heading', 'body'):
                blocks[block] = render_template(f'search-ajax-{block}.html',
                                                current_page="search",
                                                query=query, page_n=page_n,
                                                current_user=utils.get_current_user())
            return jsonify(blocks)
        else:
            if query:
                crab_results = models.Crab.search(query)
                crab_results = utils.get_current_user().filter_user_query_by_not_blocked(crab_results)
                molt_results = models.Molt.search(query)
                molt_results = utils.get_current_user().filter_molt_query(molt_results)
                molt_results = molt_results.paginate(page_n, MOLTS_PER_PAGE, False)
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
    most_followed = models.Crab.query_most_popular()
    most_followed = utils.get_current_user().filter_user_query_by_not_blocked(most_followed)
    most_followed = most_followed.first()
    newest_user = models.Crab.query_all() \
        .order_by(models.Crab.register_time.desc())
    newest_user = utils.get_current_user().filter_user_query_by_not_blocked(newest_user)
    newest_user = newest_user.first()

    best_molt = models.Molt.query_most_liked()
    best_molt = utils.get_current_user().filter_molt_query(best_molt)
    best_molt = best_molt.first()
    talked_molt = models.Molt.query_most_replied()
    talked_molt = utils.get_current_user().filter_molt_query(talked_molt)
    talked_molt = talked_molt.first()
    trendy_tag = models.Crabtag.query_most_popular().first()[0]
    trendy_tag_molts = models.Molt.order_query_by_likes(trendy_tag.query_molts())
    trendy_tag_molts = utils.get_current_user().filter_molt_query(trendy_tag_molts)
    trendy_tag_molts = trendy_tag_molts.limit(3).all()
    stats_dict = dict(users=models.Crab.query.filter_by(deleted=False, banned=False).count(),
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
                      talked_molt=talked_molt,
                      trendy_tag=trendy_tag,
                      trendy_tag_molts=trendy_tag_molts)
    if request.args.get('ajax_json'):
        blocks = dict()
        for block in ('title', 'heading', 'body'):
            blocks[block] = render_template(f'stats-ajax-{block}.html',
                                            current_user=utils.get_current_user(),
                                            stats=stats_dict, current_page='stats')
        return jsonify(blocks)
    else:
        return render_template('stats.html', current_user=utils.get_current_user(),
                               stats=stats_dict, current_page='stats')


@app.route("/debug/")
@app.route("/admin/")
@app.route("/secret/")
def secret():
    return "You're not supposed to be here. <a href='https://xkcd.com/838/'>This incident will be reported.</a>"


@app.route("/developer/", methods=("GET", "POST"))
def developer():
    current_user = utils.get_current_user()
    access_tokens = models.AccessToken.query.filter_by(crab=current_user,
                                                       deleted=False).all()
    developer_keys = models.DeveloperKey.query.filter_by(crab=current_user,
                                                         deleted=False).all()
    if request.method == "POST":
        action = request.form.get("user_action")

        if action == 'create_developer_key':
            if len(developer_keys) < API_MAX_DEVELOPER_KEYS:
                models.DeveloperKey.create(current_user)
                return utils.show_message('Created new developer key.')
            else:
                return utils.show_error(
                    f'You are only allowed {API_MAX_DEVELOPER_KEYS} '
                    'developer keys.')
        elif action == 'create_access_token':
            if len(access_tokens) < API_MAX_ACCESS_TOKENS:
                models.AccessToken.create(current_user)
                return utils.show_message('Created access token.')
            else:
                return utils.show_error(
                    f'You are only allowed {API_MAX_ACCESS_TOKENS} '
                    'access tokens.')
        elif action == 'delete_developer_key':
            key_id = request.form.get('developer_key_id')
            if key_id:
                key = models.DeveloperKey.query.filter_by(id=key_id).first()
                if key:
                    key.delete()
                    return utils.show_message('Developer key deleted.')
        elif action == 'delete_access_token':
            key_id = request.form.get('access_token_id')
            if key_id:
                key = models.AccessToken.query.filter_by(id=key_id).first()
                if key:
                    key.delete()
                    return utils.show_message('Access token deleted.')

        # PRG pattern
        return redirect(request.url)
    else:
        return render_template('developer.html',
                               access_tokens=access_tokens,
                               developer_keys=developer_keys,
                               current_user=current_user)


# This wise tortoise, the admin control panel
@app.route("/tortimer/", methods=("GET", "POST"))
def tortimer():
    from extensions import db
    if utils.get_current_user().username in ADMINS:
        if request.method == "POST":
            action = request.form.get("user_action")
            if request.form.get("target") == "crab":
                target: models.Crab = models.Crab.query.filter_by(id=request.form.get("crab_id")).first()
            else:
                target: models.Molt = models.Molt.query.filter_by(id=request.form.get("molt_id")).first()
            if action == "verify":
                target.verify()
                return utils.show_message(f"Verified @{target.username}")
            elif action == "delete":
                target.delete()
                if isinstance(target, models.Crab):
                    return utils.show_message(f"Deleted @{target.username}")
                return utils.show_message("Deleted Molt")
            elif action == "restore":
                target.restore()
                if isinstance(target, models.Crab):
                    return utils.show_message(f"Restored @{target.username}")
                return utils.show_message("Restored Molt")
            elif action == "ban":
                target.ban()
                return utils.show_message(f"Banned @{target.username}")
            elif action == "unban":
                target.unban()
                return utils.show_message(f"Unbanned @{target.username}")
            elif action == "approve":
                target.approve()
                return utils.show_message("Approved Molt")
            elif action == "award":
                if request.form.get("award_title"):
                    try:
                        target.award(title=request.form.get("award_title"))
                        return utils.show_message(f"Awarded @{target.username}: {request.form.get('award_title')}")
                    except models.NotFoundInDatabase:
                        return utils.show_error(f"Unable to find trophy with title: {request.form.get('award_title')}")
                else:
                    return utils.show_error("No award title found.")

            # PRG pattern
            return redirect(request.url)

        else:
            crab_page_n = request.args.get('pc', 1, type=int)
            molt_page_n = request.args.get('pm', 1, type=int)
            crabs = models.Crab.query \
                .order_by(models.Crab.register_time.desc()) \
                .paginate(crab_page_n, MOLTS_PER_PAGE, False)
            reports = models.Molt.query_all() \
                .filter_by(approved=False, is_remolt=False) \
                .order_by(models.Molt.reports.desc(),
                          models.Molt.timestamp.desc()) \
                .paginate(molt_page_n, MOLTS_PER_PAGE, False)
            return render_template('tortimer.html',
                                   crabs=crabs, reports=reports,
                                   current_user=utils.get_current_user(),
                                   crab_page_n=crab_page_n, molt_page_n=molt_page_n)
    else:
        return error_404(BaseException)


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
                new_molts = crab.query_timeline() \
                    .filter(models.Molt.timestamp > timestamp)
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

            target_user: models.Crab = models.Crab.get_by_username(username)
            if target_user:
                if target_user.verify_password(password):
                    if content:
                        new_molt = target_user.molt(content,
                                                    source='Crabber API')
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
            original_molt: models.Molt = models.Molt.get_by_ID(original_id)

            target_user: models.Crab = models.Crab.get_by_username(username)
            if target_user:
                if target_user.verify_password(password):
                    if content:
                        if original_molt:
                            new_molt = original_molt.reply(target_user,
                                                           content,
                                                           source='Crabber API')
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
            molt_id = request.args.get("id")
            molt = models.Molt.get_by_ID(molt_id)
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
    current_user = utils.get_current_user()
    if current_user:
        light_mode = current_user.get_preference('light_mode', False)
        dyslexic_mode = current_user.get_preference('dyslexic_mode', False)
        comicsans_mode = current_user.get_preference('comicsans_mode', False)
    else:
        light_mode = dyslexic_mode = comicsans_mode = False
    error = request.args.get("error")
    msg = request.args.get("msg")
    location = request.path
    now = datetime.datetime.utcnow()
    return dict(
        MOLT_CHAR_LIMIT=MOLT_CHAR_LIMIT,
        BASE_URL=BASE_URL,
        TIMESTAMP=round(calendar.timegm(now.utctimetuple())),
        IS_WINDOWS=os.name == "nt",
        localize=utils.localize,
        server_start=SERVER_START,
        current_year=now.utcnow().year,
        error=error, msg=msg, location=location,
        uuid=utils.hexID, referrer=request.referrer,
        light_mode=light_mode,
        dyslexic_mode=dyslexic_mode,
        comicsans_mode=comicsans_mode,
        trending_crabtags=models.Crabtag.get_trending(),
        is_debug_server=is_debug_server,
    )


@app.template_filter()
def pluralize(value: Union[Iterable, int], grammar: Tuple[str, str] = ('', 's')):
    """ Returns singular or plural string depending on length/value of `value`.
    """
    count = value if isinstance(value, int) else len(value)
    return grammar[count != 1]


@app.template_filter()
def commafy(value):
    """ Returns string of value with commas seperating the thousands places.
    """
    return format(int(value), ',d')


@app.template_filter()
def pretty_url(url, length=35):
    """ Returns a prettier/simplified version of a URL.
    """
    match = patterns.pretty_url.match(url)
    if match:
        url = match.group(1)
    if len(url) > length:
        url = f'{url[:length - 3]}...'
    return url


@app.template_filter()
def pretty_age(time: Union[datetime.datetime, int]):
    """ Converts datetime to pretty twitter-esque age string. (Wrapper for
        `utils.get_pretty_age`.
        :param time:
        :return: Age string
    """
    if isinstance(time, int):
        time: datetime.datetime = datetime.datetime.fromtimestamp(time)
    return utils.get_pretty_age(time)


@app.template_filter()
def url_root(url, length=35):
    """ Returns the root address of a URL.
    """
    match = patterns.url_root.match(url)
    if match:
        url = match.group(1)
    if len(url) > length:
        url = f'{url[:length - 3]}...'
    return url


@app.errorhandler(403)
def error_403(_error_msg):
    return render_template('403.html'), 403


@app.errorhandler(404)
def error_404(_error_msg):
    return render_template("404.html", current_page="404",
                           current_user=utils.get_current_user()), 404


@app.errorhandler(413)
def file_too_big(_e):
    return utils.show_error("Image must be smaller than 5 megabytes.")


@app.before_request
def before_request():
    # Check if remote address is banned
    if utils.is_banned(request.remote_addr):
        if request.endpoint != 'static':
            return abort(403)

    # Make sure cookies are still valid
    if session.get('current_user'):
        crab_id = session.get('current_user')
        if not models.Crab.get_by_ID(id=crab_id):
            # Force logout
            session['current_user'] = None
            if models.Crab.get_by_ID(id=crab_id, include_invalidated=True) \
               .banned:
                return utils.show_error('The account you were logged into has '
                                        'been banned.', '/login')
            return utils.show_error('The account you were logged into no '
                                    'longer exists.', '/login')
    # Persist session after browser is closed
    session.permanent = True


if __name__ == '__main__':
    # Start server locally.
    # If using WSGI this will not be run.
    port = os.getenv('PORT') or 80
    app.run("0.0.0.0", port, debug=True)
