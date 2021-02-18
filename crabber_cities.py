from config import *
from flask import abort, Blueprint, redirect, render_template, request
import models
import utils

cities = Blueprint('crabbycities', __name__)


@cities.route('/<page>', subdomain='<username>')
@cities.route('/', subdomain='<username>')
def house(username, page='index'):
    crab = models.Crab.get_by_username(username)
    if crab:
        crab_house = models.CrabHouse.get(crab, create_if_none=False)
        if crab_house:
            return crab_house.get_page(page)
        else:
            return 'This user has not set up a CrabCities page.'
    else:
        return abort(404, 'Crab not found.')


@cities.route('/', subdomain='cities')
def index():
    current_user = utils.get_current_user()

    return render_template('cities-index.html')


@cities.route('/me', subdomain='cities')
def me():
    current_user = utils.get_current_user()
    return redirect(f'http://{current_user.username}.{DOMAIN}')


@cities.route('/edit', subdomain='cities', methods=('GET', 'POST'))
def edit():
    current_user = utils.get_current_user()
    crab_house = models.CrabHouse.get(current_user)
    page_name = request.args.get('page_name', 'index')

    # User is not logged in
    if current_user is None:
        return redirect(f'{BASE_URL}/login')

    if request.method == 'POST':
        action = request.form.get('user_action')

        if action == 'update_html':
            page_name = request.form.get('page')
            page_html = request.form.get('html')
            crab_house.update_page(page_name, page_html)
        elif action == 'delete_page':
            page_name = request.form.get('page')
            crab_house.delete_page(page_name)

            page_name = 'index'

        return redirect(f'/edit?page_name={page_name}')

    return render_template('cities-edit.html', house=crab_house,
                           page_name=page_name)
