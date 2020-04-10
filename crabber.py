import datetime
from flask import Flask, render_template, request, redirect, escape, session, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from passlib.hash import sha256_crypt
import re
import uuid
from werkzeug.exceptions import RequestEntityTooLarge

# Regex stuff
mention_pattern = re.compile(r'(?<!\\)@([\w]{1,32})(?!\w)')
tag_pattern = re.compile(r'(?<!\\)%([\w]{1,16})(?!\w)')
username_pattern = re.compile(r'^\w+$')

# User uploads config
UPLOAD_FOLDER = 'static/img/user_uploads' if os.name == "nt" else "/var/www/crabber/crabber/static/img/user_uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# App config
app = Flask(__name__, template_folder="./templates")
db = SQLAlchemy(app)
app.secret_key = 'crabs are better than birds because they can cut their wings right off'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///CRABBER_DATABASE.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# DATABASE #############################################################################################################

following_table = db.Table('following',
                           db.Column('id', db.Integer, primary_key=True),
                           db.Column('follower_id', db.Integer, db.ForeignKey('crab.id')),
                           db.Column('following_id', db.Integer, db.ForeignKey('crab.id')))


# User database class
class Crab(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # User info
    username = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    display_name = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.String(140), nullable=False,
                    server_default="This user is boring and has no bio.")
    verified = db.Column(db.Boolean, nullable=False,
                         default=False)
    avatar = db.Column(db.String(140), nullable=False,
                       server_default="img/avatar.jpg")
    banner = db.Column(db.String(140), nullable=False,
                       server_default="img/banner.png")
    register_time = db.Column(db.DateTime, nullable=False,
                              default=datetime.datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False,
                        default=False)

    # Dynamic relationships
    molts = db.relationship('Molt', back_populates='author')
    following = db.relationship('Crab',
                                secondary=following_table,
                                primaryjoin=id == following_table.c.follower_id,
                                secondaryjoin=id == following_table.c.following_id,
                                backref=db.backref('followers'))
    likes = db.relationship('Like')

    def __repr__(self):
        return f"<Crab '{self.username}'>"

    @property
    def true_likes(self):
        return [like.molt for like in self.likes if like.molt.deleted is False]

    def follow(self, crab):
        if crab not in self.following:
            self.following.append(crab)
            db.session.commit()

    def unfollow(self, crab):
        if crab in self.following:
            self.following.remove(crab)
            db.session.commit()

    def verify_password(self, password):
        return sha256_crypt.verify(password, self.password)

    def molt(self, content, **kwargs):
        new_molt = Molt(author=self, content=content[:140], **kwargs)
        db.session.add(new_molt)
        db.session.commit()
        return new_molt

    def delete(self):
        self.deleted = True

    def is_following(self, crab):
        return db.session.query(following_table).filter((following_table.c.follower_id == self.id) &
                                                        (following_table.c.following_id == crab.id))

    def has_liked(self, molt):
        return bool(Like.query.filter_by(molt=molt, crab=self).all())

    def has_remolted(self, molt):
        return bool(Molt.query.filter_by(is_remolt=True, original_molt=molt, author=self, deleted=False).all())

    @staticmethod
    def create_new(**kwargs):
        kwargs["password"] = Crab.hash_pass(kwargs["password"])
        new_crab = Crab(**kwargs)
        db.session.add(new_crab)
        db.session.commit()
        return new_crab

    @staticmethod
    def hash_pass(password):
        new_hash = sha256_crypt.encrypt(password)
        return new_hash


# Molt database class, equivalent to a Tweet
class Molt(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Static info
    author_id = db.Column(db.Integer, db.ForeignKey('crab.id'),
                          nullable=False)
    author = db.relationship('Crab', back_populates='molts')
    content = db.Column(db.String(140), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False,
                          default=datetime.datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False,
                        default=False)
    raw_mentions = db.Column(db.String, nullable=False,
                             server_default="")
    raw_tags = db.Column(db.String, nullable=False,
                         server_default="")
    image = db.Column(db.String(1024), nullable=True)

    # Remolt/reply information
    is_remolt = db.Column(db.Boolean, nullable=False, default=False)
    is_reply = db.Column(db.Boolean, nullable=False, default=False)
    original_molt_id = db.Column(db.Integer, db.ForeignKey('molt.id'))
    original_molt = db.relationship('Molt', remote_side=[id], backref='remolts')

    # Dynamic relationships
    # replies
    # likes
    likes = db.relationship('Like')

    # Custom initialization required to process tags and mentions
    def __init__(self, **kwargs):
        super(Molt, self).__init__(**kwargs)
        for tag in tag_pattern.findall(self.content):
            if self.raw_tags is None:
                self.raw_tags = ""
            self.raw_tags += tag + "\n"
        for user in mention_pattern.findall(self.content):
            if self.raw_mentions is None:
                self.raw_mentions = ""
            self.raw_mentions += user[1:] + "\n"

    def __repr__(self):
        return f"<Molt by '{self.author.username}'>"

    @property
    def rich_content(self):
        new_content = str(escape(self.content)).replace("\n", "<br>")
        new_content = Molt.label_mentions(new_content)
        new_content = Molt.label_crabtags(new_content)
        return new_content

    @property
    def tags(self):
        return self.raw_tags.splitlines()

    @property
    def mentions(self):
        return [Crab.query.filter(Crab.username == user).first() for user in self.raw_mentions.splitlines()]

    @property
    def pretty_date(self):
        return self.timestamp.strftime("%I:%M %p · %b %e, %Y")

    @property
    def replies(self):
        return Molt.query.filter_by(is_reply=True, original_molt=self, deleted=False).all()

    @property
    def true_remolts(self):
        return Molt.query.filter_by(is_remolt=True, original_molt=self, deleted=False).all()

    @property
    def true_likes(self):
        return [like.molt for like in self.likes if like.molt.deleted is False]

    @property
    def pretty_age(self):
        now = datetime.datetime.utcnow()
        delta = now - self.timestamp

        if delta.seconds < 60:
            return f"{round(delta.seconds)}s"
        elif delta.seconds / 60 < 60:
            return f"{round(delta.seconds / 60)}m"
        elif delta.seconds / 60 / 60 < 24:
            return f"{round(delta.seconds / 60 / 60)}h"
        elif self.timestamp.year == now.year:
            return self.timestamp.strftime("%b %e")
        else:
            return self.timestamp.strftime("%b %e, %Y")

    def remolt(self, crab, comment="", **kwargs):
        return crab.molt(comment, is_remolt=True, original_molt=self, **kwargs)

    def reply(self, crab, comment, **kwargs):
        return crab.molt(comment, is_reply=True, original_molt=self, **kwargs)

    def like(self, crab):
        if not Like.query.filter_by(crab=crab, molt=self).all():
            new_like = Like(crab=crab, molt=self)
            db.session.add(new_like)
            db.session.commit()
            return new_like

    def unlike(self, crab):
        old_like = Like.query.filter_by(crab=crab, molt=self).first()
        if old_like is not None:
            db.session.delete(old_like)
            db.session.commit()

    def delete(self):
        self.deleted = True
        db.session.commit()

    @staticmethod
    def label_mentions(content):
        output = content
        match = mention_pattern.search(output)
        if match:
            start, end = match.span()
            output = "".join([output[:start],
                              f'<a href="/user/{match.group(1)}" class="mention zindex-front">',
                              output[start:end],
                              '</a>',
                              Molt.label_mentions(output[end:])])
        return output

    @staticmethod
    def label_crabtags(content):
        output = content
        match = tag_pattern.search(output)
        if match:
            start, end = match.span()
            output = "".join([output[:start],
                              f'<a href="/crabtag/{match.group(1)}" class="crabtag zindex-front">',
                              output[start:end],
                              '</a>',
                              Molt.label_crabtags(output[end:])])
        return output


class Like(db.Model):
    __table_args__ = (db.UniqueConstraint('crab_id', 'molt_id'),)
    id = db.Column(db.Integer, primary_key=True)
    crab_id = db.Column(db.Integer, db.ForeignKey('crab.id'),
                        nullable=False)
    crab = db.relationship('Crab', back_populates='likes')
    molt_id = db.Column(db.Integer, db.ForeignKey('molt.id'),
                        nullable=False)
    molt = db.relationship('Molt', back_populates='likes')

    def __repr__(self):
        return f"<Like from '{self.crab.username}'>"


# HELPER FUNCS #########################################################################################################

def get_current_user():
    return Crab.query.filter_by(id=session.get("current_user")).first()


def validate_username(username):
    return not Crab.query.filter_by(username=username, deleted=False).all()


def validate_email(email):
    return not Crab.query.filter_by(email=email, deleted=False).all()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def common_molt_actions():
    action = request.form.get('user_action')
    molt_id = request.form.get('molt_id')  # Can very well be none. Expect that.

    if action == "change_avatar":
        if 'file' in request.files:
            img = request.files['file']
            print(img.content_length)
            if img.filename == '':
                return redirect(request.path + "?error=No image was selected")
            elif img and allowed_file(img.filename):
                filename = str(uuid.uuid4()) + os.path.splitext(img.filename)[1]
                location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                img.save(location)
                current_user = get_current_user()
                current_user.avatar = "img/user_uploads/" + filename
                db.session.commit()
                return redirect(request.path)
            else:
                return redirect(request.path + "?error=File must be either a jpg, jpeg, or png")
        return redirect(request.path + "?error=There was an error uploading your image")
    elif action == "change_banner":
        if 'file' in request.files:
            img = request.files['file']
            if img.filename == '':
                return redirect(request.path + "?error=No image was selected")
            elif img and allowed_file(img.filename):
                filename = str(uuid.uuid4()) + os.path.splitext(img.filename)[1]
                location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                img.save(location)
                current_user = get_current_user()
                current_user.banner = "img/user_uploads/" + filename
                db.session.commit()
                return redirect(request.path)
            else:
                return redirect(request.path + "?error=File must be either a jpg, jpeg, or png")
        return redirect(request.path + "?error=There was an error uploading your image")
    # Submit new molt
    elif action == "submit_molt":
        if request.form.get('molt_content'):
            img_attachment = None
            # Handle uploaded images
            print(request.files)
            if request.files.get("molt-media"):
                print("found image")
                img = request.files['molt-media']
                if img.filename != '':
                    print("image is not blank")
                    if img and allowed_file(img.filename):
                        print("filename looks good")
                        filename = str(uuid.uuid4()) + os.path.splitext(img.filename)[1]
                        location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        img.save(location)
                        img_attachment = "img/user_uploads/" + filename
            get_current_user().molt(request.form.get('molt_content'), image=img_attachment)
    elif action == "follow":
        target_user = Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().follow(target_user)
        print(target_user.followers)
    elif action == "unfollow":
        target_user = Crab.query.filter_by(id=request.form.get('target_user')).first()
        get_current_user().unfollow(target_user)
    elif action == "submit_reply_molt":
        target_molt = Molt.query.filter_by(id=molt_id).first()
        if request.form.get('molt_content'):
            img_attachment = None
            # Handle uploaded images
            print(request.files)
            if request.files.get("molt-media"):
                print("found image")
                img = request.files['molt-media']
                if img.filename != '':
                    print("image is not blank")
                    if img and allowed_file(img.filename):
                        print("filename looks good")
                        filename = str(uuid.uuid4()) + os.path.splitext(img.filename)[1]
                        location = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        img.save(location)
                        img_attachment = "img/user_uploads/" + filename
            target_molt.reply(get_current_user(), request.form.get('molt_content'), image=img_attachment)
    elif action == "remolt_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()
        target_molt.remolt(get_current_user())

    elif action == "like_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()
        if get_current_user().has_liked(target_molt):
            target_molt.unlike(get_current_user())
        else:
            target_molt.like(get_current_user())

    elif action == "delete_molt" and molt_id is not None:
        target_molt = Molt.query.filter_by(id=molt_id).first()

        if target_molt.author.id == get_current_user().id:
            target_molt.delete()

    elif action == "update_bio":
        target_user = Crab.query.filter_by(id=request.form.get('user_id')).first()
        if target_user == get_current_user():
            disp_name = request.form.get('display_name').strip()
            desc = request.form.get('description').strip()
            current_user = get_current_user()
            current_user.display_name = disp_name
            current_user.bio = desc if desc != "This user is boring and has no bio." else ""
            db.session.commit()

    # PRG pattern
    return redirect(request.url)


# WEBSITE ##############################################################################################################

@app.route("/", methods=("GET", "POST"))
def index():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        following_ids = [crab.id for crab in get_current_user().following] + [get_current_user().id]
        molts = Molt.query.filter(Molt.author_id.in_(following_ids)) \
            .filter_by(deleted=False, is_reply=False).order_by(Molt.timestamp.desc())
        return render_template('timeline.html', current_page="home",
                               molts=molts, current_user=get_current_user())
    else:
        return redirect("/login")


@app.route("/wild", methods=("GET", "POST"))
def wild_west():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        molts = Molt.query.filter_by(deleted=False, is_reply=False).order_by(Molt.timestamp.desc())
        return render_template('wild-west.html', current_page="wild-west",
                               molts=molts, current_user=get_current_user())
    else:
        return redirect("/login")


@app.route("/notifications", methods=("GET", "POST"))
def notifications():
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        molts = Molt.query.filter_by(deleted=False, is_reply=False) \
            .filter(Molt.raw_mentions.contains((get_current_user().username + "\n"))) \
            .order_by(Molt.timestamp.desc())
        return render_template('notifications.html', current_page="notifications",
                               molts=molts, current_user=get_current_user())
    else:
        return redirect("/login")


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email, password = request.form.get("email").strip().lower(), request.form.get("password")
        attempted_user = Crab.query.filter_by(email=email, deleted=False).first()
        if attempted_user is not None:
            if attempted_user.verify_password(password):
                # Login successful
                session["current_user"] = attempted_user.id
                return redirect("/")
        # Login failed
        return redirect("login?failed")
    elif session.get("current_user"):
        return redirect("/")
    else:
        login_failed = request.args.get("failed") is not None
        return render_template("login.html", current_page="login", hide_sidebar=True, login_failed=login_failed)


@app.route("/signup", methods=("GET", "POST"))
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
                            session["current_user"] = Crab.query.filter_by(username=username).first().id
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


@app.route("/logout")
def logout():
    session["current_user"] = None
    return redirect("/login")


@app.route("/signupsuccess")
def signupsuccess():
    recommended_users = Crab.query.filter(Crab.username.in_(("jake",))).all()
    return render_template("signup_success.html", current_user=get_current_user(),
                           recommended_users=recommended_users)


@app.route("/user/<username>", methods=("GET", "POST"))
def user(username):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        error = request.args.get("error")
        this_user = Crab.query.filter_by(username=username, deleted=False).first()
        if this_user is not None:
            molts = Molt.query.filter_by(author=this_user, deleted=False, is_reply=False).order_by(
                Molt.timestamp.desc())
            return render_template('profile.html',
                                   current_page=("own-profile" if this_user == get_current_user() else ""),
                                   molts=molts, current_user=get_current_user(), this_user=this_user, error=error)
        else:
            return render_template('not-found.html', current_user=get_current_user(), error=error, noun="user")
    else:
        return redirect("/login")


@app.route("/user/<username>/follow<tab>", methods=("GET", "POST"))
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


@app.route("/user/<username>/status/<molt_id>", methods=("GET", "POST"))
def molt_page(username, molt_id):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        primary_molt = Molt.query.filter_by(id=molt_id).first()
        if primary_molt:
            replies = Molt.query.filter_by(deleted=False, is_reply=True, original_molt_id=molt_id) \
                .order_by(Molt.timestamp.desc())
            return render_template('molt_page.html', current_page="molt-page", molt=primary_molt,
                                   replies=replies, current_user=get_current_user())
        else:
            return render_template('not-found.html', current_user=get_current_user(), noun="molt")
    else:
        return redirect("/login")


@app.route("/crabtag/<crabtag>", methods=("GET", "POST"))
def crabtags(crabtag):
    # Handle forms and redirect to clear post data on browser
    if request.method == "POST":
        return common_molt_actions()

    # Display page
    elif session.get('current_user') is not None:
        molts = Molt.query.filter(Molt.raw_tags.contains((crabtag + "\n"))).filter_by(deleted=False, is_reply=False) \
            .order_by(Molt.timestamp.desc())
        return render_template('crabtag.html', current_page="crabtag",
                               molts=molts, current_user=get_current_user(), crabtag=crabtag)
    else:
        return redirect("/login")


@app.errorhandler(404)
def error_404(_error_msg):
    return render_template("404.html", current_page="404", current_user=get_current_user())


@app.errorhandler(413)
def file_to_big(e):
    return redirect(request.path + "?error=Image must be smaller than 5 megabytes")


if __name__ == '__main__':
    app.run("0.0.0.0", 80, debug=True)
