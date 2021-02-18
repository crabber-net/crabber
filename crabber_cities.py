from config import *
from flask import abort, Blueprint, render_template
import models

cities = Blueprint('crabbycities', __name__)


@cities.route('/', subdomain='<username>')
def house(username):
    return f'You are viewing {username}\'s house on crabbycities.'


@cities.route('/', subdomain='cities')
def index():
    return 'Welcome to crabbycities! Make yourself at home.'

