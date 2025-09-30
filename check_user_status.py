#!/usr/bin/env python
"""Quick helper script to inspect a user's premium/payment status.

Usage (PowerShell):
  python check_user_status.py --email codify12@gmail.com

Exits with code 0 if user exists, 1 if user not found.
"""
from __future__ import annotations
import sys
import argparse
import json
import os
from datetime import datetime

from app import create_app
from app.models import db, User, Payment, Subscription
from app.subscription import extend_premium
from app.payments import Flutterwave


def verify_and_repair_user(user: User, app) -> tuple[int, int]:
    """Verify any non-successful payments for the user against Flutterwave.

    Returns tuple: (repaired_count, newly_successful)
    """
    secret = (app.config.get('FLW_SECRET_KEY') or os.environ.get('FLW_SECRET_KEY') or '').strip()
    if not secret:
        print("[repair] Missing FLW_SECRET_KEY; cannot verify remotely.")
        return (0, 0)
    client = Flutterwave(secret, app.config.get('FLW_BASE_URL'))
    pending = Payment.query.filter(Payment.user_id == user.id, Payment.status.in_(['initiated','callback_received'])).all()
    repaired = 0
    newly_successful = 0
    for pay in pending:
        try:
            resp = client.verify_transaction_by_ref(pay.tx_ref)
        except Exception as e:  # noqa: BLE001
            print(f"[repair] verify failed tx_ref={pay.tx_ref} err={e}")
            continue
        data = (resp or {}).get('data') or {}
        v_status = (data.get('status') or '').lower()
        if v_status == 'successful':
            # Idempotent premium grant
            if pay.status != 'successful':
                pay.status = 'successful'
                pay.flw_transaction_id = str(data.get('id') or data.get('flw_ref') or '')
                from datetime import datetime as _dt
                pay.verified_at = _dt.utcnow()
                try:
                    pay.raw_meta = json.dumps({'verify': data})[:8000]
                except Exception:
                    pass
                extend_premium(user, days=30)
                newly_successful += 1
            repaired += 1
        elif v_status in {'failed','cancelled'}:
            if pay.status != 'failed':
                pay.status = 'failed'
                pay.failure_reason = data.get('processor_response') or data.get('narration') or 'failed'
                repaired += 1
        else:
            print(f"[repair] tx_ref={pay.tx_ref} still status={v_status or 'unknown'}")
    if repaired:
        db.session.commit()
    return (repaired, newly_successful)


def summarize_user(email: str, repair: bool = False, assume_yes: bool = False) -> int:
    app = create_app()
    with app.app_context():
        user: User | None = User.query.filter_by(email=email).first()
        if not user:
            print(f"User not found: {email}")
            return 1

        now = datetime.utcnow()
        premium_active = False
        reason = []

        if user.is_premium:
            if user.premium_expires_at is None or user.premium_expires_at > now:
                premium_active = True
                exp = user.premium_expires_at.isoformat() if user.premium_expires_at else 'never'
                reason.append(f"is_premium=True (expires {exp})")
            else:
                reason.append("is_premium flag set but expired")

        # Successful payments
        successful_payments = Payment.query.filter_by(user_id=user.id, status='successful').order_by(Payment.created_at.desc()).all()
        if successful_payments:
            latest_payment = successful_payments[0]
            reason.append(f"has {len(successful_payments)} successful payment(s); latest tx_ref={latest_payment.tx_ref} at {latest_payment.created_at.isoformat()}")
            if not premium_active and (user.premium_expires_at and user.premium_expires_at > now):
                premium_active = True

        # Subscription (if exists)
        active_subscription = Subscription.query.filter(Subscription.user_id == user.id, Subscription.status == 'active', Subscription.current_period_end > now).order_by(Subscription.current_period_end.desc()).first()
        if active_subscription:
            reason.append(f"active subscription plan_code={active_subscription.plan_code} until {active_subscription.current_period_end.isoformat()}")
            premium_active = True

        # Trial state
        trial_active = user.trial_active()
        if trial_active and not premium_active:
            reason.append("trial active")

        access_active = user.access_active()

        print("=== User Status ===")
        print(f"Email: {user.email}")
        print(f"User ID: {user.id}")
        print(f"Created: {user.created_at.isoformat()}")
        print(f"is_premium flag: {user.is_premium}")
        print(f"premium_expires_at: {user.premium_expires_at}")
        print(f"Trial start: {user.trial_start}")
        print(f"Trial active: {trial_active}")
        print(f"Premium active (computed): {premium_active}")
        print(f"Access active (trial or premium): {access_active}")
        print(f"Successful payments: {len(successful_payments)}")
        if successful_payments:
            for p in successful_payments[:5]:
                print(f"  - {p.tx_ref} {p.currency} {p.amount} status={p.status} created_at={p.created_at.isoformat()} verified_at={p.verified_at}")
        if active_subscription:
            print(f"Active subscription: plan_code={active_subscription.plan_code} period_end={active_subscription.current_period_end.isoformat()}")
        else:
            print("Active subscription: None")
        print("Reasons: ")
        for r in reason:
            print(f"  * {r}")

        if repair:
            # Only attempt repair if not already premium active
            needs = not premium_active
            if not needs:
                print("[repair] User already premium-active; skipping repair.")
            proceed = True
            if needs and not assume_yes:
                ans = input("Attempt remote verification & repair? [y/N]: ").strip().lower()
                proceed = ans == 'y'
            if needs and proceed:
                repaired, newly_successful = verify_and_repair_user(user, app)
                print(f"[repair] inspected pending payments: repaired={repaired} newly_successful={newly_successful}")
                # Recompute status after repair
                db.session.refresh(user)
                now2 = datetime.utcnow()
                still_premium = user.is_premium and (user.premium_expires_at is None or user.premium_expires_at > now2)
                print(f"[repair] post-repair premium_active={still_premium} premium_expires_at={user.premium_expires_at}")
        return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check a user's payment/premium status")
    parser.add_argument('--email', required=True, help='Email address to check')
    parser.add_argument('--repair', action='store_true', help='Attempt remote verification & premium repair for pending payments')
    parser.add_argument('--yes', action='store_true', help='Assume yes to prompts (non-interactive)')
    args = parser.parse_args(argv)
    return summarize_user(args.email, repair=args.repair, assume_yes=args.yes)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
