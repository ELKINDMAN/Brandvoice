from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Invoice, BusinessProfile
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
    return render_template('dashboard.html', user=current_user, profile=profile)

@main_bp.route('/invoices')
@login_required
def invoices_list():
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
