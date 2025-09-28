from datetime import datetime, timedelta
from flask import current_app
from .models import db, Subscription


def user_can_modify_invoices(user) -> bool:
    """Returns True if the user is allowed to create/print invoices (trial active or premium active)."""
    if not user:
        return False
    return user.access_active()


def extend_premium(user, days: int = 30):
    """Extend premium for user. If already has future expiry, extend from that date; else from now."""
    now = datetime.utcnow()
    base = user.premium_expires_at if user.premium_expires_at and user.premium_expires_at > now else now
    user.is_premium = True
    user.premium_expires_at = base + timedelta(days=days)
    current_app.logger.info('Extended premium user_id=%s new_expiry=%s', user.id, user.premium_expires_at.isoformat())


def needs_renewal_reminder(user) -> bool:
    """Return True if user should receive a day-before-expiry reminder."""
    if not user.is_premium or not user.premium_expires_at:
        return False
    now = datetime.utcnow()
    delta = user.premium_expires_at - now
    # Between 24h and <48h away from expiry (simple threshold) and not already sent today
    if 0 < delta.total_seconds() <= 86400 * 1.05:  # allow slight drift
        if not user.last_renewal_reminder_sent_at:
            return True
        # Avoid duplicate sends within same calendar day
        if user.last_renewal_reminder_sent_at.date() != now.date():
            return True
    return False


def mark_reminder_sent(user):
    user.last_renewal_reminder_sent_at = datetime.utcnow()


def ensure_subscription(user, plan_code: str, currency: str, tx_ref: str, days: int = 30):
    """Create or extend a subscription record for a recurring plan.

    If an active subscription with same plan exists, extend its period.
    Otherwise create new subscription row. Also extends user's premium window.
    """
    now = datetime.utcnow()
    sub = Subscription.query.filter_by(user_id=user.id, plan_code=plan_code, status='active').first()
    if sub and sub.current_period_end > now:
        base = sub.current_period_end
        sub.current_period_end = base + timedelta(days=days)
        sub.last_tx_ref = tx_ref
    else:
        period_end = now + timedelta(days=days)
        sub = Subscription(
            user_id=user.id,
            plan_code=plan_code,
            currency=currency,
            status='active',
            current_period_start=now,
            current_period_end=period_end,
            last_tx_ref=tx_ref,
        )
        db.session.add(sub)
    # Align user premium window
    from .subscription import extend_premium  # local import to avoid circular
    extend_premium(user, days=days)
    current_app.logger.info('ensure_subscription user_id=%s plan=%s new_period_end=%s', user.id, plan_code, sub.current_period_end.isoformat())
