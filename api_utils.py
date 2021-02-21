import calendar
from config import *
from datetime import datetime
from flask_sqlalchemy import BaseQuery
import json
import models
from sqlalchemy import or_
from typing import Any, List, Optional


def expect_int(value: Any, default: int, minimum: Optional[int] = None,
               maximum: Optional[int] = None):
    """ Conform a value of unknown type into an optionally bounded integer.
    """
    if value:
        try:
            value = int(value)
            if minimum:
                value = max(value, minimum)
            if maximum:
                value = min(value, maximum)
        except ValueError:
            value = default
    return value or default


def expect_timestamp(value: Any) -> Optional[datetime]:
    """ Conform a value of unknown type into a datetime object.
    """
    value = expect_int(value, 0)
    if value:
        value = datetime.fromtimestamp(value)
    return value or None


def absolute_url(relative_url: str) -> Optional[str]:
    """ Get the absolute url (minus base host) from a partial URL.
    """
    return '/static/' + relative_url if relative_url else None


def get_timestamp(datetime: datetime) -> int:
    """ Get the UTC timestamp from a datetime object.
    """
    return int(calendar.timegm(datetime.utctimetuple()))


def get_crab(crab_ID: int) -> Optional['models.Crab']:
    """ Get a Crab by ID.
    """
    crab = models.Crab.query \
            .filter_by(id=crab_ID, deleted=False, banned=False).first()
    return crab


def get_crab_by_username(username: str) -> Optional['models.Crab']:
    """ Get a Crab by username.
    """
    crab = models.Crab.query \
            .filter(models.Crab.username.ilike(username)) \
            .filter_by(deleted=False, banned=False).first()
    return crab


def get_crab_followers(crab: 'models.Crab') -> BaseQuery:
    """ Get a Crab's followers.
    """
    query = models.Crab.query.filter_by(deleted=False, banned=False) \
            .join(models.following_table,
                  models.following_table.c.follower_id == models.Crab.id) \
            .filter(models.following_table.c.following_id == crab.id)
    return query


def get_crab_following(crab: 'models.Crab') -> BaseQuery:
    """ Get a Crab's following.
    """
    query = models.Crab.query.filter_by(deleted=False, banned=False) \
            .join(models.following_table,
                  models.following_table.c.following_id == models.Crab.id) \
            .filter(models.following_table.c.follower_id == crab.id)
    return query


def get_molt(molt_ID: int) -> Optional['models.Molt']:
    """ Get a Molt by ID.
    """
    molt = models.Molt.query \
            .filter_by(id=molt_ID, deleted=False, is_remolt=False) \
            .filter(models.Molt.author.has(deleted=False, banned=False)) \
            .first()
    return molt


def get_molt_quotes(molt_ID: int, since: Optional[int] = None,
                    since_id: Optional[int] = None) -> BaseQuery:
    """ Get the replies of a Molt by ID.
    """
    query = models.Molt.query \
            .filter_by(deleted=False, is_quote=True, original_molt_id=molt_ID) \
            .filter(models.Molt.author.has(banned=False, deleted=False)) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query


def get_molt_replies(molt_ID: int, since: Optional[int] = None,
                     since_id: Optional[int] = None) -> BaseQuery:
    """ Get the replies of a Molt by ID.
    """
    query = models.Molt.query \
            .filter_by(deleted=False, is_reply=True, original_molt_id=molt_ID) \
            .filter(models.Molt.author.has(banned=False, deleted=False)) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query


def get_molts_mentioning(username: str, since: Optional[int] = None,
                         since_id: Optional[int] = None) \
        -> BaseQuery:
    """ Get the Molts that mention a username.
    """
    query = models.Molt.query \
            .filter_by(deleted=False) \
            .filter(or_(models.Molt.raw_mentions.ilike(f'%\n{username}\n%'),
                        models.Molt.raw_mentions.ilike(f'{username}\n%'))) \
            .filter(models.Molt.author.has(banned=False, deleted=False)) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query


def get_molts_replying_to(username: str, since: Optional[int] = None,
                          since_id: Optional[int] = None) \
        -> BaseQuery:
    """ Get the Molts that reply to a Molt authored by `username`.
    """
    target_crab = get_crab_by_username(username)
    query = models.Molt.query \
            .filter_by(deleted=False, is_reply=True) \
            .filter(models.Molt.original_molt.has(author=target_crab)) \
            .filter(models.Molt.author.has(banned=False, deleted=False)) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query



def get_molts_with_tag(crabtag: str, since: Optional[int] = None,
                       since_id: Optional[int] = None) \
        -> BaseQuery:
    """ Get Molts that use a specific Crabtag.
    """
    query = models.Molt.query \
            .filter_by(deleted=False) \
            .join(models.Molt.tags) \
            .filter(models.Crabtag.name == crabtag.lower()) \
            .filter(models.Molt.author.has(banned=False, deleted=False)) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query


def get_molts_from_crab(crab: 'models.Crab', since: Optional[int] = None,
                        since_id: Optional[int] = None) \
        -> BaseQuery:
    """ Get a Crab's Molts.
    """
    query = models.Molt.query \
            .filter_by(deleted=False, author=crab) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query


def get_timeline(crab: 'models.Crab', since: Optional[int] = None,
                 since_id: Optional[int] = None) \
        -> BaseQuery:
    """ Get a Crab's timeline.
    """
    following_ids = [following.id for following in crab.following]
    query = models.Molt.query \
            .filter_by(deleted=False, is_reply=False) \
            .filter(models.Molt.author.has(banned=False, deleted=False)) \
            .filter(or_(
                models.Molt.author.has(models.Crab.id.in_(following_ids)),
                models.Molt.author == crab
            )) \
            .order_by(models.Molt.timestamp.desc())
    if since:
        query = query.filter(models.Molt.timestamp > since)
    if since_id:
        query = query.filter(models.Molt.id > since_id)
    return query


def crab_to_json(crab: 'models.Crab', bio: bool = False) -> dict:
    """ Serialize a Crab object into a JSON-compatible dict.
    """
    crab_dict = {
        "id": crab.id,
        "display_name": crab.display_name,
        "username": crab.username,
        "verified": crab.verified,
        "avatar": absolute_url(crab.avatar),
        "followers": crab.follower_count,
        "following": crab.following_count,
        "register_time": get_timestamp(crab.register_time)
    }
    if bio:
        raw_bio = json.loads(crab.raw_bio)
        crab_bio = {
            "description": crab.description,
            "location": crab.location,
            **raw_bio
        }
        crab_dict['bio'] = crab_bio
    return crab_dict


def molt_to_json(molt: 'models.Molt') -> dict:
    """ Serialize a Molt object into a JSON-compatible dict.
    """
    molt_json = {
        "id": molt.id,
        "author": crab_to_json(molt.author),
        "content": molt.content,
        "crabtags": [tag.name for tag in molt.tags],
        "mentions": list(set(molt.raw_mentions.lower().splitlines())),
        "timestamp": get_timestamp(molt.timestamp),
        "edited": molt.edited,
        "quoted_molt": molt.original_molt_id if molt.is_quote else None,
        "replying_to": molt.original_molt_id if molt.is_reply else None,
        "image": absolute_url(molt.image),
        "likes": molt.like_count,
        "remolts": molt.remolt_count,
        "replies": molt.reply_count,
        "quotes": molt.quote_count
    }
    return molt_json


def query_to_json(query: BaseQuery, limit: int = 100, offset: int = 0) \
        -> dict:
    """ Serialize a list of objects into a JSON-compatible dict.
    """
    total_items = query.count()
    query = query.limit(limit).offset(offset)
    query_json = {
        "count": query.count(),
        "limit": limit,
        "offset": offset or 0,
        "total": total_items
    }

    for item in query.all():
        if isinstance(item, models.Molt):
            molt_list = query_json.get('molts', list())
            molt_list.append(molt_to_json(item))
            query_json['molts'] = molt_list
        elif isinstance(item, models.Bookmark):
            molt_list = query_json.get('molts', list())
            molt_list.append(molt_to_json(item.molt))
            query_json['molts'] = molt_list
        elif isinstance(item, models.Crab):
            crab_list = query_json.get('crabs', list())
            crab_list.append(crab_to_json(item))
            query_json['crabs'] = crab_list

    return query_json
