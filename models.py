import config
import datetime
import email.utils
import extensions
from flask import render_template, url_for
from flask_sqlalchemy import BaseQuery
import json
from passlib.hash import sha256_crypt
import patterns
import secrets
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import aliased
from sqlalchemy.sql import expression
from sqlalchemy.sql.expression import false, true, null
from typing import Any, Iterable, List, Optional, Tuple, Union
import utils

db = extensions.db

# This links Molts to Crabtags in a many-to-many relationship
crabtag_table = db.Table(
    "crabtag_links",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("molt_id", db.Integer, db.ForeignKey("molt.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("crabtag.id")),
)

# This stores unidirectional follower-followee relationships
following_table = db.Table(
    "following",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("follower_id", db.Integer, db.ForeignKey("crab.id")),
    db.Column("following_id", db.Integer, db.ForeignKey("crab.id")),
)

blocking_table = db.Table(
    "blocking",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("blocker_id", db.Integer, db.ForeignKey("crab.id")),
    db.Column("blocked_id", db.Integer, db.ForeignKey("crab.id")),
)


class NotFoundInDatabase(BaseException):
    """Raised when requested item was not found in the database."""

    pass


class Crab(db.Model):
    """A Crab is a user.

    Create new with `Crab.create_new`.
    """

    id = db.Column(db.Integer, primary_key=True)

    # User info
    username = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    display_name = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    description = db.Column(
        db.String(1024), nullable=False, server_default="This user has no description."
    )
    raw_bio = db.Column(db.String(2048), nullable=False, server_default="{}")
    location = db.Column(db.String(256), nullable=True)
    website = db.Column(db.String(1024), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    avatar = db.Column(
        db.String(140),
        nullable=False,
        server_default="https://cdn.crabber.net/img/avatar.jpg",
    )
    banner = db.Column(
        db.String(140),
        nullable=False,
        server_default="https://cdn.crabber.net/img/banner.png",
    )
    register_time = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    referrer_id = db.Column(db.Integer, db.ForeignKey("crab.id"))
    referrer = db.relationship("Crab", remote_side=[id], backref="referrals")

    deleted = db.Column(db.Boolean, nullable=False, default=False)
    timezone = db.Column(db.String(8), nullable=False, default="-06.00")
    lastfm = db.Column(db.String(128), nullable=True)
    banned = db.Column(db.Boolean, nullable=False, default=False)
    _password_reset_token = db.Column("password_reset_token", db.String(128))

    # Content visibility
    nsfw = db.Column(db.Boolean, nullable=False, default=False)
    show_nsfw = db.Column(db.Boolean, nullable=False, default=False)
    show_nsfw_thumbnails = db.Column(db.Boolean, nullable=False, default=False)
    _muted_words = db.Column(
        "muted_words", db.String(4096), nullable=False, server_default=""
    )

    # Dynamic relationships
    _molts = db.relationship("Molt", back_populates="author")
    _following = db.relationship(
        "Crab",
        secondary=following_table,
        primaryjoin=id == following_table.c.follower_id,
        secondaryjoin=id == following_table.c.following_id,
        backref=db.backref("_followers"),
    )
    _blocked = db.relationship(
        "Crab",
        secondary=blocking_table,
        primaryjoin=id == blocking_table.c.blocker_id,
        secondaryjoin=id == blocking_table.c.blocked_id,
        backref=db.backref("_blockers"),
    )
    _likes = db.relationship("Like")
    _bookmarks = db.relationship("Bookmark")

    pinned_molt_id = db.Column(db.Integer, nullable=True)
    _preferences = db.Column(
        "preferences", db.String(4096), nullable=False, default="{}"
    )

    # Used for efficient queries in templates
    column_dict = dict(
        id=id,
        avatar=avatar,
        username=username,
        display_name=display_name,
        verified=verified,
        deleted=deleted,
        banned=banned,
        description=description,
        raw_bio=raw_bio,
        location=location,
        website=website,
        banner=banner,
        register_time=register_time,
        timezone=timezone,
        lastfm=lastfm,
    )

    def __repr__(self):
        return f"<Crab '@{self.username}'>"

    @property
    def register_timestamp(self):
        """Returns integer timestamp of user's registration."""
        return int(self.register_time.timestamp())

    @property
    def rich_description(self):
        """Returns user's description parsed into rich HTML."""
        return utils.parse_rich_content(
            self.description, include_media=False, preserve_whitespace=False
        )

    @property
    def bio(self):
        """Returns bio JSON as dictionary."""
        return json.loads(self.raw_bio)

    @property
    def timedelta(self):
        """Returns time offset for user's timezone."""
        return datetime.timedelta(hours=float(self.timezone))

    @property
    def is_admin(self) -> bool:
        """Returns whether the user is a website admin."""
        return self.username.lower() in config.ADMINS

    @property
    def is_moderator(self) -> bool:
        """Returns whether the user is a website moderator."""
        return self.username.lower() in [*config.MODERATORS, *config.ADMINS]

    @property
    def muted_words(self) -> List[str]:
        """Returns a list of the words this user has muted."""
        return filter(lambda s: len(s), self._muted_words.split(","))

    @property
    def muted_words_string(self) -> List[str]:
        """Returns a comma-separated list of the words this user has muted."""
        return ", ".join(self.muted_words)

    @property
    def bookmarks(self):
        """Returns all bookmarks the user has where the molt is still available."""
        return self.query_bookmarks().all()

    @property
    def bookmark_count(self):
        """Returns number of molts the user has bookmarked that are still available."""
        return self.query_bookmarks().count()

    @property
    def likes(self):
        """Returns all likes the user has where the molt is still available."""
        return self.query_likes().all()

    @property
    def like_count(self):
        """Returns number of molts the user has liked that are still available."""
        return self.query_likes().count()

    @property
    def molts(self):
        """Returns all molts the user has published that are still available."""
        return self.query_molts().all()

    @property
    def molt_count(self):
        """Returns number of molts the user has published that are still available."""
        return self.query_molts().count()

    @property
    def replies(self):
        """Returns all replies the user has published that are still available."""
        return self.query_replies().all()

    @property
    def reply_count(self):
        """Returns number of replies the user has published that are still available."""
        return self.query_replies().count()

    @property
    def blocked(self) -> List["Crab"]:
        """Returns this Crab's blocked Crabs without deleted/banned users."""
        return self.query_blocked().all()

    @property
    def blockers(self) -> List["Crab"]:
        """Returns Crabs that have blocked this Crab without deleted/banned users."""
        return self.query_blockers().all()

    @property
    def following(self) -> List["Crab"]:
        """Returns this Crab's following without deleted/banned users."""
        return self.query_following().all()

    @property
    def followers(self) -> List["Crab"]:
        """Returns this Crab's followers without deleted/banned users."""
        return self.query_followers().all()

    @property
    def following_count(self):
        """Returns this Crab's following count without deleted/banned users."""
        return self.query_following().count()

    @property
    def follower_count(self):
        """Returns this Crab's follower count without deleted/banned users."""
        return self.query_followers().count()

    @property
    def days_active(self):
        """Returns number of days since user signed up."""
        return (datetime.datetime.utcnow() - self.register_time).days

    @property
    def trophy_count(self):
        """Returns amount of trophies user has earned."""
        return TrophyCase.query.filter_by(owner_id=self.id).count()

    @property
    def unread_notifications(self):
        """Get the amount of unread notifications for this Crab."""
        return Notification.query_all().filter_by(recipient=self, read=False).count()

    @property
    def pinned(self) -> Optional["Molt"]:
        """Return user's currently pinned molt."""
        return Molt.query.filter_by(id=self.pinned_molt_id).first()

    @property
    def referral_code(self) -> "ReferralCode":
        """Return user's referral code."""
        return ReferralCode.get(self)

    def generate_password_reset_token(self):
        """Generates and returns a new password reset token."""
        new_token = dict(
            token=secrets.token_hex(32),
            timestamp=int(datetime.datetime.utcnow().timestamp()),
        )
        self._password_reset_token = json.dumps(new_token)
        db.session.commit()
        return new_token["token"]

    def verify_password_reset_token(self, token: str) -> bool:
        """Verifies a given password reset token is still valid."""
        if token and self._password_reset_token:
            # Load from JSON
            real_token = json.loads(self._password_reset_token)
            # Check if expired
            token_time = datetime.datetime.fromtimestamp(real_token["timestamp"])
            elapsed_minutes = (
                abs((token_time - datetime.datetime.utcnow()).total_seconds()) / 60
            )
            if elapsed_minutes < 10 and token == real_token["token"]:
                return True
        return False

    def clear_password_reset_token(self):
        """Removes any existing password reset tokens."""
        self._password_reset_token = None
        db.session.commit()

    def bookmark(self, molt):
        """Add `molt` to bookmarks."""
        if not self.has_bookmarked(molt):
            new_bookmark = Bookmark(crab=self, molt=molt)
            db.session.add(new_bookmark)
            db.session.commit()

    def unbookmark(self, molt):
        """Remove `molt` from bookmarks."""
        bookmark = self.has_bookmarked(molt)
        if bookmark:
            self.bookmarks.remove(bookmark)
            db.session.delete(bookmark)
            db.session.commit()

    def get_mutuals_for(self, crab: "Crab"):
        """Returns a list of people you follow who also follow `crab`."""
        self_following = (
            db.session.query(Crab.id)
            .join(following_table, Crab.id == following_table.c.following_id)
            .filter(following_table.c.follower_id == self.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
        )
        crab_followers = (
            db.session.query(Crab)
            .join(following_table, Crab.id == following_table.c.follower_id)
            .filter(following_table.c.following_id == crab.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
        )
        mutuals = crab_followers.filter(Crab.id.in_(self_following))
        return mutuals.all()

    def get_preference(self, key: str, default: Optional[Any] = None):
        """Gets key from user's preferences."""
        preferences_dict = json.loads(self._preferences)
        return preferences_dict.get(key, default)

    def set_preference(self, key: str, value: Any):
        """Sets a value in user's preferences."""
        preferences_dict = json.loads(self._preferences)
        preferences_dict[key] = value
        self._preferences = json.dumps(preferences_dict)
        db.session.commit()

    def get_recommended_crabs(self, limit=3):
        """Returns recommended crabs based on this user's following."""
        following_ids = (
            db.session.query(Crab.id)
            .join(following_table, Crab.id == following_table.c.following_id)
            .filter(following_table.c.follower_id == self.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
        )
        if following_ids.count():
            recommended = (
                db.session.query(Crab)
                .join(following_table, Crab.id == following_table.c.following_id)
                .filter(following_table.c.follower_id.in_(following_ids))
                .filter(following_table.c.following_id.notin_(following_ids))
                .group_by(Crab.id)
                .filter(Crab.banned == false(), Crab.deleted == false())
                .filter(Crab.id != self.id)
                .order_by(func.count(Crab.id).desc())
            )
        else:
            recommended = (
                Crab.query_most_popular().filter(Crab.id != self.id).with_entities(Crab)
            )
        recommended = self.filter_user_query_by_not_blocked(recommended)

        return recommended.limit(limit).all()

    def update_bio(self, updates: dict):
        """Update bio with keys from `new_bio`."""
        self.description = updates.get("description") or self.description
        self.location = updates.get("location") or self.location
        self.website = updates.get("website") or self.website

        valid_keys = (
            "age",
            "emoji",
            "jam",
            "obsession",
            "pronouns",
            "quote",
            "remember",
        )

        # Load bio JSON from string
        new_bio = json.loads(self.raw_bio)
        # Update bio with new values
        new_bio.update(updates)
        # Remove empty fields
        new_bio = {
            k: v
            for k, v in new_bio.items()
            if (str(v.strip()) if v is not None else v) and k in valid_keys
        }
        # Convert bio back to JSON string and update in database
        self.raw_bio = json.dumps(new_bio)
        db.session.commit()

    def verify(self):
        """Verify this user."""
        self.verified = True

        for crab in self.following:
            crab.award(title="I Captivated the Guy")

        db.session.commit()

    def unverify(self):
        """Revoke this user's verification."""
        self.verified = False

        db.session.commit()

    def clear_username(self):
        """Change this user's username to a randomly generated one."""
        new_username = f"crab{utils.hexID(8)}"
        while not utils.validate_username(new_username):
            new_username = f"crab{utils.hexID(8)}"
        self.username = new_username
        db.session.commit()

    def clear_display_name(self):
        """Change this user's display name to a generic one."""
        self.display_name = "Unnamed Crab"
        db.session.commit()

    def clear_description(self, description="This user has no description."):
        """Change this user's description to a generic one."""
        self.description = description
        db.session.commit()

    def clear_avatar(self):
        """Change this user's avatar to a generic one."""
        self.avatar = utils.make_crabatar(self.username)
        db.session.commit()

    def clear_banner(self):
        """Change this user's banner to a generic one."""
        self.banner = "https://cdn.crabber.net/img/banner.png"
        db.session.commit()

    def ban(self, reason=None):
        """Banish this user from the site."""
        if not self.banned:
            self.banned = True
            db.session.commit()

            if config.MAIL_ENABLED:
                # Send ban notification email
                body = render_template(
                    "user-banned-email.html", crab=self, ban_reason=reason
                )
                if config.is_debug_server:
                    print(f"\nEMAIL BODY:\n{body}\n")
                else:
                    extensions.mail.send_mail(
                        self.email, subject="Your account has been banned", body=body
                    )

    def unban(self):
        """Restore a banned user's access to the site."""
        if self.banned:
            self.banned = False
            db.session.commit()

            if config.MAIL_ENABLED:
                # Send ban notification email
                body = render_template("user-unbanned-email.html", crab=self)
                if config.is_debug_server:
                    print(f"\nEMAIL BODY:\n{body}\n")
                else:
                    extensions.mail.send_mail(
                        self.email, subject="Your account has been restored", body=body
                    )

    def pin(self, molt):
        """Set `molt` as user's pinned molt."""
        self.pinned_molt_id = molt.id
        db.session.commit()

    def unpin(self):
        """Unpin whatever molt user currently has pinned."""
        self.pinned_molt_id = None
        db.session.commit()

    def get_notifications(self, paginated=False, page=1):
        """Return all valid notifications for user."""
        blocker_ids = db.session.query(blocking_table.c.blocker_id).filter(
            blocking_table.c.blocked_id == self.id
        )
        blocked_ids = db.session.query(blocking_table.c.blocked_id).filter(
            blocking_table.c.blocker_id == self.id
        )

        block_ids = blocked_ids.union(blocker_ids)

        notifs = (
            Notification.query_all()
            .filter(
                db.or_(
                    Notification.sender_id == null(),
                    Notification.sender_id.notin_(block_ids),
                )
            )
            .filter_by(recipient=self)
        )
        likes = (
            notifs.with_entities(
                Notification,
                func.count(Notification.id),
                func.max(Notification.timestamp),
            )
            .filter_by(type="like")
            .group_by(Notification.molt_id)
        )
        remolts = (
            notifs.with_entities(
                Notification,
                func.count(Notification.id),
                func.max(Notification.timestamp),
            )
            .filter_by(type="remolt")
            .join(Molt, Molt.id == Notification.molt_id)
            .group_by(Molt.original_molt_id)
        )
        other = notifs.with_entities(
            Notification,
            expression.literal(1),
            Notification.timestamp.label("timestamp"),
        ).filter(
            Notification.type.in_(
                ("other", "warning", "trophy", "mention", "quote", "reply", "follow")
            )
        )
        notifs = other.union(likes, remolts).order_by(Notification.timestamp.desc())
        if paginated:
            return notifs.paginate(page, config.NOTIFS_PER_PAGE, False)
        else:
            return notifs.all()

    def read_notifications(self):
        """Mark all of this user's notifications as read."""
        notifs = (
            Notification.query_all().filter_by(recipient=self).filter_by(read=False)
        )
        for notif in notifs:
            notif.read = True
        db.session.commit()

    def award(self, title=None, trophy=None):
        """Award user trophy by object or by title."""
        if trophy is None and title is None:
            raise TypeError(
                "You must specify one of either trophy object or trophy title."
            )

        # Query trophy by title
        if trophy is None:
            trophy_query = Trophy.query.filter(Trophy.title.ilike(title))
            if trophy_query.count() == 0:
                raise NotFoundInDatabase(f"Trophy with title: '{title}' not found.")
            trophy = trophy_query.first()

        # Check trophy hasn't already been awarded to user
        if not TrophyCase.query.filter_by(owner=self, trophy=trophy).count():
            new_trophy = TrophyCase(owner=self, trophy=trophy)
            db.session.add(new_trophy)

            # Notify of new award
            self.notify(type="trophy", content=trophy.title)
            db.session.commit()
            return new_trophy

    def block(self, crab):
        """Add `crab` to this Crab's block users."""
        if crab not in self._blocked and crab is not self:
            self.unfollow(crab)
            crab.unfollow(self)
            self._blocked.append(crab)
            db.session.commit()

    def unblock(self, crab):
        """Removes `crab` from this Crab's block users."""
        if crab in self._blocked and crab is not self:
            self._blocked.remove(crab)
            db.session.commit()

    def follow(self, crab):
        """Adds user to `crab`'s following."""
        if crab not in self._following and crab is not self:
            self._following.append(crab)

            # Create follow notification
            crab.notify(sender=self, type="follow")

            # Award applicable trophies
            self.check_follower_count_trophies()
            crab.check_follower_count_trophies()
            if self.verified:
                crab.award(title="I Captivated the Guy")

            db.session.commit()

    def unfollow(self, crab):
        """Removes user from `crab`'s following."""
        if crab in self._following and crab is not self:
            self._following.remove(crab)
            db.session.commit()

    def verify_password(self, password):
        """Returns true if `password` matches user's password."""
        return sha256_crypt.verify(password, self.password)

    def molt(self, content, **kwargs):
        """Create and publish new Molt."""
        kwargs["nsfw"] = kwargs.get("nsfw", self.nsfw)
        new_molt = Molt.create(author=self, content=content, **kwargs)

        # Award molt count trophies
        molt_count = self.molt_count
        if molt_count >= 10_000:
            self.award(title="Please Stop")
        if molt_count >= 1_000:
            self.award(title="Loudmouth")
        if molt_count == 1:
            self.award(title="Baby Crab")

        return new_molt

    def delete(self):
        """Delete user. (Can be undone)."""
        self.deleted = True
        db.session.commit()

    def restore(self):
        """Restore deleted user."""
        self.deleted = False
        db.session.commit()

    def is_blocking(self, crab):
        """Returns True if user has blocked `crab`."""
        return (
            db.session.query(blocking_table)
            .filter(
                (blocking_table.c.blocker_id == self.id)
                & (blocking_table.c.blocked_id == crab.id)
            )
            .count()
        )

    def is_blocked_by(self, crab):
        """Returns True if user has been blocked by `crab`."""
        return (
            db.session.query(blocking_table)
            .filter(
                (blocking_table.c.blocked_id == self.id)
                & (blocking_table.c.blocker_id == crab.id)
            )
            .count()
        )

    def is_following(self, crab):
        """Returns True if user is following `crab`."""
        return (
            db.session.query(following_table)
            .filter(
                (following_table.c.follower_id == self.id)
                & (following_table.c.following_id == crab.id)
            )
            .count()
        )

    def has_bookmarked(self, molt) -> Optional["Bookmark"]:
        """Returns bookmark if user has bookmarked `molt`."""
        return Bookmark.query.filter_by(molt_id=molt.id, crab_id=self.id).first()

    def has_liked(self, molt) -> Optional["Like"]:
        """Returns like if user has liked `molt`."""
        return Like.query.filter_by(molt_id=molt.id, crab_id=self.id).first()

    def has_remolted(self, molt) -> Optional["Molt"]:
        """Returns the Remolt if user has remolted `molt`, otherwise None."""
        molt = Molt.query.filter_by(
            is_remolt=True, original_molt_id=molt.id, author_id=self.id, deleted=False
        ).first()
        return molt

    def notify(self, **kwargs):
        """Create notification for user."""
        is_duplicate = False
        if kwargs.get("sender") is not self:
            # Don't notify if either user is blocked
            sender = kwargs.get("sender")
            if sender is not None:
                if self.is_blocked_by(sender) or self.is_blocking(sender):
                    return None

            # Check for molt duplicates
            molt = kwargs.get("molt")
            if molt:
                duplicate_notification = Notification.query.filter_by(
                    recipient=self,
                    sender=kwargs.get("sender"),
                    type=kwargs.get("type"),
                    molt=molt,
                )
                if duplicate_notification.count():
                    is_duplicate = True

            # Check for notification spamming
            if kwargs.get("type") in ("follow", "unfollow"):
                now = datetime.datetime.utcnow()
                yesterday = now - datetime.timedelta(days=1)
                duplicate_notification = (
                    Notification.query_all()
                    .filter_by(
                        recipient=self,
                        sender=kwargs.get("sender"),
                        type=kwargs.get("type"),
                        molt=kwargs.get("molt"),
                    )
                    .filter(Notification.timestamp > yesterday)
                )
                if duplicate_notification.count():
                    is_duplicate = True

            if not is_duplicate:
                new_notif = Notification(recipient=self, **kwargs)
                db.session.add(new_notif)
                db.session.commit()
                return new_notif

    # Query methods

    def query_blocked(self) -> BaseQuery:
        """Returns this Crab's blocked Crabs without deleted/banned users."""
        blocked = (
            db.session.query(Crab)
            .join(blocking_table, Crab.id == blocking_table.c.blocked_id)
            .filter(blocking_table.c.blocker_id == self.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
            .order_by(Crab.username)
        )
        return blocked

    def query_blockers(self) -> BaseQuery:
        """Returns Crabs that have blocked this Crab without deleted/banned users."""
        blockers = (
            db.session.query(Crab)
            .join(blocking_table, Crab.id == blocking_table.c.blocker_id)
            .filter(blocking_table.c.blocked_id == self.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
            .order_by(Crab.username)
        )
        return blockers

    def query_following(self) -> BaseQuery:
        """Returns this Crab's following without deleted/banned users."""
        following = (
            db.session.query(Crab)
            .join(following_table, Crab.id == following_table.c.following_id)
            .filter(following_table.c.follower_id == self.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
        )
        return following

    def query_followers(self) -> BaseQuery:
        """Returns this Crab's followers without deleted/banned users."""
        followers = (
            db.session.query(Crab)
            .join(following_table, Crab.id == following_table.c.follower_id)
            .filter(following_table.c.following_id == self.id)
            .filter(Crab.banned == false(), Crab.deleted == false())
        )
        return followers

    def query_bookmarks(self) -> BaseQuery:
        """Returns all bookmarks the user has where the molt is still available."""
        bookmarks = (
            Bookmark.query.filter_by(crab=self)
            .filter(Bookmark.molt.has(deleted=False))
            .filter(Bookmark.molt.has(Molt.author.has(banned=False, deleted=False)))
            .join(Molt, Bookmark.molt)
            .order_by(Bookmark.timestamp.desc())
        )
        return bookmarks

    def query_likes(self) -> BaseQuery:
        """Returns all likes the user has where the molt is still available."""
        likes = (
            Like.query.filter_by(crab=self)
            .filter(Like.molt.has(deleted=False))
            .filter(Like.molt.has(Molt.author.has(banned=False, deleted=False)))
            .join(Molt, Like.molt)
            .order_by(Molt.timestamp.desc())
        )
        return likes

    def query_molts(self) -> BaseQuery:
        """Returns all molts the user has published that are still available."""
        molts = Molt.query.filter_by(author=self, deleted=False).order_by(
            Molt.timestamp.desc()
        )
        return Molt.filter_query_by_available(molts)

    def query_replies(self) -> BaseQuery:
        """Returns all replies the user has published that are still available."""
        molts = (
            self.query_molts()
            .filter_by(is_reply=True)
            .filter(Molt.original_molt.has(deleted=False))
        )
        return molts

    def query_timeline(self) -> BaseQuery:
        """Retrieves the molts in this user's timeline."""
        following_ids = db.session.query(following_table.c.following_id).filter(
            following_table.c.follower_id == self.id
        )
        molts = (
            Molt.query_all(
                include_replies=False, include_quotes=True, include_remolts=True
            )
            .filter(
                db.or_(Molt.author_id.in_(following_ids), Molt.author_id == self.id)
            )
            .order_by(Molt.timestamp.desc())
        )
        molts = self.filter_molt_query(molts)
        return molts

    def change_password(self, password: str):
        """Updates this user's password hash."""
        self.password = self.hash_pass(password)
        db.session.commit()

    def filter_molt_query(self, query: BaseQuery) -> BaseQuery:
        """Filters a Molt query for all user blocks and preferences."""
        query = self.filter_molt_query_by_not_blocked(query)
        if not self.show_nsfw:
            query = self.filter_molt_query_by_not_nsfw(query)
        query = self.filter_molt_query_by_muted_words(query)
        return query

    def filter_molt_query_by_muted_words(self, query: BaseQuery) -> BaseQuery:
        """Filters Molts containing muted words out of a query."""
        for muted_word in self.muted_words:
            query = query.filter(
                db.or_(
                    Molt.author_id == self.id,
                    db.not_(Molt.content.ilike(f"%{muted_word}%")),
                )
            )
        return query

    def filter_molt_query_by_not_nsfw(self, query: BaseQuery) -> BaseQuery:
        """Filters NSFW Molts out of a query."""
        query = query.filter(
            db.or_(Molt.nsfw == false(), Molt.author_id == self.id)
        ).filter(
            db.or_(
                Molt.original_molt == null(),
                Molt.original_molt.has(nsfw=False),
                Molt.original_molt.has(author_id=self.id),
                Molt.author_id == self.id,
            )
        )
        return query

    def filter_molt_query_by_not_blocked(self, query: BaseQuery) -> BaseQuery:
        """Filters a Molt query by authors who are not blocked."""
        blocked_ids = db.session.query(blocking_table.c.blocked_id).filter(
            blocking_table.c.blocker_id == self.id
        )
        blocker_ids = db.session.query(blocking_table.c.blocker_id).filter(
            blocking_table.c.blocked_id == self.id
        )
        original_molt = aliased(Molt)
        query = (
            query.filter(Molt.author_id.notin_(blocker_ids))
            .filter(Molt.author_id.notin_(blocked_ids))
            .outerjoin(original_molt, original_molt.id == Molt.original_molt_id)
            .filter(
                db.or_(
                    Molt.original_molt == null(),
                    db.and_(
                        original_molt.author_id.notin_(blocked_ids),
                        original_molt.author_id.notin_(blocker_ids),
                    ),
                )
            )
        )
        return query

    def check_customization_trophies(self):
        """Awards applicable bio customization trophies."""
        if all(
            (
                self.description != "This user has no description.",
                "user_uploads" in self.banner,
                "user_uploads" in self.avatar,
                self.raw_bio != "{}",
            )
        ):
            self.award("I Want it That Way")

    def check_follower_count_trophies(self):
        """Awards necessary follower/following trophies."""
        following_count = self.following_count
        follower_count = self.follower_count
        if follower_count == 1:
            self.award(title="Social Newbie")
        elif follower_count == 10:
            self.award(title="Mingler")
        elif follower_count == 100:
            self.award(title="Life of the Party")
        elif follower_count == 1_000:
            self.award(title="Celebrity")

        if following_count >= 20:
            follower_ratio = follower_count / following_count
            if follower_ratio >= 20:
                self.award(title="20/20")
            if follower_ratio >= 100:
                self.award(title="The Golden Ratio")

    def filter_user_query_by_not_blocked(self, query: BaseQuery) -> BaseQuery:
        """Filters a Crab query by users who are not blocked."""
        blocker_ids = [crab.id for crab in self.blockers]
        blocked_ids = [crab.id for crab in self.blocked]
        query = query.filter(Crab.id.notin_(blocker_ids)).filter(
            Crab.id.notin_(blocked_ids)
        )
        return query

    @staticmethod
    def order_query_by_followers(query: BaseQuery) -> BaseQuery:
        """Orders a Crab query by number of followers (descending)."""
        # Ordering by None overrides previous order_by
        query = (
            query.outerjoin(following_table, following_table.c.following_id == Crab.id)
            .group_by(following_table.c.following_id)
            .order_by(None)
            .order_by(func.count(following_table.c.following_id).desc())
        )
        return query

    @staticmethod
    def query_all() -> BaseQuery:
        """Queries all valid crabs."""
        return Crab.query.filter_by(deleted=False, banned=False)

    @staticmethod
    def query_most_popular() -> BaseQuery:
        """Queries most followed crabs."""
        followers = (
            db.session.query(
                following_table.c.following_id,
                func.count(following_table.c.following_id).label("count"),
            )
            .join(Crab, Crab.id == following_table.c.follower_id)
            .filter(Crab.deleted == false(), Crab.banned == false())
            .group_by(following_table.c.following_id)
            .subquery()
        )

        crabs = (
            db.session.query(Crab, followers.c.count)
            .join(followers, followers.c.following_id == Crab.id)
            .filter(Crab.deleted == false(), Crab.banned == false())
            .order_by(db.desc("count"))
        )
        return crabs

    @staticmethod
    def query_most_referrals() -> BaseQuery:
        """Queries crabs with the most referrals."""
        crabs = (
            db.session.query(Crab, ReferralCode.uses)
            .join(ReferralCode, Crab.id == ReferralCode.crab_id)
            .filter(Crab.deleted == false(), Crab.banned == false())
            .filter(ReferralCode.disabled == false())
            .order_by(ReferralCode.uses.desc())
        )
        return crabs

    @staticmethod
    def get_by_ID(id: int, include_invalidated: bool = False) -> Optional["Crab"]:
        """Retrieves crab by ID."""
        if id:
            crab = Crab.query.filter_by(id=id)
            if not include_invalidated:
                crab = crab.filter_by(deleted=False, banned=False)
            return crab.first()

    @staticmethod
    def get_by_email(email: str, include_invalidated: bool = False) -> Optional["Crab"]:
        """Retrieves crab by email."""
        if email:
            crab = Crab.query.filter(Crab.email.ilike(email))
            if not include_invalidated:
                crab = crab.filter_by(deleted=False, banned=False)
            return crab.first()

    @staticmethod
    def get_by_username(
        username: str, include_invalidated: bool = False
    ) -> Optional["Crab"]:
        """Retrieves crab by username."""
        if username:
            crab = Crab.query.filter(Crab.username.ilike(username))
            if not include_invalidated:
                crab = crab.filter_by(deleted=False, banned=False)
            return crab.first()

    @staticmethod
    def search(query: str) -> BaseQuery:
        """Searches availabled crabs."""
        results = Crab.query.filter_by(deleted=False, banned=False).filter(
            db.or_(
                Crab.display_name.contains(query, autoescape=True),
                Crab.username.contains(query, autoescape=True),
            )
        )
        return Crab.order_query_by_followers(results)

    @staticmethod
    def hash_pass(password):
        """Returns hash of `password`."""
        new_hash = sha256_crypt.encrypt(password)
        return new_hash

    @classmethod
    def create_new(cls, **kwargs):
        """Create new user. See `Crab.__init__` for arguments."""
        kwargs["password"] = cls.hash_pass(kwargs["password"])
        kwargs["banner"] = kwargs.get(
            "banner", "https://cdn.crabber.net/img/banner.png"
        )
        new_crab = cls(**kwargs)
        if "avatar" not in kwargs:
            crabatar_img = utils.make_crabatar(new_crab.username)
            new_crab.avatar = crabatar_img
        db.session.add(new_crab)
        db.session.commit()
        return new_crab


class Molt(db.Model):
    """Molt object is the equivilant of a tweet. Create using `Crab.molt`."""

    id = db.Column(db.Integer, primary_key=True)

    # Static info
    author_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    author = db.relationship("Crab", back_populates="_molts")
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    deleted = db.Column(db.Boolean, nullable=False, default=False)
    raw_mentions = db.Column(db.String(1024), nullable=False, server_default="")
    raw_tags = db.Column(db.String(1024), nullable=False, server_default="")
    image = db.Column(db.String(1024), nullable=True)
    source = db.Column(db.String(1024))

    card_id = db.Column(db.Integer, db.ForeignKey("card.id"))
    card = db.relationship("Card")

    # Content visibility
    nsfw = db.Column(db.Boolean, nullable=False, default=False)

    # Tag links
    tags = db.relationship("Crabtag", secondary=crabtag_table, back_populates="molts")

    # Analytical data
    browser = db.Column(db.String(512))
    platform = db.Column(db.String(512))
    address = db.Column(db.String(512))

    # Moderation/flagging
    reports = db.Column(db.Integer, nullable=False, default=0)
    approved = db.Column(db.Boolean, nullable=False, default=False)

    # Remolt/reply information
    is_remolt = db.Column(db.Boolean, nullable=False, default=False)
    is_reply = db.Column(db.Boolean, nullable=False, default=False)
    is_quote = db.Column(db.Boolean, nullable=False, default=False)
    original_molt_id = db.Column(db.Integer, db.ForeignKey("molt.id"))
    original_molt = db.relationship("Molt", remote_side=[id], backref="_remolts")

    # Dynamic relationships
    _likes = db.relationship("Like")
    edited = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        """__repr__."""
        return f"<Molt by '@{self.author.username}'>"

    @property
    def editable(self) -> bool:
        """Returns true if molt is recent enough to edit."""
        return (
            datetime.datetime.utcnow() - self.timestamp
        ).total_seconds() < config.MINUTES_EDITABLE * 60

    @property
    def mentions(self):
        """Return list of Crabs mentioned in Molt."""
        if self.raw_mentions:
            mention_list = self.raw_mentions.splitlines()
            return Crab.query.filter(func.lower(Crab.username).in_(mention_list)).all()
        return list()

    @property
    def pretty_date(self):
        """Return date of publish, formatted for display."""
        return utils.localize(self.timestamp).strftime("%I:%M %p · %b %e, %Y")

    @property
    def quotes(self):
        """Get all currently valid quotes of Molt."""
        return Molt.query_quotes(self).all()

    @property
    def quote_count(self):
        """Get number of currently valid quotes of Molt."""
        return Molt.query_quotes(self).count()

    @property
    def remolts(self):
        """Get all currently valid remolts of Molt."""
        return Molt.query_remolts(self).all()

    @property
    def remolt_count(self):
        """Get number of currently valid remolts of Molt."""
        return Molt.query_remolts(self).count()

    @property
    def replies(self):
        """List all currently valid Molts that reply to this Molt."""
        return self.query_replies().all()

    @property
    def reply_count(self):
        """Get number of currently valid Molts that reply to this Molt."""
        return self.query_replies().count()

    @property
    def likes(self):
        """List all currently valid likes of Molt."""
        return Molt.query_likes(self).all()

    @property
    def like_count(self):
        """List number of currently valid likes of Molt."""
        return Molt.query_likes(self).count()

    @property
    def RFC_2822(self):
        """Returns RFC 2822-compliant post date."""
        return email.utils.format_datetime(self.timestamp)

    @property
    def href(self):
        """Returns a link to this Molt."""
        return f"{config.BASE_URL}/user/{self.author.username}" f"/status/{self.id}/"

    @property
    def pretty_age(self):
        """Property wrapper for `Molt.get_pretty_age`."""
        return utils.get_pretty_age(self.timestamp)

    @property
    def is_thread(self):
        """Returns whether this molt is the start of a thread."""
        if (not self.is_reply) and self.get_reply_from(self.author):
            return True
        return False

    def get_author(self, column_names: Optional[Iterable[str]] = None):
        """Returns only necessary columns from Molt.author."""
        column_names = column_names or (
            "id",
            "username",
            "display_name",
            "verified",
            "deleted",
            "banned",
            "avatar",
        )
        columns = (Crab.column_dict.get(col) for col in column_names)
        author = db.session.query(*columns).filter(Crab.id == self.author_id).first()
        return author

    def evaluate_contents(self, notify: bool = True):
        """Evaluates Crabtags and Mentions in Molt.

        This should be called whenever content is changed.
        """
        # Update raw_tags to include all new tags
        if self.raw_tags is None:
            self.raw_tags = ""

        self.tags = list()

        # Parse all tags
        for tag in patterns.tag.findall(self.content):
            self.raw_tags += tag + "\n"

            # Update tags relationship to include all new tags
            self.tags.append(Crabtag.get(tag))

        # Parse all mentions
        for user in patterns.mention.findall(self.content):
            if self.raw_mentions is None:
                self.raw_mentions = ""
            self.raw_mentions += user.lower() + "\n"

        # Parse links
        card_url = None
        link = patterns.ext_link.search(self.content)
        if link:
            card_url = link.group(2)
        else:
            link = patterns.ext_md_link.search(self.content)
            if link:
                card_url = link.group(2)
        if card_url:
            # Check that link doesn't match any embed types
            if all(
                (
                    not pattern.match(card_url)
                    for pattern in [patterns.youtube, patterns.giphy, patterns.ext_img]
                )
            ):
                self.card = Card.get(card_url)

        # Notify mentioned users
        for user in self.mentions:
            user.notify(sender=self.author, type="mention", molt=self)

        # Award trophies where applicable:

        lowercase_tags = [tag.lower() for tag in self.raw_tags.splitlines()]
        if "420" in lowercase_tags:
            self.author.award(title="Pineapple Express")
        if "waaahhhh" in lowercase_tags:
            self.author.award(title="Mega Freakoid")
        if "lolcat" in lowercase_tags:
            self.author.award(title="i can haz cheezburger?")
        if "fffffffuuuuuuuuuuuu" in lowercase_tags:
            self.author.award(title="f7u12")
        if "1985" in lowercase_tags:
            self.author.award(title="Back to the Future")

    def approve(self):
        """Approve Molt so it doesn't show in reports page."""
        if not self.approved:
            self.approved = True
            db.session.commit()

    def unapprove(self):
        """Undo the approval of this Molt."""
        if self.approved:
            self.approved = False
            db.session.commit()

    def label_nsfw(self):
        """Mark molt as NSFW."""
        if not self.nsfw:
            self.nsfw = True
            db.session.commit()

    def label_sfw(self):
        """Mark molt as SFW (not NOT safe for work)."""
        if self.nsfw:
            self.nsfw = False
            db.session.commit()

    def semantic_content(self):
        """Render molt content for RSS.

        Returns Molt content (including embeds, tags, and mentions) rasterized as semantic
        HTML. (For RSS feeds and other external applications)
        """
        quoted_molt = self.original_molt if self.is_quote else None
        return utils.parse_semantic_content(
            self.content, self.image, quoted_molt=quoted_molt
        )

    def rich_content(self, full_size_media=False):
        """Render molt content for site.

        Returns Molt content (including embeds, tags, and mentions)
        rasterized as rich HTML.
        """
        return utils.parse_rich_content(
            self.content,
            full_size_media=full_size_media,
            nsfw=self.nsfw,
            card=self.card,
        )

    def dict(self):
        """Serialize Molt into dictionary."""
        return {
            "molt": {
                "author": {
                    "id": self.author.id,
                    "username": self.author.username,
                    "display_name": self.author.display_name,
                },
                "content": self.content,
                "rich_content": self.rich_content(),
                "likes": [like.id for like in self.likes],
                "remolts": [remolt.id for remolt in self.remolts],
                "image": None
                if self.image is None
                else config.BASE_URL + url_for("static", filename=self.image),
                "id": self.id,
                "timestamp": round(self.timestamp.timestamp()),
            }
        }

    def get_reply_from(self, crab: Union[List[int], Crab, int]) -> Optional["Molt"]:
        """Return first reply Molt from `crab` if it exists."""
        reply = None
        if self.reply_count > 0:
            reply = Molt.query.filter_by(
                is_reply=True, original_molt=self, deleted=False
            )
            if isinstance(crab, list):
                crab = [id for id in crab if id]
                reply = reply.filter(Molt.author_id.in_(crab))
            elif isinstance(crab, Crab):
                reply = reply.filter_by(author=crab)
            elif isinstance(crab, int):
                reply = reply.filter_by(author_id=crab)
            else:
                return None
            reply = reply.order_by(Molt.timestamp).first()
        return reply

    def get_reply_from_following(self, crab):
        """Return first reply Molt from a crab that `crab` follows if it exists."""
        reply = None
        if self.reply_count > 0:
            reply = (
                Molt.query_all()
                .filter(Molt.is_reply == true(), Molt.original_molt_id == self.id)
                .join(following_table, following_table.c.following_id == Molt.author_id)
                .filter(
                    or_(
                        following_table.c.follower_id == crab.id,
                        Molt.author_id == crab.id,
                    )
                )
                .order_by(Molt.timestamp)
                .first()
            )
        return reply

    def quote(self, author, comment, **kwargs):
        """Quote Molt as `author`."""
        kwargs["nsfw"] = kwargs.get("nsfw", self.nsfw)
        new_quote = author.molt(comment, is_quote=True, original_molt=self, **kwargs)
        self.author.notify(sender=author, type="quote", molt=new_quote)
        return new_quote

    def remolt(self, crab, **kwargs):
        """Remolt Molt as `crab`."""
        # Check if already remolted
        duplicate_remolt = Molt.query.filter_by(
            is_remolt=True, original_molt=self, author=crab, deleted=False
        )
        if not duplicate_remolt.count():
            new_remolt = crab.molt(
                "", is_remolt=True, original_molt=self, nsfw=self.nsfw, **kwargs
            )
            self.author.notify(sender=crab, type="remolt", molt=new_remolt)
            return new_remolt

    def reply(self, author, comment, **kwargs):
        """Reply to Molt as `author`."""
        kwargs["nsfw"] = kwargs.get("nsfw", self.nsfw)
        new_reply = author.molt(comment, is_reply=True, original_molt=self, **kwargs)
        self.author.notify(sender=author, type="reply", molt=new_reply)
        return new_reply

    def report(self):
        """Increment report counter for Molt."""
        self.reports += 1
        db.session.commit()

    def edit(self, content=None, image=None):
        """Change Molt content to `new_content`."""
        if self.editable:
            self.content = content or self.content
            self.image = image or self.image
            self.edited = True
            # Re-evaluate mentions and tags
            self.evaluate_contents()
            db.session.commit()

    def like(self, crab):
        """Like Molt as `crab`."""
        if not Like.query.filter_by(crab=crab, molt=self).all():
            new_like = Like(crab=crab, molt=self)
            db.session.add(new_like)
            self.author.notify(sender=crab, type="like", molt=self)

            # Check if awards are applicable:
            if self.like_count == 10:
                self.author.award(title="Dopamine Hit")
            if self.like_count == 100:
                self.author.award(title="Dopamine Addict")
            if self.like_count == 1000:
                self.author.award(title="Full on Junkie")
            if (
                "seth rogen" in self.content.lower()
                or "sethrogen" in self.raw_tags.lower()
            ):
                crab.award(title="Rogen Out of Control")

            db.session.commit()
            return new_like

    def unlike(self, crab):
        """Unlike Molt as `crab`."""
        old_like = Like.query.filter_by(crab=crab, molt=self).first()
        if old_like is not None:
            db.session.delete(old_like)
            db.session.commit()

    def delete(self):
        """Delete molt."""
        self.deleted = True
        db.session.commit()

    def restore(self):
        """Undelete/restore Molt."""
        self.deleted = False
        db.session.commit()

    # Query methods

    def query_likes(self):
        """Query this molt's likes."""
        return Like.query.filter_by(molt=self).filter(
            Like.crab.has(deleted=False, banned=False)
        )

    def query_quotes(self) -> BaseQuery:
        """Query this molt's quotes."""
        return Molt.query.filter_by(
            is_quote=True, original_molt=self, deleted=False
        ).filter(Molt.author.has(banned=False, deleted=False))

    def query_remolts(self) -> BaseQuery:
        """Query this molt's remolts."""
        return Molt.query.filter_by(
            is_remolt=True, original_molt=self, deleted=False
        ).filter(Molt.author.has(banned=False, deleted=False))

    def query_replies(self) -> BaseQuery:
        """Query this molt's replies."""
        return Molt.query.filter_by(
            is_reply=True, original_molt=self, deleted=False
        ).filter(Molt.author.has(banned=False, deleted=False))

    @staticmethod
    def query_all(
        include_replies=True, include_remolts=False, include_quotes=True
    ) -> BaseQuery:
        """Query all valid molts."""
        molts = (
            Molt.query.filter_by(deleted=False)
            .filter(Molt.author.has(deleted=False, banned=False))
            .order_by(Molt.timestamp.desc())
        )
        if not include_replies:
            molts = molts.filter_by(is_reply=False)
        if not include_remolts:
            molts = molts.filter_by(is_remolt=False)
        if not include_quotes:
            molts = molts.filter_by(is_quote=False)
        return molts

    @staticmethod
    def query_reported() -> BaseQuery:
        """Query reported molts."""
        queue = (
            Molt.query.filter_by(
                deleted=False,
                approved=False,
            )
            .filter(Molt.reports > 0)
            .filter(Molt.author.has(banned=False, deleted=False))
            .order_by(
                Molt.reports.desc(),
                Molt.timestamp.desc(),
            )
        )

        return queue

    @staticmethod
    def query_like_counts() -> BaseQuery:
        """Queries molt like counts and orders by likes descending.

        Returns as tuple: (molt_id: int, likes: int)
        """
        likes = (
            db.session.query(Like.molt_id, func.count(Like.molt_id).label("likes"))
            .group_by(Like.molt_id)
            .order_by(desc("likes"))
        )
        return likes

    @staticmethod
    def query_most_liked() -> BaseQuery:
        """Query most liked molts."""
        molts = (
            db.session.query(Molt, func.count(Like.id))
            .join(Molt, Molt.id == Like.molt_id)
            .filter(Like.molt.has(deleted=False))
            .filter(Like.crab.has(deleted=False))
            .filter(Like.molt.has(Molt.author.has(deleted=False, banned=False)))
            .order_by(func.count(Like.id).desc())
            .group_by(Like.molt_id)
        )
        return molts

    @staticmethod
    def query_most_replied() -> BaseQuery:
        """Query most replied molts."""
        unique_replies = (
            Molt.query_all()
            .filter_by(is_reply=True)
            .group_by(Molt.original_molt_id, Molt.author_id)
            .subquery()
        )
        molts = (
            Molt.query.join(
                unique_replies, unique_replies.c.original_molt_id == Molt.id
            )
            .group_by(Molt.id)
            .order_by(func.count(Molt.id).desc())
        )
        molts = Molt.filter_query_by_available(molts)
        return molts

    @staticmethod
    def query_with_tag(crabtag: Union["Crabtag", str]) -> BaseQuery:
        """Query molts containing a given crabtag."""
        molts = Molt.query_all().join(Molt.tags)
        if isinstance(crabtag, Crabtag):
            molts = molts.filter(Crabtag.name == crabtag.name)
        else:
            molts = molts.filter(Crabtag.name == crabtag.lower())
        molts = molts.order_by(Molt.timestamp.desc())
        return molts

    @staticmethod
    def filter_query_by_available(query: BaseQuery) -> BaseQuery:
        """Filters a Molt query by available Molts.

        This means Molts that are not deleted and are authored by Crabs
        that are neither deleted or banned.
        """
        query = query.filter(
            Molt.deleted == false(), Molt.author.has(deleted=false(), banned=false())
        ).filter(
            db.or_(Molt.is_remolt == false(), Molt.original_molt.has(deleted=False))
        )
        return query

    @staticmethod
    def order_query_by_likes(query: BaseQuery) -> BaseQuery:
        """Orders a Molt query by number of likes (descending)."""
        like_counts = Molt.query_like_counts().subquery()

        # Ordering by None overrides previous order_by
        query = query.outerjoin(like_counts).order_by(None).order_by(desc("likes"))
        return query

    @staticmethod
    def search(query: str) -> BaseQuery:
        """Search all molts."""
        results = (
            Molt.query.filter_by(deleted=False, is_reply=False)
            .filter(Molt.content.contains(query, autoescape=True))
            .filter(Molt.author.has(deleted=False, banned=False))
            .order_by(Molt.timestamp.desc())
        )
        return results

    @staticmethod
    def get_by_ID(id: int, include_invalidated: bool = False) -> Optional["Molt"]:
        """Get a Molt by ID."""
        molt = Molt.query.filter_by(id=id, is_remolt=False)
        if not include_invalidated:
            molt = molt.filter(Molt.author.has(deleted=False, banned=False)).filter_by(
                deleted=False
            )
        return molt.first()

    @classmethod
    def create(cls, author, content, **kwargs):
        """Create new molt."""
        kwargs["source"] = kwargs.get("source", "Crabber Web App")
        new_molt = cls(
            author=author, content=content[: config.MOLT_CHAR_LIMIT], **kwargs
        )

        new_molt.evaluate_contents()
        db.session.add(new_molt)
        db.session.commit()
        return new_molt


class Like(db.Model):
    """Represents one like given to a Molt by a Crab."""

    __table_args__ = (db.UniqueConstraint("crab_id", "molt_id"),)
    id = db.Column(db.Integer, primary_key=True)
    crab_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    crab = db.relationship("Crab", back_populates="_likes")
    molt_id = db.Column(db.Integer, db.ForeignKey("molt.id"), nullable=False)
    molt = db.relationship("Molt", back_populates="_likes")

    def __repr__(self):
        return f"<Like from '@{self.crab.username}'>"

    @staticmethod
    def query_all():
        """Queries all valid Likes (of valid Molt, Molt author, and Crab)."""
        likes = (
            Like.query.join(Like.molt)
            .filter(Like.crab.has(deleted=False, banned=False))
            .filter(Molt.deleted == false())
            .filter(Molt.author.has(deleted=False, banned=False))
        )
        return likes


class Notification(db.Model):
    """Represents a notificaiton given to a Crab."""

    id = db.Column(db.Integer, primary_key=True)
    # Crab receiving notif
    recipient_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    recipient = db.relationship(
        "Crab",
        backref=db.backref("notifications", order_by="Notification.timestamp.desc()"),
        foreign_keys=[recipient_id],
    )
    # Crab responsible for notif
    sender_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=True)
    sender = db.relationship("Crab", foreign_keys=[sender_id])

    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    read = db.Column(db.BOOLEAN, nullable=False, default=False)

    # can be: mention, reply, follow, like, remolt, other
    type = db.Column(db.String(32), nullable=False)

    # Molt (optional) (for replies, mentions, likes, etc)
    molt_id = db.Column(db.Integer, db.ForeignKey("molt.id"), nullable=True)
    molt = db.relationship("Molt", foreign_keys=[molt_id])

    # If type is 'other'
    content = db.Column(db.String(140), nullable=True)
    link = db.Column(db.String(140), nullable=True)

    def __repr__(self):
        return f"<Notification | '{self.type}' | '@{self.recipient.username}'>"

    @property
    def pretty_date(self):
        """Formats notification date in an attractive way."""
        return utils.localize(self.timestamp).strftime("%I:%M %p · %b %e, %Y")

    @property
    def pretty_age(self):
        """Formats notification age in an attractive way."""
        return utils.get_pretty_age(self.timestamp)

    @staticmethod
    def query_all() -> BaseQuery:
        """Returns a query containing all valid notifications."""
        return Notification.query.filter(
            or_(
                Notification.sender.has(deleted=False, banned=False),
                Notification.sender == null(),
            )
        )

    def mark_read(self, is_read=True):
        """Mark this notification as 'read' by the user."""
        self.read = is_read
        db.session.commit()


# Stores what users have what trophies
class TrophyCase(db.Model):
    """Represents the possession of a Trophy by a Crab."""

    id = db.Column(db.Integer, primary_key=True)
    # Crab who owns trophy
    owner_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    owner = db.relationship(
        "Crab",
        backref=db.backref("trophies", order_by="TrophyCase.timestamp.desc()"),
        foreign_keys=[owner_id],
    )
    # Trophy in question
    trophy_id = db.Column(db.Integer, db.ForeignKey("trophy.id"), nullable=False)
    trophy = db.relationship("Trophy", foreign_keys=[trophy_id])
    # Time trophy was awarded
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<TrophyCase | '{self.trophy.title}' | " f"'@{self.owner.username}'>"


# Stores each type of trophy
class Trophy(db.Model):
    """Represents an available trophy.

    Only one `Trophy` will exist per available trophy. Crabs are awarded `TrophyCase`
    instead.
    """

    id = db.Column(db.Integer, primary_key=True)
    # Short display title
    title = db.Column(db.String(32), nullable=False)
    # Medium description of what it's for
    description = db.Column(db.String(240), nullable=False)
    # Image to display as an icon
    image = db.Column(
        db.String(240),
        nullable=False,
        default="https://cdn.crabber.net/trophies/default_trophy.png",
    )

    def __repr__(self):
        return f"<Trophy '{self.title}'>"


class DeveloperKey(db.Model):
    """A key that grants API access to a developer under a given account."""

    __tablename__ = "developer_keys"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False)
    crab_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    crab = db.relationship("Crab", foreign_keys=[crab_id])
    deleted = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<DeveloperKey (@{self.crab.username})>"

    def delete(self):
        """Deletes this key."""
        self.deleted = True
        db.session.commit()

    @classmethod
    def gen_key(cls):
        """Generates a unique key string."""
        while True:
            key = secrets.token_hex(16)
            if not cls.query.filter_by(key=key).count():
                return key

    @classmethod
    def create(cls, crab):
        """Generates a new key for `crab`."""
        key = cls.gen_key()
        token = cls(crab=crab, key=key)
        db.session.add(token)
        db.session.commit()
        return token


class AccessToken(db.Model):
    """A key that grants a developer to take action on behalf of a `Crab`."""

    __tablename__ = "access_tokens"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False)
    crab_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    crab = db.relationship("Crab", foreign_keys=[crab_id])
    deleted = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<AccessToken (@{self.crab.username})>"

    def delete(self):
        """Deletes this key."""
        self.deleted = True
        db.session.commit()

    @classmethod
    def gen_key(cls):
        """Generates a unique key string."""
        while True:
            key = secrets.token_hex(16)
            if not cls.query.filter_by(key=key).count():
                return key

    @classmethod
    def create(cls, crab):
        """Generates a new key for `crab`."""
        key = cls.gen_key()
        token = cls(crab=crab, key=key)
        db.session.add(token)
        db.session.commit()
        return token


class Crabtag(db.Model):
    """Represents a specific crabtag used in at least one `Molt`."""

    __tablename__ = "crabtag"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), nullable=False)

    molts = db.relationship("Molt", secondary=crabtag_table, back_populates="tags")

    def __repr__(self):
        return f"<Crabtag '%{self.name}'>"

    def query_molts(self) -> BaseQuery:
        """Query Molts that use this tag."""
        return Molt.query_with_tag(self)

    @staticmethod
    def query_most_popular(since_date: Optional[datetime.datetime] = None) -> BaseQuery:
        """Queries the most popular (utilized) crabtags.

        Returns as tuple: (tag: Crabtag, count: int)
        """
        most_popular = (
            Crabtag.query.join(Crabtag.molts)
            .group_by(Crabtag.id)
            .add_columns(func.count(Crabtag.id).label("uses"))
            .order_by(desc("uses"))
        )
        most_popular = Molt.filter_query_by_available(most_popular)
        if since_date:
            most_popular = most_popular.filter(Molt.timestamp > since_date)
        return most_popular

    @staticmethod
    def get_trending(limit: int = 3) -> List[Tuple["Crabtag", int]]:
        """Return most popular Crabtags of the last week.

        :param limit: Number of results to return.
        """
        # Get date of 7 days ago
        since_date = datetime.datetime.utcnow() - datetime.timedelta(7)

        return Crabtag.query_most_popular(since_date=since_date).limit(limit).all()

    @classmethod
    def get(cls, name: str) -> "Crabtag":
        """Gets Crabtag by name and creates new ones where necessary."""
        crabtag = cls.query.filter_by(name=name.lower()).first()
        if crabtag is None:
            crabtag = cls(name=name.lower())
            db.session.add(crabtag)
        return crabtag


class Card(db.Model):
    """Represents a preview card for a URL."""

    __tablename__ = "card"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(1024))
    title = db.Column(db.String(256))
    description = db.Column(db.String(256))
    image = db.Column(db.String(1024))
    ready = db.Column(db.Boolean, default=False)
    failed = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Card {self.url!r}>"

    @staticmethod
    def format_url(url: str) -> str:
        """Removes unnecessary parts of URL and conforms to standard format."""
        # Strip extra bits
        url = patterns.url_essence.match(url).group(1)
        # Ensure trailing slash
        if not url.endswith("/"):
            url += "/"
        # Ensure https
        url = "https://" + url

        return url

    # Query methods

    @staticmethod
    def query_unready() -> BaseQuery:
        """Queries all Cards linked to valid Molts that aren't ready."""
        cards = (
            Molt.filter_query_by_available(
                Card.query.join(Molt, Molt.card_id == Card.id)
            )
            .filter(Molt.card)
            .filter(Molt.card.has(ready=False, failed=False))
        )
        return cards

    @classmethod
    def get(cls, url: str) -> "Card":
        """Gets Card by URL."""
        # Conform URL so that near-duplicates aren't created
        url = cls.format_url(url)
        card = cls.query.filter_by(url=url).first()
        if card is None:
            card = cls(url=url)
            db.session.add(card)
        return card


class Bookmark(db.Model):
    """Represents a `Crab`'s bookmark of a given `Molt`."""

    __tablename__ = "bookmark"
    __table_args__ = (db.UniqueConstraint("crab_id", "molt_id"),)

    id = db.Column(db.Integer, primary_key=True)
    crab_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    crab = db.relationship("Crab", back_populates="_bookmarks")
    molt_id = db.Column(db.Integer, db.ForeignKey("molt.id"), nullable=False)
    molt = db.relationship("Molt")
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Bookmark '@{self.crab.username}'>"

    @staticmethod
    def query_all():
        """Queries all valid bookmarks (of valid Molt, Molt author, and Crab)."""
        likes = (
            Like.query.join(Like.molt)
            .filter(Like.crab.has(deleted=False, banned=False))
            .filter(Molt.deleted == false())
            .filter(Molt.author.has(deleted=False, banned=False))
        )
        return likes


class ModLog(db.Model):
    """Represents the log of an action taken by a moderator."""

    __tablename__ = "mod_logs"
    id = db.Column(db.Integer, primary_key=True)
    mod_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    mod = db.relationship("Crab", foreign_keys=[mod_id])
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    action = db.Column(db.String(64), nullable=False)
    additional_context = db.Column(db.String(512))

    # Subject Crab
    crab_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    crab = db.relationship("Crab", foreign_keys=[crab_id])

    # Subject Molt
    molt_id = db.Column(db.Integer, db.ForeignKey("molt.id"))
    molt = db.relationship("Molt", foreign_keys=[molt_id])

    def __repr__(self):
        return f"<ModLog (@{self.mod.username})>"

    def __str__(self):
        action_text = "unknown"
        if self.action == "attempted_action_on_mod":
            action_text = f"attempted action on mod or admin (@{self.crab.username})"
        elif self.action == "ban":
            action_text = (
                f"banned user (@{self.crab.username}, "
                f'reason: "{self.additional_context}")'
            )
        elif self.action == "unban":
            action_text = f"unbanned user (@{self.crab.username})"
        elif self.action == "warn":
            action_text = (
                f"warned user (@{self.crab.username}, "
                f'message: "{self.additional_context}")'
            )
        elif self.action == "clear_username":
            action_text = (
                f"cleared username (@{self.crab.username}, "
                f"originally @{self.additional_context})"
            )
        elif self.action == "clear_display_name":
            action_text = (
                f"cleared display name (@{self.crab.username}, "
                f'originally "{self.additional_context}")'
            )
        elif self.action == "clear_description":
            action_text = (
                f"cleared user description (@{self.crab.username}, "
                f"see DB for more details)"
            )
        elif self.action == "clear_avatar":
            action_text = (
                f"cleared avatar (@{self.crab.username}, "
                f'originally "{self.additional_context}")'
            )
        elif self.action == "clear_banner":
            action_text = (
                f"cleared banner (@{self.crab.username}, "
                f'originally "{self.additional_context}")'
            )
        elif self.action == "disable_referrals":
            action_text = f"disabled referral code (@{self.crab.username})"
        elif self.action == "enable_referrals":
            action_text = f"re-enabled referral code (@{self.crab.username})"
        elif self.action == "verify_user":
            action_text = f"verified user (@{self.crab.username})"
        elif self.action == "unverify_user":
            action_text = f"unverified user (@{self.crab.username})"
        elif self.action == "award_trophy":
            action_text = (
                f"awarded trophy to user (@{self.crab.username}, "
                f'"{self.additional_context}")'
            )
        elif self.action == "approve_molt":
            action_text = f"approved molt (#{self.molt.id}, @{self.crab.username})"
        elif self.action == "unapprove_molt":
            action_text = f"unapproved molt (#{self.molt.id}, @{self.crab.username})"
        elif self.action == "delete_molt":
            action_text = f"deleted molt (#{self.molt.id}, @{self.crab.username})"
        elif self.action == "restore_molt":
            action_text = f"restored molt (#{self.molt.id}, @{self.crab.username})"
        elif self.action == "nsfw_molt":
            action_text = f"labeled molt NSFW (#{self.molt.id}, @{self.crab.username})"
        elif self.action == "sfw_molt":
            action_text = (
                f"removed molt's NSFW label (#{self.molt.id}, @{self.crab.username})"
            )

        return (
            f'[{self.timestamp.isoformat(timespec="seconds")}]'
            + f" [@{self.mod.username}]".ljust(16)
            + f" - {action_text}"
        )

    @classmethod
    def create(
        cls,
        mod: Crab,
        action: str,
        crab: Crab,
        molt: Optional[Molt] = None,
        additional_context: Optional[str] = None,
    ):
        """Logs a new action."""
        log = cls(
            mod=mod,
            action=action,
            crab=crab,
            molt=molt,
            additional_context=additional_context,
        )
        db.session.add(log)
        db.session.commit()
        return log


class ImageDescription(db.Model):
    """Represents a user-provided text description for a given image url."""

    __tablename__ = "image_description"

    id = db.Column(db.Integer, primary_key=True)
    src = db.Column(db.String(1024))
    alt = db.Column(db.String(1024))

    def __repr__(self) -> str:
        return f"<ImageDescription {self.src!r}>"

    @classmethod
    def get(cls, src: str) -> Optional["ImageDescription"]:
        """Gets image description object by image source URL."""
        return cls.query.filter_by(src=src).first()

    @classmethod
    def get_alt(cls, src: str) -> Optional[str]:
        """Gets image description string by image source URL."""
        desc = cls.query.filter_by(src=src).first()
        if desc:
            return desc.alt

    @classmethod
    def set(cls, src: str, alt: str) -> "ImageDescription":
        """Creates image description by image source URL."""
        desc = cls.query.filter_by(src=src).first()
        if desc:
            desc.alt = alt
            db.session.commit()
        else:
            desc = cls(src=src, alt=alt)
            db.session.add(desc)
            db.session.commit()
        return desc


class ReferralCode(db.Model):
    """A code that tracks user referrals."""

    __tablename__ = "referral_codes"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False)
    crab_id = db.Column(db.Integer, db.ForeignKey("crab.id"), nullable=False)
    crab = db.relationship("Crab", foreign_keys=[crab_id])
    uses = db.Column(db.Integer, nullable=False, default=0)
    disabled = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<ReferralCode (@{self.crab.username})>"

    @property
    def link(self):
        """Returns a sign-up link that uses the referral code."""
        return f"{config.BASE_URL}/signup/?referral-code={self.key}"

    def disable(self):
        """Disables this referral code."""
        if not self.disabled:
            self.disabled = True
            db.session.commit()

    def enable(self):
        """Re-enables this referral code."""
        if self.disabled:
            self.disabled = False
            db.session.commit()

    @classmethod
    def use(cls, key) -> Optional["Crab"]:
        """Uses referral code and returns referrer if code exists."""
        code = cls.query.filter_by(key=key).first()
        if code:
            if not code.disabled:
                code.uses += 1
                db.session.commit()
                return code.crab

    @classmethod
    def gen_key(cls):
        """Generates a unique key string."""
        while True:
            key = secrets.token_hex(16)
            if not cls.query.filter_by(key=key).count():
                return key

    @classmethod
    def get(cls, crab):
        """Gets or creates the referral code for `crab`."""
        code = cls.query.filter_by(crab=crab).first()
        if code is None:
            code = cls.create(crab)
        return code

    @classmethod
    def create(cls, crab):
        """Generates a new referral code for `crab`."""
        key = cls.gen_key()
        code = cls(crab=crab, key=key)
        db.session.add(code)
        db.session.commit()
        return code
