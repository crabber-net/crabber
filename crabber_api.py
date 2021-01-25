import api_utils
from config import *
from flask import abort, Blueprint, request
import models

API = Blueprint('REST API v1', __name__)

@API.route('/')
def root():
    return 'Congrats. You\'ve taken your first step into a larger world.'


@API.route('/crabs/<crab_ID>/')
def get_crab(crab_ID):
    crab = api_utils.get_crab(crab_ID)
    if crab:
        return api_utils.crab_to_json(crab)
    else:
        return abort(404)


@API.route('/crabs/<crab_ID>/bio/')
def get_crab_bio(crab_ID):
    crab = api_utils.get_crab(crab_ID)
    if crab:
        return api_utils.crab_to_json(crab, bio=True)
    else:
        return abort(404)


@API.route('/crabs/<crab_ID>/molts/')
def get_crab_molts(crab_ID):
    limit = request.args.get('limit', API_DEFAULT_MOLT_LIMIT)
    try:
        limit = min(int(limit), API_MAX_MOLT_LIMIT)
    except ValueError:
        limit = 0
    offset = request.args.get('offset')
    since = request.args.get('since')

    crab = api_utils.get_crab(crab_ID)
    if crab:
        molts = api_utils.get_molts_from_crab(crab, limit=limit, offset=offset,
                                              since=since)
        molts_json = {
            "molts": [api_utils.molt_to_json(molt) for molt in molts]
        }
        return molts_json
    else:
        return abort(404)


@API.route('/molts/<molt_ID>/')
def get_molt_replies(molt_ID):
    return abort(501)
