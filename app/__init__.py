from flask import Flask
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .models import db
from datetime import timedelta

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_object='config.DevConfig'):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)
    # Session / remember configuration
    app.config.setdefault('REMEMBER_COOKIE_DURATION', timedelta(days=1))

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)
    # Canonical application domain for external links / absolute URLs
    app.config.setdefault('CANONICAL_DOMAIN', 'brandvoice.live')
    # Default sender config (used by Mailtrap API helper)
    app.config.setdefault('MAIL_DEFAULT_SENDER', ("BrandVoice Support", "support@brandvoice.live"))

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
