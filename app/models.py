from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Trial & subscription fields
    trial_start = db.Column(db.DateTime)  # set at registration
    is_premium = db.Column(db.Boolean, default=False)
    premium_expires_at = db.Column(db.DateTime)
    # Renewal reminder tracking (when last 1-day-before-expiry reminder was sent)
    last_renewal_reminder_sent_at = db.Column(db.DateTime)
    # Password reset fields
    password_reset_token = db.Column(db.String(255))
    password_reset_sent_at = db.Column(db.DateTime)
    business_profile = db.relationship('BusinessProfile', backref='owner', uselist=False)
    invoices = db.relationship('Invoice', backref='user', lazy=True)

    def trial_active(self) -> bool:
        if self.is_premium:
            return False  # premium overrides trial display
        if not self.trial_start:
            return False
        return datetime.utcnow() < self.trial_start + timedelta(days=7)

    def access_active(self) -> bool:
        # Either within trial or premium active
        if self.is_premium:
            if self.premium_expires_at is None:
                return True
            return datetime.utcnow() < self.premium_expires_at
        return self.trial_active()

class BusinessProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_name = db.Column(db.String(255))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    logo_path = db.Column(db.String(255))

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invoice_number = db.Column(db.String(100), nullable=False)
    client_name = db.Column(db.String(255))
    client_contact = db.Column(db.String(255))
    payment_instructions = db.Column(db.Text)
    thanks_message = db.Column(db.Text)
    total_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    template_name = db.Column(db.String(100), default='invoice_template_1.html')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tx_ref = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(50), default='initialized')  # initialized, successful, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_code = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(50), default='active')  # active, cancelled, expired
    current_period_start = db.Column(db.DateTime, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime, nullable=False)
    last_tx_ref = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_active(self):
        return self.status == 'active' and datetime.utcnow() < self.current_period_end

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    name = db.Column(db.String(255))
    price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, default=1)
    subtotal = db.Column(db.Float, default=0.0)
