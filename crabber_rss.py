import api_utils
from config import *
from flask import abort, Blueprint, render_template, Response
import models

RSS = Blueprint('RSS Feeds', __name__)


@RSS.route('/')
def root():
    return render_template('rss_index.html')


@RSS.route('/user/<username>/')
def get_crab(username):
    crab = api_utils.get_crab_by_username(username)
    if crab:
        molts = crab.query_molts().filter_by(is_reply=False, is_remolt=False) \
            .limit(RSS_MOLT_LIMIT)
        xml = render_template('rss_user_page.xml', crab=crab, molts=molts)
        return Response(xml, mimetype='text/xml')
    else:
        return abort(404, description='No Crab with that username.')


@RSS.route('/crabtag/<tagname>/')
def get_crabtag(tagname):
    crabtag = models.Crabtag.get(tagname)
    if crabtag:
        molts = crabtag.query_molts().limit(RSS_MOLT_LIMIT)
    else:
        molts = []
    xml = render_template('rss_crabtag.xml', molts=molts, crabtag=tagname)
    return Response(xml, mimetype='text/xml')


@RSS.route('/timeline/<username>/')
def get_timeline(username):
    crab = api_utils.get_crab_by_username(username)
    if crab:
        molts = crab.query_timeline().limit(RSS_MOLT_LIMIT)
        xml = render_template('rss_user_timeline.xml', crab=crab, molts=molts)
        return Response(xml, mimetype='text/xml')
    else:
        return abort(404, description='No Crab with that username.')
