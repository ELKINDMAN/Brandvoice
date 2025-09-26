from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Invoice, BusinessProfile, User, Payment
from datetime import datetime, timedelta
import uuid
from werkzeug.utils import secure_filename
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    profile = BusinessProfile.query.filter_by(user_id=current_user.id).first()
    trial_active = current_user.trial_active() if hasattr(current_user, 'trial_active') else False
    access_active = current_user.access_active() if hasattr(current_user, 'access_active') else False
    days_left = None
    if current_user.trial_start and not current_user.is_premium:
        from datetime import datetime as _dt, timedelta as _td
        end = current_user.trial_start + _td(days=7)
        remaining = (end - _dt.utcnow()).days
        days_left = remaining if remaining > 0 else 0
    return render_template(
        'dashboard.html',
        user=current_user,
        profile=profile,
        trial_active=trial_active,
        access_active=access_active,
        days_left=days_left,
    )

@main_bp.route('/invoices')
@login_required
def invoices_list():
    # Gate access if neither trial nor premium
    if not current_user.access_active():
        flash('Your trial has expired. Please subscribe to continue.', 'warning')
        return redirect(url_for('main.subscribe_pay'))
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).all()
    return render_template('invoices_list.html', invoices=invoices)


@main_bp.route('/business-profile', methods=['GET', 'POST'])
@login_required
def business_profile():
    profile = BusinessProfile.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        business_name = request.form.get('business_name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        email = request.form.get('email')
        logo_file = request.files.get('logo')

        logo_path_rel = profile.logo_path if profile else None
        if logo_file and logo_file.filename:
            uploads_dir = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            fname = secure_filename(logo_file.filename)
            save_path = os.path.join(uploads_dir, fname)
            logo_file.save(save_path)
            logo_path_rel = f'uploads/{fname}'

        if not profile:
            profile = BusinessProfile(
                user_id=current_user.id,
                business_name=business_name,
                address=address,
                phone=phone,
                email=email,
                logo_path=logo_path_rel,
            )
            db.session.add(profile)
        else:
            profile.business_name = business_name
            profile.address = address
            profile.phone = phone
            profile.email = email
            profile.logo_path = logo_path_rel

        db.session.commit()
        flash('Business profile saved.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('business_profile.html', profile=profile)


@main_bp.route('/subscribe/pay')
@login_required
def subscribe_pay():
    if current_user.is_premium:
        return redirect(url_for('main.dashboard'))
    from .payments import Flutterwave
    secret = (current_app.config.get('FLW_SECRET_KEY') or '').strip()
    # Defensive validation & logging
    def _mask(k: str):
        if not k:
            return 'EMPTY'
        if len(k) <= 8:
            return '****'
        return k[:6] + '...' + k[-4:]
    if not secret or secret.lower() in {'changeme','none'}:
        current_app.logger.error('Flutterwave key missing or placeholder. Value=%s', _mask(secret))
        flash('Payment gateway not configured.', 'error')
        return redirect(url_for('main.dashboard'))
    if not secret.startswith('FLWSECK_'):
        current_app.logger.warning('FLW secret does not start with expected prefix; proceeding anyway. Masked=%s', _mask(secret))

    base_amount_usd = 4.99  # fixed price reference
    import requests
    country = None
    try:
        ip_resp = requests.get('https://ipapi.co/json/', timeout=5)
        if ip_resp.ok:
            country = ip_resp.json().get('country_code')
    except Exception as e:
        current_app.logger.warning(f'Geo IP lookup failed: {e}')

    currency = 'USD'
    amount = base_amount_usd
    if country == 'NG':
        currency = 'NGN'
        amount = round(base_amount_usd * 1600, 2)
    elif country == 'GB':
        currency = 'GBP'
        amount = round(base_amount_usd * 0.78, 2)
    elif country == 'US':
        currency = 'USD'
        amount = base_amount_usd

    tx_ref = str(uuid.uuid4())
    flw = Flutterwave(secret)
    redirect_url = url_for('main.payment_callback', _external=True)
    customer = {'email': current_user.email}
    payment_options = 'card,banktransfer,applepay,googlepay'
    try:
        resp = flw.initialize_payment(
            tx_ref,
            f"{amount}",
            currency,
            redirect_url,
            customer,
            payment_options=payment_options,
            meta={'user_id': current_user.id},
            customizations={'title': 'BrandVoice Subscription', 'description': 'Access full invoice experience'}
        )
    except Exception as e:
        current_app.logger.exception('Flutterwave init failed for tx_ref=%s currency=%s amount=%s: %s', tx_ref, currency, amount, e)
        flash('Could not reach payment gateway. Please try again shortly.', 'error')
        return redirect(url_for('main.dashboard'))
    p = Payment(user_id=current_user.id, tx_ref=tx_ref, amount=amount, currency=currency)
    db.session.add(p)
    db.session.commit()
    data = resp.get('data') if isinstance(resp, dict) else None
    link = data.get('link') if data else None
    if not link:
        current_app.logger.error('Flutterwave response missing payment link. Raw=%s', resp)
        flash('Payment initialization failed (no link).', 'error')
        return redirect(url_for('main.dashboard'))
    if link:
        return redirect(link)
    flash('Failed to start payment', 'error')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/payment/callback')
def payment_callback():
    tx_ref = request.args.get('tx_ref') or request.args.get('txRef')
    status = request.args.get('status')
    if not tx_ref:
        flash('Missing transaction reference.', 'error')
        return redirect(url_for('main.dashboard'))
    p = Payment.query.filter_by(tx_ref=tx_ref).first()
    if not p:
        flash('Unknown transaction.', 'error')
        return redirect(url_for('main.dashboard'))
    if status == 'successful':
        p.status = 'successful'
        # Grant premium 30 days for now
        user = User.query.get(p.user_id)
        user.is_premium = True
        user.premium_expires_at = datetime.utcnow() + (datetime.utcnow() - datetime.utcnow())  # placeholder; extend below
        # Simple extend 30 days
        user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        flash('Subscription activated!', 'success')
        return redirect(url_for('main.dashboard'))
    else:
        p.status = 'failed'
        db.session.commit()
        flash('Payment not successful.', 'error')
        return redirect(url_for('main.dashboard'))
