from flask import Blueprint, render_template, request, url_for, current_app, redirect, flash
from flask_login import login_required, current_user
from .models import db, Invoice, BusinessProfile, InvoiceItem

main_generate_bp = Blueprint('generate', __name__)

@main_generate_bp.route('/generate', methods=['GET'])
@login_required
def generate_get():
    # Two-pane page with form (iframe) and live preview (iframe)
    profile = BusinessProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please create your Business Profile before creating invoices.', 'warning')
        return redirect(url_for('main.business_profile'))
    return render_template('generate_live.html')

@main_generate_bp.route('/generate/form', methods=['GET'])
@login_required
def generate_form():
    # Embedded form only (loaded inside the left iframe)
    profile = BusinessProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('main.business_profile'))
    return render_template('form.html')


@main_generate_bp.route('/generate', methods=['POST'])
@login_required
def generate_post():
    # from .utils import fmt_currency
    if request.method == 'POST':
        is_preview = (request.form.get('preview') == 'true')
        payment_instructions = request.form.get('payment_instructions')
        thanks_message = request.form.get('thank_you_note')
        template = request.form.get('template')

        client_name = request.form.get('client_name')
        client_contact = request.form.get('client_contact')

        # if not all([client_name, client_contact]):
        #     flash('Client Name and Contact are required.', 'error')
        #     return redirect(url_for('generate.generate_get'))

        # Load business profile for current user
        profile = BusinessProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            # If no profile, cannot proceed
            flash('Please create your Business Profile before creating invoices.', 'warning')
            return redirect(url_for('main.business_profile'))

        # Build items from form
        items = []
        index = 0
        while True:
            item_name = request.form.get(f'items[{index}][name]')
            item_price = request.form.get(f'items[{index}][price]')
            item_quantity = request.form.get(f'items[{index}][quantity]')
            item_subtotal = request.form.get(f'items[{index}][subtotal]')
            if not item_name:
                break
            items.append({
                'name': item_name,
                'price': float(item_price or 0),
                'quantity': int(item_quantity or 0),
                'subtotal': float(item_subtotal or 0),
            })
            index += 1

        # Logo comes from saved profile
        brand_logo_url = url_for('static', filename=profile.logo_path) if profile.logo_path else None

        # Ensure numeric values and recompute subtotal and total for safety
        for it in items:
            price = float(it.get('price') or 0)
            qty = int(it.get('quantity') or 0)
            it['subtotal'] = round(price * qty, 2)
            it['price'] = price
            it['quantity'] = qty
        total_amount = round(sum(i['subtotal'] for i in items), 2)

        # Auto-generate invoice number with first two letters of business name + zero-padded sequence
        import re
        name = (profile.business_name or '').strip()
        letters = re.sub(r'[^A-Za-z]', '', name).upper()
        prefix = (letters[:2] or 'IN')
        seq = Invoice.query.filter_by(user_id=current_user.id).count() + 1
        invoice_number = f"{prefix}{seq:04d}"

        # Determine template (validate against allowed set)
        allowed_templates = {
            "invoice_template_1.html", "invoice_template_2.html", "invoice_template_3.html",
            "invoice_template_4.html", "invoice_template_5.html", "invoice_template_6.html",
            "invoice_template_7.html"
        }
        chosen_template = template if template in allowed_templates else "invoice_template_1.html"

        # Save invoice meta to DB only if not a live preview (finalize)
        if not is_preview:
            inv = Invoice(
                user_id=current_user.id,
                invoice_number=invoice_number,
                client_name=client_name,
                client_contact=client_contact,
                payment_instructions=payment_instructions,
                thanks_message=thanks_message,
                total_amount=total_amount,
                template_name=chosen_template,
            )
            db.session.add(inv)
            db.session.flush()  # obtain inv.id
            # Persist line items
            for it in items:
                db.session.add(InvoiceItem(
                    invoice_id=inv.id,
                    name=it['name'],
                    price=it['price'],
                    quantity=it['quantity'],
                    subtotal=it['subtotal'],
                ))
            db.session.commit()

        html = render_template(
            chosen_template,
            business_name=profile.business_name,
            invoice_number=invoice_number,
            address=profile.address,
            phone=profile.phone,
            email=profile.email,
            brand_logo=brand_logo_url,
            payment_instructions=payment_instructions,
            thanks_message=thanks_message,
            client_name=client_name,
            client_contact=client_contact,
            items=items,
            total_amount=total_amount,
        )

        return html


@main_generate_bp.route('/invoices/<int:invoice_id>/print')
@login_required
def print_invoice(invoice_id: int):
    inv = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    profile = BusinessProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Missing Business Profile for this account.', 'warning')
        return redirect(url_for('main.dashboard'))

    items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
    brand_logo_url = url_for('static', filename=profile.logo_path) if profile.logo_path else None

    # Reconstruct items list shape expected by templates
    item_dicts = [{
        'name': it.name,
        'price': it.price,
        'quantity': it.quantity,
        'subtotal': it.subtotal,
    } for it in items]

    # Use stored template_name for print view (persisted when finalized)
    # Optional auto-print toggle via query param (?auto_print=1)
    auto_print = str(request.args.get('auto_print', '')).lower() in {'1', 'true', 'yes'}

    chosen_template = inv.template_name or 'invoice_template_1.html'
    html = render_template(
        chosen_template,
        business_name=profile.business_name,
        invoice_number=inv.invoice_number,
        address=profile.address,
        phone=profile.phone,
        email=profile.email,
        brand_logo=brand_logo_url,
        payment_instructions=inv.payment_instructions,
        thanks_message=inv.thanks_message,
        client_name=inv.client_name,
        client_contact=inv.client_contact,
        items=item_dicts,
        total_amount=inv.total_amount,
        auto_print=auto_print,
    )
    return html
