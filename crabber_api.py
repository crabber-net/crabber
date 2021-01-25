import api_utils
from config import *
from flask import abort, Blueprint, request
import models
from typing import Optional

API = Blueprint('REST API v1', __name__)


def require_auth(request) -> Optional[dict]:
    # TODO: Proper authentication
    if request.args.get('auth'):
        return dict(crab_id=1)


@API.before_request
def check_API_key():
    api_key = request.args.get('api_key')
    if not api_key:
        return abort(400, description='API key not provided.')
    # TODO: Check if API key is valid


@API.route('/')
def root():
    return 'Congrats. You\'ve taken your first step into a larger world.'


@API.route('/crabs/<crab_ID>/')
def get_crab(crab_ID):
    crab = api_utils.get_crab(crab_ID)
    if crab:
        return api_utils.crab_to_json(crab)
    else:
        return abort(404, description='No Crab with that ID.')


@API.route('/crabs/<crab_ID>/bio/')
def get_crab_bio(crab_ID):
    crab = api_utils.get_crab(crab_ID)
    if crab:
        return api_utils.crab_to_json(crab, bio=True)
    else:
        return abort(404, description='No Crab with that ID.')

@API.route('/crabs/<crab_ID>/followers/')
def get_crab_followers(crab_ID):
    limit = request.args.get('limit')
    limit = api_utils.expect_int(limit, default=API_DEFAULT_CRAB_LIMIT,
                                 minimum=0, maximum=API_MAX_CRAB_LIMIT)
    offset = request.args.get('offset')
    offset = api_utils.expect_int(offset, default=0, minimum=0)

    crab = api_utils.get_crab(crab_ID)
    if crab:
        followers = api_utils.get_crab_followers(crab)
        followers_json = api_utils.query_to_json(followers, limit=limit,
                                                 offset=offset)
        return followers_json
    else:
        return abort(404, description='No Crab with that ID.')

@API.route('/crabs/<crab_ID>/following/')
def get_crab_following(crab_ID):
    limit = request.args.get('limit')
    limit = api_utils.expect_int(limit, default=API_DEFAULT_CRAB_LIMIT,
                                 minimum=0, maximum=API_MAX_CRAB_LIMIT)
    offset = request.args.get('offset')
    offset = api_utils.expect_int(offset, default=0, minimum=0)

    crab = api_utils.get_crab(crab_ID)
    if crab:
        following = api_utils.get_crab_following(crab)
        following_json = api_utils.query_to_json(following, limit=limit,
                                                 offset=offset)
        return following_json
    else:
        return abort(404, description='No Crab with that ID.')

@API.route('/crabs/<crab_ID>/molts/')
def get_crab_molts(crab_ID):
    limit = request.args.get('limit')
    limit = api_utils.expect_int(limit, default=API_DEFAULT_MOLT_LIMIT,
                                 minimum=0, maximum=API_MAX_MOLT_LIMIT)
    offset = request.args.get('offset')
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get('since'))

    crab = api_utils.get_crab(crab_ID)
    if crab:
        molts = api_utils.get_molts_from_crab(crab, since=since)
        molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
        return molts_json
    else:
        return abort(404, description='No Crab with that ID.')


@API.route('/molts/', methods=['POST'])
def post_molt():
    auth = require_auth(request)
    if auth:
        crab = api_utils.get_crab(auth['crab_id'])
        if crab:
            molt_content = request.form.get('content')
            if molt_content:
                new_molt = crab.molt(molt_content)
                return api_utils.molt_to_json(new_molt), 201
            else:
                return abort(400, description='Missing required content.')
        else:
            return abort(400, description='The authorized user no longer ' \
                         'exists.')
    else:
        return abort(401, description='This endpoint requires authentication.')


@API.route('/molts/<molt_ID>/', methods=['GET', 'DELETE'])
def get_molt(molt_ID):
    molt = api_utils.get_molt(molt_ID)
    if molt:
        if request.method == 'DELETE':
            auth = require_auth(request)
            if auth:
                crab = api_utils.get_crab(auth['crab_id'])
                if crab:
                    if molt.author is crab:
                        molt.delete()
                        return 'Molt successfully deleted.', 200
                    else:
                        return abort(400, description='The authorized user ' \
                                     'does not own this Molt.')
                else:
                    return abort(400, description='The authorized user no ' \
                                 'longer exists.')
            else:
                return abort(401, description='This endpoint requires authentication.')
        else:
            return api_utils.molt_to_json(molt)
    else:
        return abort(404, description='No Molt with that ID.')


@API.route('/molts/<molt_ID>/replies/')
def get_molt_replies(molt_ID):
    limit = request.args.get('limit')
    limit = api_utils.expect_int(limit, default=API_DEFAULT_MOLT_LIMIT,
                                 minimum=0, maximum=API_MAX_MOLT_LIMIT)
    offset = request.args.get('offset')
    offset = api_utils.expect_int(offset, default=0, minimum=0)

    replies = api_utils.get_molt_replies(molt_ID)
    replies_json = api_utils.query_to_json(replies, limit=limit, offset=offset)
    return replies_json


@API.route('/molts/mentioning/<username>/')
def get_molts_mentioning(username):
    limit = request.args.get('limit')
    limit = api_utils.expect_int(limit, default=API_DEFAULT_MOLT_LIMIT,
                                 minimum=0, maximum=API_MAX_MOLT_LIMIT)
    offset = request.args.get('offset')
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get('since'))

    molts = api_utils.get_molts_mentioning(username, since=since)
    molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
    return molts_json


@API.route('/crabtag/<crabtag>/')
def get_crabtag(crabtag):
    limit = request.args.get('limit')
    limit = api_utils.expect_int(limit, default=API_DEFAULT_MOLT_LIMIT,
                                 minimum=0, maximum=API_MAX_MOLT_LIMIT)
    offset = request.args.get('offset')
    offset = api_utils.expect_int(offset, default=0, minimum=0)
    since = api_utils.expect_timestamp(request.args.get('since'))

    molts = api_utils.get_molts_with_tag(crabtag, since=since)
    molts_json = api_utils.query_to_json(molts, limit=limit, offset=offset)
    return molts_json
