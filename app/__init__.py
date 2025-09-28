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
    # Mail configuration (Live Mailtrap SMTP as requested)
    # Overriding any prior defaults explicitly
    app.config['MAIL_SERVER'] = 'live.smtp.mailtrap.io'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'api'
    # Mail password pulled from environment (.env) for safety
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    # Keep existing default sender env override if present, else fallback
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('APP_EMAIL', 'no-reply@example.com')
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
