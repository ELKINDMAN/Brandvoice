from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import secrets
from .__init__ import mail
from flask_mail import Message

# NOTE: Email sending (password reset) uses the Gmail SMTP configuration defined
# in create_app within app.__init__.py. Ensure GMAIL_ADDRESS and GMAIL_APP_PASSWORD
# environment variables are set before triggering password reset.

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            # Redirect to dashboard (no forced payment)
            return redirect(url_for('main.dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
        else:
            user = User(email=email, password_hash=generate_password_hash(password), trial_start=datetime.utcnow())
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            # Show welcome modal once via query flag
            return redirect(url_for('main.dashboard', welcome=1))
    return render_template('register.html')


RESET_EXP_MINUTES = 30

@auth_bp.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            # NOTE: Current message still discloses invalid vs valid and can enable enumeration.
            # Consider switching to a generic success message always.
            current_app.logger.info('Password reset requested for non-existent email=%s', email)
            flash('Invalid email address.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        token = secrets.token_urlsafe(48)
        user.password_reset_token = token
        user.password_reset_sent_at = datetime.utcnow()
        db.session.commit()
        reset_link = url_for('auth.reset_password', token=token, _external=True)
        canonical = current_app.config.get('CANONICAL_DOMAIN')
        if canonical:
            # Replace netloc if running in an internal environment (heuristic: localhost or 127).* 
            try:
                from urllib.parse import urlparse, urlunparse
                parts = urlparse(reset_link)
                if parts.hostname in {'localhost', '127.0.0.1'} or parts.hostname.endswith('.onrender.com'):
                    reset_link = urlunparse((parts.scheme, canonical, parts.path, parts.params, parts.query, parts.fragment))
            except Exception as _e:  # noqa: BLE001
                current_app.logger.debug('Canonical URL rewrite skipped: %s', _e)
        # Pre-flight mail configuration sanity logging (masked where appropriate)
        mail_cfg = {
            'server': current_app.config.get('MAIL_SERVER'),
            'port': current_app.config.get('MAIL_PORT'),
            'use_tls': current_app.config.get('MAIL_USE_TLS'),
            'use_ssl': current_app.config.get('MAIL_USE_SSL'),
            'username_present': bool(current_app.config.get('MAIL_USERNAME')),
            'password_present': bool(current_app.config.get('MAIL_PASSWORD')),
            'default_sender': current_app.config.get('MAIL_DEFAULT_SENDER'),
        }
        current_app.logger.info('Initiating password reset email user_id=%s email=%s mail_cfg=%s token_prefix=%s',
                                user.id, email, mail_cfg, token[:8])
        try:
            msg = Message(
                subject='Password Reset Request',
                recipients=[email],
                body=f'Click the link to reset your password (expires in {RESET_EXP_MINUTES} minutes): {reset_link}'
            )
            if current_app.config.get('MAIL_DEFAULT_SENDER'):
                msg.sender = current_app.config['MAIL_DEFAULT_SENDER']
            mail.send(msg)
            current_app.logger.info('Password reset email dispatched user_id=%s tx_token_prefix=%s', user.id, token[:8])
        except Exception as e:
            # Keep token (user can retry later); log full exception stack
            current_app.logger.exception('Mail send failed for user_id=%s email=%s: %s', user.id, email, e)
        flash('Password reset link has been sent to email. Check your email.', 'info')
        return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(password_reset_token=token).first()
    if not user:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))
    # Expire after RESET_EXP_MINUTES
    if user.password_reset_sent_at and datetime.utcnow() - user.password_reset_sent_at > timedelta(minutes=RESET_EXP_MINUTES):
        flash('Reset link expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        pw1 = request.form.get('password')
        pw2 = request.form.get('password_confirm')
        if not pw1 or pw1 != pw2:
            flash('Passwords do not match.', 'error')
        else:
            user.password_hash = generate_password_hash(pw1)
            user.password_reset_token = None
            user.password_reset_sent_at = None
            db.session.commit()
            flash('Password updated. You can now login.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('reset_password.html', token=token)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
