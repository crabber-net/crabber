import api_utils
from config import *
from flask import abort, Blueprint, request
import models
from typing import Optional
import utils

API = Blueprint("REST API v1", __name__)


def get_api_key():
    """A key function for use by flask_limiter."""
    return request.args.get("api_key")


def require_auth(request) -> Optional[dict]:
    access_token = request.args.get("access_token")
    if access_token:
        token_object = models.AccessToken.query.filter_by(
            key=access_token, deleted=False
        ).first()
        if token_object:
            return dict(crab_id=token_object.crab.id)


@API.before_request
def check_API_key():
    api_key = request.args.get("api_key")
    if not api_key:
        return abort(400, description="API key not provided.")
    key_object = models.DeveloperKey.query.filter_by(key=api_key, deleted=False).first()

    # Invalid key
    if key_object is None:
        return abort(400, description="API key is invalid or expired.")
    # Key owner deleted
    if key_object.crab.deleted:
        return abort(
            400,
            description="The account to which this API key "
            "belongs has been deleted.",
        )
    # Key owner banned
    if key_object.crab.banned:
        return abort(
            400,
            description="The account to which this API key " "belongs has been banned.",
        )


@API.route("/")
def root():
    return "Congrats. You've taken your first step into a larger world."


@API.route("/authenticate/")
def authenticate():
    auth = require_auth(request)
    if auth:
        return api_utils.crab_to_json(api_utils.get_crab(auth["crab_id"]))
    else:
        return abort(401, description="This endpoint requires authentication.")


@API.route("/crabs/<crab_ID>/")
def get_crab(crab_ID):
    crab = api_utils.get_crab(crab_ID)
    if crab:
        return api_utils.crab_to_json(crab)
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/username/<username>/")
def get_crab_by_username(username):
    crab = api_utils.get_crab_by_username(username)
    if crab:
        return api_utils.crab_to_json(crab)
    else:
        return abort(404, description="No Crab with that username.")


@API.route("/crabs/<crab_ID>/follow/", methods=["POST"])
def follow_crab(crab_ID):
    target_crab = api_utils.get_crab(crab_ID)
    if target_crab:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                if crab is not target_crab:
                    crab.follow(target_crab)
                    return "Followed Crab.", 200
                else:
                    return abort(400, description="Cannot follow self.")
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/<crab_ID>/unfollow/", methods=["POST"])
def unfollow_crab(crab_ID):
    target_crab = api_utils.get_crab(crab_ID)
    if target_crab:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                crab.unfollow(target_crab)
                return "Unfollowed Crab.", 200
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/<crab_ID>/bio/", methods=["GET", "POST"])
def crab_bio(crab_ID):
    crab = api_utils.get_crab(crab_ID)
    if crab:
        if request.method == "GET":
            return api_utils.crab_to_json(crab, bio=True)
        elif request.method == "POST":
            auth = require_auth(request)
            if auth:
                if crab.id == auth["crab_id"]:
                    new_bio = {
                        key: value
                        for key, value in request.form.items()
                        if key
                        in (
                            "age",
                            "description",
                            "emoji",
                            "jam",
                            "location",
                            "obsession",
                            "pronouns",
                            "quote",
                            "remember",
                        )
                        and value
                    }
                    crab.update_bio(new_bio)
                    return api_utils.crab_to_json(crab, bio=True)
                else:
                    return abort(
                        401,
                        description="This bio does not "
                        "belong to the authorized user.",
                    )
            else:
                return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/<crab_ID>/followers/")
def get_crab_followers(crab_ID):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_CRAB_LIMIT, minimum=0, maximum=API_MAX_CRAB_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)

    crab = api_utils.get_crab(crab_ID)
    if crab:
        followers = api_utils.get_crab_followers(crab)
        followers_json = api_utils.query_to_json(followers, limit=limit, offset=offset)
        return followers_json
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/<crab_ID>/bookmarks/")
def get_crab_bookmarks(crab_ID):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_CRAB_LIMIT, minimum=0, maximum=API_MAX_CRAB_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)

    crab = api_utils.get_crab(crab_ID)
    if crab:
        auth = require_auth(request)
        if auth:
            if crab.id == auth["crab_id"]:
                bookmarks = crab.query_bookmarks()
                bookmarks_json = api_utils.query_to_json(bookmarks)
                return bookmarks_json
            else:
                return abort(
                    401,
                    description="These bookmarks do not "
                    "belong to the authorized user.",
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/<crab_ID>/following/")
def get_crab_following(crab_ID):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_CRAB_LIMIT, minimum=0, maximum=API_MAX_CRAB_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)

    crab = api_utils.get_crab(crab_ID)
    if crab:
        following = api_utils.get_crab_following(crab)
        following_json = api_utils.query_to_json(following, limit=limit, offset=offset)
        return following_json
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/crabs/<crab_ID>/molts/")
def get_crab_molts(crab_ID):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    crab = api_utils.get_crab(crab_ID)
    if crab:
        molts = api_utils.get_molts_from_crab(crab, since=since, since_id=since_id)
        molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
        return molts_json
    else:
        return abort(404, description="No Crab with that ID.")


@API.route("/molts/", methods=["POST"])
def post_molt():
    auth = require_auth(request)
    if auth:
        crab = api_utils.get_crab(auth["crab_id"])
        if crab:
            molt_content = request.form.get("content")
            molt_image_link = request.form.get("image")
            molt_image = request.files.get("image")
            molt_source = request.form.get("source", "Crabber API")
            image_verified = False

            if molt_image_link:
                return abort(400, "Images must be submitted as files, not text.")
            if molt_image:
                if molt_image.filename != "":
                    if molt_image and utils.allowed_file(molt_image.filename):
                        image_verified = True
                    else:
                        return abort(
                            400, "There was a problem with the uploaded image."
                        )
                else:
                    return abort(400, "Image filename is blank. Aborting.")
            if molt_content:
                if len(molt_content) <= MOLT_CHAR_LIMIT:
                    if image_verified:
                        molt_image = utils.upload_image(molt_image)
                        if molt_image is None:
                            return abort(400, "Image is corrupted.")
                        new_molt = crab.molt(
                            molt_content, image=molt_image, source=molt_source
                        )
                    else:
                        new_molt = crab.molt(molt_content, source=molt_source)
                    return api_utils.molt_to_json(new_molt), 201
                else:
                    return abort(
                        400,
                        description="Molt length must be less than or equal "
                        f"to {MOLT_CHAR_LIMIT} characters.",
                    )
            else:
                return abort(400, description="Missing required content.")
        else:
            return abort(400, description="The authorized user no longer " "exists.")
    else:
        return abort(401, description="This endpoint requires authentication.")


@API.route("/molts/<molt_ID>/", methods=["GET", "DELETE"])
def get_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        if request.method == "DELETE":
            auth = require_auth(request)
            if auth:
                crab = api_utils.get_crab(auth["crab_id"])
                if crab:
                    if molt.author is crab:
                        molt.delete()
                        return "Molt successfully deleted.", 200
                    else:
                        return abort(
                            400,
                            description="The authorized user "
                            "does not own this Molt.",
                        )
                else:
                    return abort(
                        400, description="The authorized user no " "longer exists."
                    )
            else:
                return abort(401, description="This endpoint requires authentication.")
        else:
            return api_utils.molt_to_json(molt)
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/edit/", methods=["POST"])
def edit_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                molt_content = request.form.get("content")
                molt_image_link = request.form.get("image")
                molt_image = request.files.get("image")
                molt_source = request.form.get("source", "Crabber API")
                image_verified = False

                if molt_image_link:
                    return abort(400, "Images must be submitted as files, not text.")
                if molt_image:
                    if molt_image.filename != "":
                        if molt_image and utils.allowed_file(molt_image.filename):
                            image_verified = True
                        else:
                            return abort(
                                400, "There was a problem with the uploaded image."
                            )
                    else:
                        return abort(400, "Image filename is blank. Aborting.")
                if molt.editable:
                    if image_verified:
                        if molt.editable:
                            molt_image = utils.upload_image(molt_image)
                            molt.edit(content=molt_content, image=molt_image)
                    elif molt_content:
                        molt.edit(content=molt_content)
                    else:
                        return abort(400, description="Missing required content.")
                    # Return edited Molt
                    return api_utils.molt_to_json(molt), 201
                else:
                    return abort(400, description="Molt is not editable.")
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires " "authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/quote/", methods=["POST"])
def quote_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                molt_content = request.form.get("content")
                molt_image_link = request.form.get("image")
                molt_image = request.files.get("image")
                molt_source = request.form.get("source", "Crabber API")
                image_verified = False

                if molt_image_link:
                    return abort(400, "Images must be submitted as files, not text.")
                if molt_image:
                    if molt_image.filename != "":
                        if molt_image and utils.allowed_file(molt_image.filename):
                            image_verified = True
                        else:
                            return abort(
                                400, "There was a problem with the uploaded image."
                            )
                    else:
                        return abort(400, "Image filename is blank. Aborting.")
                if molt_content:
                    if image_verified:
                        molt_image = utils.upload_image(molt_image)
                        new_molt = molt.quote(
                            crab, molt_content, image=molt_image, source=molt_source
                        )
                    else:
                        new_molt = molt.quote(crab, molt_content, source=molt_source)
                    return api_utils.molt_to_json(new_molt), 201
                else:
                    return abort(400, description="Missing required content.")
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires " "authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/reply/", methods=["POST"])
def reply_to_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                molt_content = request.form.get("content")
                molt_image_link = request.form.get("image")
                molt_image = request.files.get("image")
                molt_source = request.form.get("source", "Crabber API")
                image_verified = False

                if molt_image_link:
                    return abort(400, "Images must be submitted as files, not text.")
                if molt_image:
                    if molt_image.filename != "":
                        if molt_image and utils.allowed_file(molt_image.filename):
                            image_verified = True
                        else:
                            return abort(
                                400, "There was a problem with the uploaded image."
                            )
                    else:
                        return abort(400, "Image filename is blank. Aborting.")
                if molt_content:
                    if image_verified:
                        molt_image = utils.upload_image(molt_image)
                        new_molt = molt.reply(
                            crab, molt_content, image=molt_image, source=molt_source
                        )
                    else:
                        new_molt = molt.reply(crab, molt_content, source=molt_source)
                    return api_utils.molt_to_json(new_molt), 201
                else:
                    return abort(400, description="Missing required content.")
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires " "authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/remolt/", methods=["POST", "DELETE"])
def remolt_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                if request.method == "POST":
                    if molt.author is not crab:
                        if not crab.has_remolted(molt):
                            molt.remolt(crab)
                            return "Remolted Molt.", 200
                        else:
                            return abort(
                                400,
                                description="Molt has already "
                                "been remolted by user.",
                            )
                    else:
                        return abort(400, description="Cannot remolt own Molt.")
                else:
                    remolt_shell = crab.has_remolted(molt)
                    if remolt_shell:
                        remolt_shell.delete()
                        return "Remolt successfully deleted.", 200
                    else:
                        return abort(400, description="No Remolt to delete.")
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires " "authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/bookmark/", methods=["POST"])
def bookmark_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                if not crab.has_bookmarked(molt):
                    crab.bookmark(molt)
                return "Bookmarked Molt.", 200
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/unbookmark/", methods=["POST"])
def unbookmark_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                if crab.has_bookmarked(molt):
                    crab.unbookmark(molt)
                return "Unbookmarked Molt.", 200
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/like/", methods=["POST"])
def like_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                if not crab.has_liked(molt):
                    molt.like(crab)
                return "Liked Molt.", 200
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/unlike/", methods=["POST"])
def unlike_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        auth = require_auth(request)
        if auth:
            crab = api_utils.get_crab(auth["crab_id"])
            if crab:
                if crab.has_liked(molt):
                    molt.unlike(crab)
                return "Unliked Molt.", 200
            else:
                return abort(
                    400, description="The authorized user no " "longer exists."
                )
        else:
            return abort(401, description="This endpoint requires authentication.")
    else:
        return abort(404, description="No Molt with that ID.")


@API.route("/molts/<molt_ID>/replies/")
def get_molt_replies(molt_ID):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    replies = api_utils.get_molt_replies(molt_ID, since=since, since_id=since_id)
    replies_json = api_utils.query_to_json(replies, limit=limit, offset=offset)
    return replies_json


@API.route("/molts/<molt_ID>/quotes/")
def get_molt_quotes(molt_ID):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    quotes = api_utils.get_molt_quotes(molt_ID, since=since, since_id=since_id)
    quotes_json = api_utils.query_to_json(quotes, limit=limit, offset=offset)
    return quotes_json


@API.route("/molts/mentioning/<username>/")
def get_molts_mentioning(username):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    molts = api_utils.get_molts_mentioning(username, since=since, since_id=since_id)
    molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
    return molts_json


@API.route("/molts/replying/<username>/")
def get_molts_replying(username):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    molts = api_utils.get_molts_replying_to(username, since=since, since_id=since_id)
    molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
    return molts_json


@API.route("/crabtag/<crabtag>/")
def get_crabtag(crabtag):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    molts = api_utils.get_molts_with_tag(crabtag, since=since, since_id=since_id)
    molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
    return molts_json


@API.route("/timeline/<username>/")
def get_timeline(username):
    limit = request.args.get("limit")
    limit = api_utils.expect_int(
        limit, default=API_DEFAULT_MOLT_LIMIT, minimum=0, maximum=API_MAX_MOLT_LIMIT
    )
    offset = request.args.get("offset")
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get("since"))
    since_id = request.args.get("since_id")

    crab = api_utils.get_crab_by_username(username)
    if crab:
        molts = api_utils.get_timeline(crab, since=since, since_id=since_id)
        molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
        return molts_json
    else:
        return abort(404, description="No Crab with that username.")
