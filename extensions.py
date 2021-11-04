import config
from crab_mail import CrabMail
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

if config.MAIL_ENABLED:
    mail = CrabMail(config.MAIL_ADDRESS, config.MAIL_PASSWORD)
else:
    mail = None
