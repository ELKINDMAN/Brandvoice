from flask import Flask
import os
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .models import db
from datetime import timedelta

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
mail = Mail()

def create_app(config_object='config.DevConfig'):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)
    # Session / remember configuration
    app.config.setdefault('REMEMBER_COOKIE_DURATION', timedelta(days=1))

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)
    # ------------------------------------------------------------------
    # Mailtrap SMTP configuration (preferred for staging / dev)
    # ------------------------------------------------------------------
    mail_username = os.environ.get('MAIL_USERNAME') or 'api'
    mail_password = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_SERVER'] = 'live.smtp.mailtrap.io'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = mail_username
    app.config['MAIL_PASSWORD'] = mail_password
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('APP_EMAIL', 'no-reply@brandvoice.live')
    if not mail_password:
        app.logger.warning('Mailtrap SMTP not fully configured: missing MAIL_PASSWORD env var.')
    # ------------------------------------------------------------------
    # Gmail block retained for reference (now disabled)
    # ------------------------------------------------------------------
    # gmail_address = os.environ.get('GMAIL_ADDRESS')
    # gmail_app_password = os.environ.get('GMAIL_APP_PASSWORD')
    # if gmail_address and gmail_app_password:
    #     app.logger.info('Gmail credentials detected but Mailtrap is active; comment Mailtrap block to switch.')

    # Canonical application domain for external links / absolute URLs
    app.config.setdefault('CANONICAL_DOMAIN', 'brandvoice.live')
    mail.init_app(app)

    # Register blueprints
    from .auth import auth_bp
    from .routes import main_bp
    from .routes_generate import main_generate_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(main_generate_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
