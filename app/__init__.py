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
    # Legacy Mailtrap configuration (commented out for reference only)
    # Keeping this block so we can easily revert if needed.
    # ------------------------------------------------------------------
    # app.config['MAIL_SERVER'] = 'live.smtp.mailtrap.io'
    # app.config['MAIL_PORT'] = 587
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USE_SSL'] = False
    # app.config['MAIL_USERNAME'] = 'api'
    # app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    # app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('APP_EMAIL', 'no-reply@example.com')

    # ------------------------------------------------------------------
    # Temporary Gmail SMTP configuration
    # NOTE: Requires you to create a Google App Password (not your normal
    # Gmail password). Set env vars GMAIL_ADDRESS and GMAIL_APP_PASSWORD.
    # ------------------------------------------------------------------
    gmail_address = os.environ.get('GMAIL_ADDRESS')
    gmail_app_password = os.environ.get('GMAIL_APP_PASSWORD')
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = gmail_address
    app.config['MAIL_PASSWORD'] = gmail_app_password
    app.config['MAIL_DEFAULT_SENDER'] = gmail_address or os.environ.get('APP_EMAIL', 'no-reply@example.com')
    if not gmail_address or not gmail_app_password:
        app.logger.warning('Gmail SMTP not fully configured: missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD environment variable.')
    # ------------------------------------------------------------------
    # End Gmail SMTP configuration
    # ------------------------------------------------------------------
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
