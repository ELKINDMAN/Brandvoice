from datetime import datetime, timedelta
from flask import current_app


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
