from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Invoice, BusinessProfile, User, Payment
from .subscription import extend_premium, user_can_modify_invoices, needs_renewal_reminder, mark_reminder_sent
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
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).all()
    can_modify = current_user.access_active()
    return render_template('invoices_list.html', invoices=invoices, can_modify=can_modify)


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
    import requests

    # --- Currency & amount determination ---
    base_amount_usd = 4.99  # base reference price in USD

    def geo_country() -> str | None:
        """Attempt to detect 2-letter country code with primary + fallback provider."""
        # Respect X-Forwarded-For if behind proxy (take first IP)
        fwd = request.headers.get('X-Forwarded-For')
        if fwd:
            ip = fwd.split(',')[0].strip()
        else:
            ip = None  # public IP detection provider will infer
        try:
            resp = requests.get('https://ipapi.co/json/', timeout=4)
            if resp.ok:
                return resp.json().get('country_code')
        except Exception as e:
            current_app.logger.info('Primary geo provider failed: %s', e)
        # fallback
        try:
            resp2 = requests.get('https://ipwho.is/' + (ip or ''), timeout=4)
            if resp2.ok:
                data = resp2.json()
                if data.get('success') is not False:
                    return data.get('country_code') or data.get('country_code_iso2')
        except Exception as e2:
            current_app.logger.warning('Fallback geo provider failed: %s', e2)
        return None

    country = geo_country()
    detected_country = country  # keep for logging/diagnostics

    # Allow safe manual override via query (?currency=USD) restricted to whitelist
    override_currency = request.args.get('currency', '').upper().strip()
    allowed_currencies = {'USD', 'NGN', 'GBP'}
    if override_currency and override_currency not in allowed_currencies:
        flash('Unsupported currency override ignored.', 'warning')
        override_currency = ''

    if override_currency:
        currency = override_currency
    else:
        if country == 'NG':
            currency = 'NGN'
        elif country == 'GB':  # United Kingdom
            currency = 'GBP'
        elif country == 'US':
            currency = 'USD'
        else:
            # default to USD when unknown
            currency = 'USD'

    # Rough FX multipliers (TODO: replace with live FX service)
    if currency == 'NGN':
        amount = round(base_amount_usd * 1600, 2)
    elif currency == 'GBP':
        amount = round(base_amount_usd * 0.78, 2)
    else:  # USD
        amount = base_amount_usd

    # Plan mapping (recurring support if plan IDs present)
    plan_map = {
        'USD': current_app.config.get('FLW_PLAN_USD'),
        'NGN': current_app.config.get('FLW_PLAN_NGN'),
        'GBP': current_app.config.get('FLW_PLAN_GBP'),
    }
    plan_id = plan_map.get(currency)
    recurring = bool(plan_id)

    # Dynamic payment options
    if recurring:
        # Restrict to tokenizable methods only
        payment_options = 'card,applepay,googlepay'
    else:
        if currency == 'NGN':
            payment_options = 'card,banktransfer,ussd,account,qr,barter'
        else:
            payment_options = 'card,banktransfer,applepay,googlepay'

    requested_plan = (request.args.get('plan') or '').strip().lower() or None
    # tx_ref pattern: BV-{user_id}-{uuid}
    tx_ref = f"BV-{current_user.id}-{uuid.uuid4()}"
    flw = Flutterwave(secret, current_app.config.get('FLW_BASE_URL'))
    redirect_url = url_for('main.payment_callback', _external=True)
    canonical = current_app.config.get('CANONICAL_DOMAIN')
    if canonical:
        try:
            from urllib.parse import urlparse, urlunparse
            parts = urlparse(redirect_url)
            if parts.hostname in {'localhost', '127.0.0.1'} or (parts.hostname and parts.hostname.endswith('.onrender.com')):
                redirect_url = urlunparse((parts.scheme, canonical, parts.path, parts.params, parts.query, parts.fragment))
        except Exception as _e:  # noqa: BLE001
            current_app.logger.debug('Canonical redirect rewrite skipped: %s', _e)
    customer = {'email': current_user.email}

    current_app.logger.info('Initializing FLW payment tx_ref=%s currency=%s amount=%s country_detected=%s override=%s options=%s requested_plan=%s recurring=%s',
                            tx_ref, currency, amount, detected_country, bool(override_currency), payment_options, requested_plan, recurring)
    try:
        resp = flw.initialize_payment(
            tx_ref,
            f"{amount}",
            currency,
            redirect_url,
            customer,
            payment_options=payment_options,
            meta={
                'user_id': current_user.id,
                'detected_country': detected_country,
                'recurring': recurring,
                'requested_plan': requested_plan,
                'app_env': current_app.config.get('FLASK_ENV') or os.environ.get('FLASK_ENV'),
            },
            customizations={
                'title': 'BrandVoice Subscription',
                'description': 'Access full invoice experience',
                'logo': ''
            },
            payment_plan=str(plan_id) if plan_id else None,
        )
    except Exception as e:
        current_app.logger.exception('Flutterwave init failed for tx_ref=%s currency=%s amount=%s: %s', tx_ref, currency, amount, e)
        flash('Could not reach payment gateway. Please try again shortly.', 'error')
        return redirect(url_for('main.dashboard'))

    # Persist provisional payment record
    p = Payment(user_id=current_user.id, tx_ref=tx_ref, amount=amount, currency=currency, status='initiated')
    db.session.add(p)
    db.session.commit()

    data = resp.get('data') if isinstance(resp, dict) else None
    link = data.get('link') if data else None
    if not link:
        current_app.logger.error('Flutterwave response missing payment link. Raw=%s', resp)
        flash('Payment initialization failed (no link).', 'error')
        return redirect(url_for('main.dashboard'))
    return redirect(link)

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
        user = User.query.get(p.user_id)
        extend_premium(user, days=30)
        db.session.commit()
        flash('Subscription activated!', 'success')
        return redirect(url_for('main.dashboard'))
    else:
        p.status = 'failed'
        db.session.commit()
        flash('Payment not successful.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/webhook/flutterwave', methods=['POST'])
def flutterwave_webhook():
    from flask import jsonify
    data_raw = request.get_data(cache=False, as_text=True)
    sig = request.headers.get('verif-hash') or request.headers.get('Verif-Hash')
    expected = (current_app.config.get('FLW_HASH') or '').strip()
    if not expected:
        current_app.logger.error('Webhook received but FLW_HASH not set; rejecting for safety.')
        return jsonify({'status': 'misconfigured'}), 500
    if sig != expected:
        current_app.logger.warning('Rejected webhook invalid hash provided=%s', sig)
        return jsonify({'status': 'invalid hash'}), 401

    payload = request.get_json(silent=True) or {}
    event = payload.get('event') or payload.get('status')
    flw_data = payload.get('data') or {}
    tx_ref = flw_data.get('tx_ref') or flw_data.get('txRef')
    if not tx_ref:
        current_app.logger.info('Webhook missing tx_ref; event=%s raw=%s', event, data_raw[:300])
        return jsonify({'status': 'ignored'}), 200

    payment = Payment.query.filter_by(tx_ref=tx_ref).first()
    if not payment:
        current_app.logger.warning('Webhook for unknown tx_ref=%s; ignoring', tx_ref)
        return jsonify({'status': 'ignored'}), 200

    # Idempotency: if already successful & event signals success, short-circuit
    if payment.status == 'successful' and event in {'charge.completed', 'successful'}:
        return jsonify({'status': 'ok'}), 200

    # Verify transaction with Flutterwave (server-side) for integrity
    from .payments import Flutterwave
    secret = (current_app.config.get('FLW_SECRET_KEY') or '').strip()
    if not secret:
        current_app.logger.error('Missing FLW_SECRET_KEY during webhook verification.')
        return jsonify({'status': 'misconfigured'}), 500

    verifier = Flutterwave(secret, current_app.config.get('FLW_BASE_URL'))
    try:
        verify_resp = verifier.verify_transaction_by_ref(tx_ref)
    except Exception as e:
        current_app.logger.exception('Transaction verify failed tx_ref=%s: %s', tx_ref, e)
        return jsonify({'status': 'verify failed'}), 502

    vdata = (verify_resp or {}).get('data') or {}
    v_status = (vdata.get('status') or '').lower()
    v_amount = vdata.get('amount')
    v_currency = vdata.get('currency')

    # Basic consistency checks
    mismatch = []
    if v_currency and payment.currency and v_currency != payment.currency:
        mismatch.append('currency')
    if v_amount and payment.amount and float(v_amount) != float(payment.amount):
        mismatch.append('amount')
    if mismatch:
        current_app.logger.warning('Verify mismatch tx_ref=%s fields=%s v_currency=%s payment_currency=%s v_amount=%s payment_amount=%s',
                                   tx_ref, mismatch, v_currency, payment.currency, v_amount, payment.amount)
        return jsonify({'status': 'mismatch'}), 400

    if v_status == 'successful' and event in {'charge.completed', 'successful'}:
        user = User.query.get(payment.user_id)
        if payment.status != 'successful':
            payment.status = 'successful'
            plan_code = (vdata.get('payment_plan') or vdata.get('paymentplan') or
                         payload.get('payment_plan') or flw_data.get('payment_plan'))
            if plan_code:
                from .subscription import ensure_subscription
                ensure_subscription(user, str(plan_code), payment.currency, tx_ref, days=30)
            else:
                extend_premium(user, days=30)
            db.session.commit()
            current_app.logger.info('Premium extended via webhook verify user_id=%s tx_ref=%s plan=%s', user.id, tx_ref, plan_code)
        return jsonify({'status': 'ok'}), 200

    if v_status in {'failed', 'cancelled'} or event in {'charge.failed'}:
        payment.status = 'failed'
        db.session.commit()
        return jsonify({'status': 'not successful'}), 200

    # Unknown transitional state
    current_app.logger.info('Unhandled webhook state tx_ref=%s v_status=%s event=%s', tx_ref, v_status, event)
    return jsonify({'status': 'pending'}), 200

@main_bp.route('/jobs/daily')
def run_daily_jobs():
    # Simple unsecured endpoint (should protect with secret in production)
    from .models import User
    secret = request.args.get('secret')
    expected = current_app.config.get('CRON_SECRET')
    if expected and secret != expected:
        return 'Forbidden', 403
    now = datetime.utcnow()
    users = User.query.filter(User.is_premium == True).all()
    sent = 0
    from .utils_mail import safe_send_mail
    for u in users:
        if needs_renewal_reminder(u):
            body = 'Your BrandVoice subscription will expire in about 1 day. Renew now to avoid interruption.'
            ok = safe_send_mail('Your BrandVoice subscription expires soon', [u.email], body, category='renewal_reminder')
            if ok:
                mark_reminder_sent(u)
                sent += 1
            else:
                current_app.logger.warning('Queued (failed send) renewal reminder user_id=%s', u.id)
    db.session.commit()
    return f'OK sent={sent}'
