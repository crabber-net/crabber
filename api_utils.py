from config import *
import json
import models
from typing import List, Optional


def get_timestamp(datetime):
    return int(datetime.timestamp())


def get_crab(crab_ID: int) -> Optional['models.Crab']:
    crab = models.Crab.query \
            .filter_by(id=crab_ID, deleted=False, banned=False).first()
    return crab


def get_molt(molt_ID: int) -> Optional['models.Molt']:
    molt = models.Molt.query \
            .filter_by(id=molt_ID, deleted=False) \
            .filter(models.Molt.author.has(deleted=False, banned=False)) \
            .first()
    return molt


def get_molts_from_crab(crab: 'models.Crab', limit=API_DEFAULT_MOLT_LIMIT,
                        offset=0, since=None) -> List['models.Molt']:
    query = models.Molt.query \
            .filter_by(deleted=False, author=crab) \
            .order_by(models.Molt.timestamp.desc()) \
            .limit(limit).offset(offset)
    if since:
        query = query.filter(models.Molt.timestamp > since)
    return query.all()


def crab_to_json(crab: 'models.Crab', bio: bool = False) -> dict:
    crab_dict = {
        "id": crab.id,
        "display_name": crab.display_name,
        "username": crab.username,
        "verified": crab.verified,
        "avatar": crab.avatar,
        "followers": crab.true_follower_count,
        "following": crab.true_following_count,
    }
    if bio:
        raw_bio = json.loads(crab.raw_bio)
        crab_bio = {
            "description": crab.description,
            "location": crab.location,
            "register_time": get_timestamp(crab.register_time),
            **raw_bio
        }
        crab_dict['bio'] = crab_bio
    return crab_dict


def molt_to_json(molt: 'models.Molt', replies: bool = False) -> dict:
    molt_json = {
        "id": molt.id,
        "author": crab_to_json(molt.author),
        "text": molt.content,
        "crabtags": molt.tags,
        "mentions": list(set(molt.raw_mentions.lower().splitlines())),
        "timestamp": get_timestamp(molt.timestamp)
    }
    return molt_json
