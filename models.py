from config import *
import datetime
import extensions
from flask import escape, render_template_string, url_for
import json
from passlib.hash import sha256_crypt
import patterns
import secrets
from typing import Any, Optional
import utils

db = extensions.db

class NotFoundInDatabase(BaseException):
    pass


# This stores unidirectional follower-followee relationships
following_table = db.Table('following',
                           db.Column('id', db.Integer, primary_key=True),
                           db.Column('follower_id', db.Integer, db.ForeignKey('crab.id')),
                           db.Column('following_id', db.Integer, db.ForeignKey('crab.id')))


class Crab(db.Model):
    """ Crab object is the what stores user data. Users are referred to as crabs. Create new with `Crab.create_new`.
    """
    id = db.Column(db.Integer, primary_key=True)

    # User info
    username = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    display_name = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(140), nullable=False,
                    server_default="This user has no description.")
    raw_bio = db.Column(db.String, nullable=False,
                        server_default='{}')
    location = db.Column(db.String, nullable=True)
    verified = db.Column(db.Boolean, nullable=False,
                         default=False)
    avatar = db.Column(db.String(140), nullable=False,
                       server_default="img/avatar.jpg")
    banner = db.Column(db.String(140), nullable=False,
                       server_default="img/banner.png")
    register_time = db.Column(db.DateTime, nullable=False,
                              default=datetime.datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False)
    timezone = db.Column(db.String(8), nullable=False, default="-06.00")
    lastfm = db.Column(db.String, nullable=True)
    banned = db.Column(db.Boolean, nullable=False, default=False)

    # Dynamic relationships
    molts = db.relationship('Molt', back_populates='author')
    following = db.relationship('Crab',
                                secondary=following_table,
                                primaryjoin=id == following_table.c.follower_id,
                                secondaryjoin=id == following_table.c.following_id,
                                backref=db.backref('followers'))
    likes = db.relationship('Like')

    pinned_molt_id = db.Column(db.Integer, nullable=True)
    _preferences = db.Column('preferences', db.String, nullable=False, default='{}')

    def __repr__(self):
        return f"<Crab '@{self.username}'>"

    @property
    def bio(self):
        """ Returns bio JSON as dictionary.
        """
        return json.loads(self.raw_bio)

    @property
    def timedelta(self):
        """ Returns time offset for user's timezone
        """

        return datetime.timedelta(hours=float(self.timezone))

    @property
    def true_likes(self):
        """ Returns all molts the user has liked that are still available.
        """
        return self.get_true_likes()

    @property
    def true_molts(self):
        """ Returns all molts the user has published that are still available.
        """
        return self.get_true_molts()

    @property
    def true_molts_count(self):
        """ Returns count of molts the user has published that are still available.
        """
        return len(self.true_molts)

    @property
    def true_following(self):
        """ Returns this Crab's following without deleted/banned users.
        """
        return self.get_true_following()

    @property
    def true_followers(self):
        """ Returns this Crab's followers without deleted/banned users.
        """
        return self.get_true_followers()

    @property
    def true_following_count(self):
        """ Returns this Crab's following count without deleted/banned users.
        """
        return self.get_true_following(count=True)

    @property
    def true_follower_count(self):
        """ Returns this Crab's follower count without deleted/banned users.
        """
        return self.get_true_followers(count=True)

    @property
    def days_active(self):
        """ Returns number of days since user signed up.
        """
        return (datetime.datetime.utcnow() - self.register_time).days

    @property
    def trophy_count(self):
        """ Returns amount of trophies user has earned.
        """
        return len(self.trophies)

    @property
    def unread_notifications(self):
        """
        Get the amount of unread notifications for this Crab
        :return: len of unread notifs
        """
        return Notification.query.filter_by(recipient=self, read=False).count()

    @property
    def pinned(self):
        """ Return user's currently pinned molt. (May be None)
        """
        return Molt.query.filter_by(id=self.pinned_molt_id).first()

    def get_preference(self, key: str, default: Optional[Any] = None):
        """ Gets key from user's preferences.
        """
        preferences_dict = json.loads(self._preferences)
        return preferences_dict.get(key, default)

    def set_preference(self, key: str, value: Any):
        """ Sets a value in user's preferences.
        """
        preferences_dict = json.loads(self._preferences)
        preferences_dict[key] = value
        self._preferences = json.dumps(preferences_dict)
        db.session.commit()


    def update_bio(self, updates: dict):
        """ Update bio with keys from `new_bio`.
        """
        self.description = updates.get('description') or self.description
        self.location = updates.get('location') or self.location

        valid_keys = ('age', 'emoji', 'jam', 'obsession', 'pronouns', 'quote',
                      'remember')

        # Load bio JSON from string
        new_bio = json.loads(self.raw_bio)
        # Update bio with new values
        new_bio.update(updates)
        # Remove empty fields
        new_bio = {k: v for k, v in new_bio.items()
                   if (str(v.strip()) if v is not None else v)
                   and k in valid_keys}
        # Convert bio back to JSON string and update in database
        self.raw_bio = json.dumps(new_bio)
        db.session.commit()

    def ban(self):
        """ Banish this user from the site.
        """
        if not self.banned:
            self.banned = True
            db.session.commit()

    def unban(self):
        """ Restore a banned user's access to the site.
        """
        if self.banned:
            self.banned = False
            db.session.commit()

    def pin(self, molt):
        """ Set `molt` as user's pinned molt
        """
        self.pinned_molt_id = molt.id
        db.session.commit()

    def unpin(self):
        """ Unpin whatever molt user currently has pinned.
        """
        self.pinned_molt_id = None
        db.session.commit()

    def get_notifications(self, paginated=False, page=1):
        """ Return all valid notifications for user.
        """
        notifs = Notification.query.filter_by(recipient=self).order_by(Notification.timestamp.desc())
        if paginated:
            return notifs.paginate(page, NOTIFS_PER_PAGE, False)
        else:
            return notifs.all()

    def get_true_likes(self, paginated=False, page=1):
        """ Returns all molts the user has liked that are still available.
        """
        likes = Like.query.filter_by(crab=self).filter(Like.molt.has(deleted=False)) \
            .filter(Like.molt.has(Molt.author.has(banned=False, deleted=False))) \
            .join(Molt, Like.molt).order_by(Molt.timestamp.desc())
        if paginated:
            return likes.paginate(page, MOLTS_PER_PAGE, False)
        else:
            return likes.all()

    def get_true_molts(self, paginated=False, page=1):
        """ Returns all molts the user has published that are still available.
        """
        molts = Molt.query.filter_by(author=self).filter_by(deleted=False).order_by(Molt.timestamp.desc())
        if paginated:
            return molts.paginate(page, MOLTS_PER_PAGE, False)
        else:
            return molts.all()

    def get_true_following(self, count=False):
        """ Returns this Crab's following without deleted/banned users.
        """
        following = db.session.query(Crab) \
                .join(following_table, Crab.id==following_table.c.following_id) \
                .filter(following_table.c.follower_id == self.id) \
                .filter(Crab.banned == False, Crab.deleted == False)
        if count:
            return following.count()
        return following.all()

    def get_true_followers(self, count=False):
        """ Returns this Crab's followers without deleted/banned users.
        """
        followers = db.session.query(Crab) \
                .join(following_table, Crab.id==following_table.c.follower_id) \
                .filter(following_table.c.following_id == self.id) \
                .filter(Crab.banned == False, Crab.deleted == False)
        if count:
            return followers.count()
        return followers.all()

    def award(self, title=None, trophy=None):
        """
        Award user trophy. Pass either a trophy object to `trophy`, or the title to `title`. Not both. Not neither.
        :param trophy: Trophy object to award
        :param title: Title of trophy to award
        :return: Trophy case
        """

        if trophy is None and title is None:
            raise TypeError("You must specify one of either trophy object or trophy title.")

        # Use title instead of object
        if trophy is None:
            trophy = Trophy.query.filter_by(title=title).first()

        if trophy is None:
            raise NotFoundInDatabase(f"Trophy with title: '{title}' not found.")

        # Check trophy hasn't already been awarded to user
        if not TrophyCase.query.filter_by(owner=self, trophy=trophy).count():
            new_trophy = TrophyCase(owner=self, trophy=trophy)
            db.session.add(new_trophy)

            # Notify of new award
            self.notify(type="trophy", content=trophy.title)
            db.session.commit()
            return new_trophy

    def follow(self, crab):
        """ Adds user to `crab`'s following.
        """
        if crab not in self.following:
            self.following.append(crab)

            # Create follow notification
            crab.notify(sender=self, type="follow")
            # Check if awards are applicable:
            follower_count = len(crab.followers)
            if follower_count == 1:
                crab.award(title="Social Newbie")
            elif follower_count == 10:
                crab.award(title="Mingler")
            elif follower_count == 100:
                crab.award(title="Life of the Party")
            elif follower_count == 1000:
                crab.award(title="Celebrity")
            if self.verified:
                crab.award(title="I Captivated the Guy")

            db.session.commit()

    def unfollow(self, crab):
        """ Removers user from `crab`'s following.
        """
        if crab in self.following:
            self.following.remove(crab)
            crab.notify(sender=self, type="unfollow")
            db.session.commit()

    def verify_password(self, password):
        """ Returns true if `password` matches user's password.
            :param password: Hash of password to check
        """
        return sha256_crypt.verify(password, self.password)

    def molt(self, content, **kwargs):
        """ Create and publish new Molt.
        """
        kwargs['source'] = kwargs.get('source', 'Crabber Web App')
        new_molt = Molt(author=self, content=content[:MOLT_CHAR_LIMIT], **kwargs)
        db.session.add(new_molt)
        for user in new_molt.mentions:
            user.notify(sender=self, type="mention", molt=new_molt)

        # Check if awards are applicable:
        if len(self.molts) == 1:
            self.award(title="Baby Crab")
        if "420" in new_molt.tags:
            self.award(title="Pineapple Express")
        db.session.commit()
        return new_molt

    def delete(self):
        """ Delete user. (Can be undone).
        """
        self.deleted = True
        db.session.commit()

    def restore(self):
        """ Restore deleted user.
        """
        self.deleted = False
        db.session.commit()

    def is_following(self, crab):
        """ Returns True if user is following `crab`.
        """
        return db.session.query(following_table).filter((following_table.c.follower_id == self.id) &
                                                        (following_table.c.following_id == crab.id))

    def has_liked(self, molt):
        """ Returns True if user has liked `molt`.
        """
        return bool(Like.query.filter_by(molt=molt, crab=self).all())

    def has_remolted(self, molt) -> Optional['Molt']:
        """ Returns the Remolt if user has remolted `molt`, otherwise None.
        """
        molt = Molt.query.filter_by(is_remolt=True, original_molt=molt, author=self, deleted=False).first()
        return molt

    def notify(self, **kwargs):
        """ Create notification for user.
        """
        if kwargs.get("sender") is self:
            return "Declined notification on grounds of sender being recipient."
        if kwargs.get("molt"):
            if Notification.query.filter_by(recipient=self, sender=kwargs.get('sender'),
                                            type=kwargs.get('type'), molt=kwargs.get('molt')).first():
                return "Declined notification on grounds of duplication."
        new_notif = Notification(recipient=self, **kwargs)
        db.session.add(new_notif)
        db.session.commit()
        return new_notif

    @staticmethod
    def create_new(**kwargs):
        """ Create new user. See `Crab.__init__` for arguments.
        """
        kwargs["password"] = Crab.hash_pass(kwargs["password"])
        new_crab = Crab(**kwargs)
        if 'avatar' not in kwargs:
            crabatar_img = utils.make_crabatar(new_crab.username)
            new_crab.avatar = crabatar_img
        db.session.add(new_crab)
        db.session.commit()
        return new_crab

    @staticmethod
    def hash_pass(password):
        """ Returns hash of `password`.
        """
        new_hash = sha256_crypt.encrypt(password)
        return new_hash


class Molt(db.Model):
    """ Molt object is the equivilant of a tweet. Create using `Crab.molt`.
    """
    id = db.Column(db.Integer, primary_key=True)

    # Static info
    author_id = db.Column(db.Integer, db.ForeignKey('crab.id'),
                          nullable=False)
    author = db.relationship('Crab', back_populates='molts')
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False,
                          default=datetime.datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False,
                        default=False)
    raw_mentions = db.Column(db.String, nullable=False,
                             server_default="")
    raw_tags = db.Column(db.String, nullable=False,
                         server_default="")
    image = db.Column(db.String(1024), nullable=True)
    source = db.Column(db.String)

    # Moderation/flagging
    reports = db.Column(db.Integer, nullable=False, default=0)
    approved = db.Column(db.Boolean, nullable=False, default=False)

    # Remolt/reply information
    is_remolt = db.Column(db.Boolean, nullable=False, default=False)
    is_reply = db.Column(db.Boolean, nullable=False, default=False)
    original_molt_id = db.Column(db.Integer, db.ForeignKey('molt.id'))
    original_molt = db.relationship('Molt', remote_side=[id], backref='remolts')

    # Dynamic relationships
    # replies
    # likes
    likes = db.relationship('Like')
    edited = db.Column(db.Boolean, nullable=False, default=False)

    # Custom initialization required to process tags and mentions
    def __init__(self, **kwargs):
        super(Molt, self).__init__(**kwargs)
        for tag in patterns.tag.findall(self.content):
            if self.raw_tags is None:
                self.raw_tags = ""
            self.raw_tags += tag + "\n"
        for user in patterns.mention.findall(self.content):
            if self.raw_mentions is None:
                self.raw_mentions = ""
            self.raw_mentions += user + "\n"

    def __repr__(self):
        return f"<Molt by '@{self.author.username}'>"

    @property
    def editable(self) -> bool:
        """
        Returns true if molt is recent enough to edit.
        """
        return (datetime.datetime.utcnow() - self.timestamp).total_seconds() < MINUTES_EDITABLE * 60

    @property
    def tags(self):
        """ Return list of tags contained withing Molt.
        """
        return self.raw_tags.splitlines()

    @property
    def mentions(self):
        """ Return all mentions contained within Molt.
        """
        if self.raw_mentions:
            return Crab.query.filter(Crab.username.in_(self.raw_mentions.splitlines())).all()
        else:
            return list()

    @property
    def pretty_date(self):
        """ Return date of publish, formatted for display.
        """
        return utils.localize(self.timestamp).strftime("%I:%M %p · %b %e, %Y")

    @property
    def replies(self):
        """ List all currently valid Molts that reply to this Molt.
        """
        return Molt.query.filter_by(is_reply=True, original_molt=self, deleted=False) \
            .filter(Molt.author.has(banned=False, deleted=False)).all()

    @property
    def true_remolts(self):
        """ List all currently valid remolts of Molt.
        """
        return Molt.query.filter_by(is_remolt=True, original_molt=self, deleted=False) \
            .filter(Molt.author.has(banned=False, deleted=False)).all()

    @property
    def true_likes(self):
        """ List all currently valid likes of Molt.
        """
        return Like.query.filter_by(molt=self).filter(Like.crab.has(deleted=False, banned=False)).all()

    @property
    def pretty_age(self):
        """ Property wrapper for `Molt.get_pretty_age`.
        """
        return utils.get_pretty_age(self.timestamp)

    def approve(self):
        """ Approve Molt so it doesn't show in reports page.
        """
        if not self.approved:
            self.approved = True
            db.session.commit()

    def unapprove(self):
        """ Undo the approval of this Molt.
        """
        if self.approved:
            self.approved = False
            db.session.commit()

    def rich_content(self, full_size_media=False):
        """ Return HTML-formatted content of Molt with embeds, media, tags, and etc.
        """
        # Escape/sanitize user submitted content
        new_content = str(escape(self.content))

        # Convert youtube link to embedded iframe
        if patterns.youtube.search(new_content):
            youtube_embed = render_template_string(("{% with video='" +
                                                    patterns.youtube.search(new_content).group(1) +
                                                    "' %}{% include 'youtube.html' %}{% endwith %}"))
            new_content = patterns.youtube.sub('', new_content)
        else:
            youtube_embed = "<!-- no valid youtube links found -->"

        # Convert giphy link to embedded iframe
        if patterns.giphy.search(new_content):
            giphy_embed = render_template_string(("{% with giphy_id='" +
                                                  patterns.giphy.search(new_content).group(1) +
                                                  "' %}{% include 'giphy.html' %}{% endwith %}"),
                                                 full_size_media=full_size_media)
            new_content = patterns.giphy.sub('', new_content)
        else:
            giphy_embed = "<!-- no valid giphy links found -->"

        # Convert giphy link to embedded iframe
        if patterns.ext_img.search(new_content):
            ext_img_embed = render_template_string(("{% with link='" +
                                                    patterns.ext_img.search(new_content).group(1) +
                                                    "' %}{% include 'external_img.html' %}{% endwith %}"),
                                                   full_size_media=full_size_media)
            new_content = patterns.ext_img.sub('', new_content)
        else:
            ext_img_embed = "<!-- no valid external image links found -->"

        # Convert spotify link to embedded iframe
        if patterns.spotify.search(new_content):
            results = patterns.spotify.search(new_content)
            spotify_embed = render_template_string(("{% with link=('" +
                                                    results.group(2) +
                                                    "', '" +
                                                    results.group(3) +
                                                    "') %}{% include 'spotify.html' %}{% endwith %}"))
            new_content = patterns.spotify.sub('', new_content)
        else:
            spotify_embed = "<!-- no valid spotify links found -->"

        new_content = Molt.label_md_links(new_content)
        new_content = Molt.label_links(new_content)

        # Preserve newlines
        new_content = new_content.strip().replace("\n", "<br>")

        # Convert mentions into anchor tags
        new_content = Molt.label_mentions(new_content)
        # Convert crabtags into anchor tags
        new_content = Molt.label_crabtags(new_content)

        return new_content + giphy_embed + ext_img_embed + youtube_embed + spotify_embed

    def dict(self):
        """ Serialize Molt into dictionary.
        """
        return {"molt": {"author": {"id": self.author.id,
                                    "username": self.author.username,
                                    "display_name": self.author.display_name},
                         "content": self.content,
                         "rich_content": self.rich_content(),
                         "likes": [like.id for like in self.true_likes],
                         "remolts": [remolt.id for remolt in self.true_remolts],
                         "image": (BASE_URL + url_for('static', filename=self.image)) if self.image else None,
                         "id": self.id,
                         "timestamp": round(self.timestamp.timestamp())}}

    def get_reply_from(self, crab):
        """ Return first reply Molt from `crab` if it exists.
        """
        reply = Molt.query.filter_by(is_reply=True, original_molt=self, author=crab, deleted=False).order_by(Molt.timestamp).first()
        return reply

    def get_reply_from_following(self, crab):
        """ Return first reply Molt from a crab that `crab` follows if it exists.
        """
        following_ids = [followed.id for followed in crab.true_following]
        following_ids.append(crab.id)
        reply = Molt.query.filter_by(is_reply=True, original_molt=self,
                                     deleted=False) \
                .filter(Molt.author.has(deleted=False, banned=False)) \
                .join(Molt.author).filter(Crab.id.in_(following_ids)) \
                .order_by(Molt.timestamp).first()
        return reply

    def remolt(self, crab, comment="", **kwargs):
        """ Remolt Molt as `crab` with optional `comment`.
        """
        # Already remolted
        if Molt.query.filter_by(is_remolt=True, original_molt=self, author=crab, deleted=False).first():
            return "Remolt declined on grounds of duplication."
        new_remolt = crab.molt(comment, is_remolt=True, original_molt=self, **kwargs)
        self.author.notify(sender=crab, type="remolt", molt=new_remolt)
        return new_remolt

    def reply(self, crab, comment, **kwargs):
        """ Reply to Molt as `crab`.
        """
        new_reply = crab.molt(comment, is_reply=True, original_molt=self, **kwargs)
        self.author.notify(sender=crab, type="reply", molt=new_reply)
        return new_reply

    def report(self):
        """ Increment report counter for Molt.
        """
        self.reports += 1
        db.session.commit()

    def edit(self, new_content):
        """ Change Molt content to `new_content`.
        """
        self.content = new_content
        self.edited = True
        db.session.commit()

    def like(self, crab):
        """ Like Molt as `crab`.
        """
        if not Like.query.filter_by(crab=crab, molt=self).all():
            new_like = Like(crab=crab, molt=self)
            db.session.add(new_like)
            self.author.notify(sender=crab, type="like", molt=self)

            # Check if awards are applicable:
            if self.true_likes == 10:
                self.author.award(title="Dopamine Hit")
            if self.true_likes == 100:
                self.author.award(title="Dopamine Addict")
            if self.true_likes == 1000:
                self.author.award(title="Full on Junkie")
            db.session.commit()
            return new_like

    def unlike(self, crab):
        """ Unlike Molt as `crab`.
        """
        old_like = Like.query.filter_by(crab=crab, molt=self).first()
        if old_like is not None:
            db.session.delete(old_like)
            db.session.commit()

    def delete(self):
        """ Delete molt.
        """
        self.deleted = True
        db.session.commit()

    def restore(self):
        """ Undelete/restore Molt.
        """
        self.deleted = False
        db.session.commit()

    @staticmethod
    def label_links(content, max_len=35):
        """ Replace links with HTML tags.
        """
        output = content
        match = patterns.ext_link.search(output)
        if match:
            start, end = match.span()
            url = match.group(1)
            output = "".join([output[:start],
                              f'<a href="{url}" class="no-onclick mention zindex-front" target="_blank">',
                              url if len(url) <= max_len else url[:max_len - 3] + '...',
                              '</a>',
                              Molt.label_links(output[end:])])
        return output

    @staticmethod
    def label_md_links(content):
        """ Replace markdown links with HTML tags.
        """
        output = content
        match = patterns.ext_md_link.search(output)
        if match:
            start, end = match.span()
            output = "".join([output[:start],
                              f'<a href="{match.group(2)}" class="no-onclick mention zindex-front" target="_blank">',
                              match.group(1),
                              '</a>',
                              Molt.label_md_links(output[end:])])
        return output

    @staticmethod
    def label_mentions(content):
        """ Replace mentions with HTML links to users.
        """
        output = content
        match = patterns.mention.search(output)
        if match:
            start, end = match.span()
            username_str = output[start : end].strip("@ \t\n")
            username = Crab.query.filter_by(deleted=False, banned=False).filter(Crab.username.ilike(username_str)).first()
            if username:
                output = "".join([output[:start],
                                f'<a href="/user/{match.group(1)}" class="no-onclick mention zindex-front">',
                                output[start:end],
                                '</a>',
                                Molt.label_mentions(output[end:])])
            else:
                output = "".join([output[:end],
                                Molt.label_mentions(output[end:])])
        return output

    @staticmethod
    def label_crabtags(content):
        """ Replace crabtags with HTML links to crabtag exploration page.
        """
        output = content
        match = patterns.tag.search(output)
        if match:
            start, end = match.span()
            output = "".join([output[:start],
                              f'<a href="/crabtag/{match.group(1)}" class="no-onclick crabtag zindex-front">',
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
        return f"<Like from '@{self.crab.username}'>"


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Crab receiving notif
    recipient_id = db.Column(db.Integer, db.ForeignKey('crab.id'),
                             nullable=False)
    recipient = db.relationship('Crab', backref=db.backref('notifications', order_by='Notification.timestamp.desc()'),
                                foreign_keys=[recipient_id])
    # Crab responsible for notif
    sender_id = db.Column(db.Integer, db.ForeignKey('crab.id'),
                          nullable=True)
    sender = db.relationship('Crab', foreign_keys=[sender_id])

    timestamp = db.Column(db.DateTime, nullable=False,
                          default=datetime.datetime.utcnow)

    read = db.Column(db.BOOLEAN, nullable=False, default=False)

    # can be: mention, reply, follow, like, remolt, other
    type = db.Column(db.String(32), nullable=False)

    # Molt (optional) (for replies, mentions, likes, etc)
    molt_id = db.Column(db.Integer, db.ForeignKey('molt.id'),
                        nullable=True)
    molt = db.relationship('Molt', foreign_keys=[molt_id])

    # If type is 'other'
    content = db.Column(db.String(140), nullable=True)
    link = db.Column(db.String(140), nullable=True)

    def __repr__(self):
        return f"<Notification | '{self.type}' | for '@{self.recipient.username}'>"

    @property
    def pretty_date(self):
        return utils.localize(self.timestamp).strftime("%I:%M %p · %b %e, %Y")

    @property
    def pretty_age(self):
        return utils.get_pretty_age(self.timestamp)

    def mark_read(self, is_read=True):
        self.read = is_read
        db.session.commit()


# Stores what users have what trophies
class TrophyCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Crab who owns trophy
    owner_id = db.Column(db.Integer, db.ForeignKey('crab.id'),
                         nullable=False)
    owner = db.relationship('Crab', backref=db.backref('trophies', order_by='TrophyCase.timestamp.desc()'),
                            foreign_keys=[owner_id])
    # Trophy in question
    trophy_id = db.Column(db.Integer, db.ForeignKey('trophy.id'),
                          nullable=False)
    trophy = db.relationship('Trophy', foreign_keys=[trophy_id])
    # Time trophy was awarded
    timestamp = db.Column(db.DateTime, nullable=False,
                          default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<TrophyCase | '{self.trophy.title}' | '@{self.owner.username}'>"


# Stores each type of trophy
class Trophy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Short display title
    title = db.Column(db.String(32), nullable=False)
    # Medium description of what it's for
    description = db.Column(db.String(240), nullable=False)
    # Image to display as an icon
    image = db.Column(db.String(240), nullable=False, default="img/default_trophy.png")

    def __repr__(self):
        return f"<Trophy '{self.title}'>"


class DeveloperKey(db.Model):
    __tablename__ = 'developer_keys'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, nullable=False)
    crab_id = db.Column(db.Integer, db.ForeignKey('crab.id'), nullable=False)
    crab = db.relationship('Crab', foreign_keys=[crab_id])
    deleted = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<DeveloperKey (@{crab.username})>'

    def delete(self):
        self.deleted = True
        db.session.commit()

    @classmethod
    def gen_key(cls):
        while True:
            key = secrets.token_hex(16)
            if not cls.query.filter_by(key=key).count():
                return key

    @classmethod
    def create(cls, crab):
        key = cls.gen_key()
        token = cls(crab=crab, key=key)
        db.session.add(token)
        db.session.commit()
        return token


class AccessToken(db.Model):
    __tablename__ = 'access_tokens'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, nullable=False)
    crab_id = db.Column(db.Integer, db.ForeignKey('crab.id'), nullable=False)
    crab = db.relationship('Crab', foreign_keys=[crab_id])
    deleted = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<AccessToken (@{self.crab.username})>'

    def delete(self):
        self.deleted = True
        db.session.commit()

    @classmethod
    def gen_key(cls):
        while True:
            key = secrets.token_hex(16)
            if not cls.query.filter_by(key=key).count():
                return key

    @classmethod
    def create(cls, crab):
        key = cls.gen_key()
        token = cls(crab=crab, key=key)
        db.session.add(token)
        db.session.commit()
        return token
