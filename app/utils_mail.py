import os
import socket
from typing import List, Optional
from flask import current_app
from .models import db, FailedEmail
import mailtrap as mt
from datetime import datetime

# Network level errors we want to catch distinctly
NETWORK_ERRORS = (socket.gaierror, OSError)

class MailtrapEmailClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('MAILTRAP_API_KEY')
        self._client = None
        if self.token:
            try:
                self._client = mt.MailtrapClient(token=self.token)
            except Exception as e:  # noqa: BLE001
                current_app.logger.error('Failed to initialize Mailtrap client: %s', e)
        else:
            current_app.logger.warning('MAILTRAP_API_KEY not set; email sending disabled.')

    def send(self, subject: str, recipients: List[str], text: str, category: str = 'transactional', sender_name: str = 'BrandVoice Support'):  # noqa: D401
        current_app.logger.info('Email attempt subject=%s to=%s category=%s', subject, ','.join(recipients), category)
        if not self._client:
            current_app.logger.warning('Mailtrap client not available; queuing email.')
            _persist_failed(subject, recipients, text, 'client_not_initialized')
            return False
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER')
        # MAIL_DEFAULT_SENDER may be tuple or string
        if isinstance(sender_email, (list, tuple)):
            email_addr = sender_email[1]
            name = sender_email[0]
        else:
            email_addr = sender_email or 'support@brandvoice.live'
            name = sender_name
        try:
            mail = mt.Mail(
                sender=mt.Address(email=email_addr, name=name),
                to=[mt.Address(email=r) for r in recipients],
                subject=subject,
                text=text,
                category=category,
            )
            resp = self._client.send(mail)
            current_app.logger.info('Email success subject=%s to=%s resp_id=%s', subject, ','.join(recipients), getattr(resp, 'message_ids', None))
            return True
        except NETWORK_ERRORS as e:
            current_app.logger.error('Email network error subject=%s to=%s err=%s', subject, ','.join(recipients), e)
            _persist_failed(subject, recipients, text, str(e))
        except Exception as e:  # noqa: BLE001
            current_app.logger.exception('Email general failure subject=%s to=%s', subject, ','.join(recipients))
            _persist_failed(subject, recipients, text, str(e))
        return False

def _persist_failed(subject: str, recipients: List[str], body: str, error: str):
    from .models import FailedEmail
    for r in recipients:
        fe = FailedEmail(
            to_address=r,
            subject=subject,
            body=body,
            error=error,
        )
        db.session.add(fe)
    try:
        db.session.commit()
    except Exception as commit_err:  # noqa: BLE001
        current_app.logger.error('Failed to commit FailedEmail records: %s', commit_err)
        db.session.rollback()

def retry_failed_emails(limit: int = 20):
    q = FailedEmail.query.order_by(FailedEmail.last_attempt_at.asc()).limit(limit).all()
    if not q:
        return 0
    client = MailtrapEmailClient()
    sent = 0
    for fe in q:
        fe.retry_count += 1
        fe.last_attempt_at = datetime.utcnow()
        try:
            ok = client.send(fe.subject, [fe.to_address], fe.body)
            if ok:
                current_app.logger.info('FailedEmail retry success id=%s to=%s subject=%s attempts=%s', fe.id, fe.to_address, fe.subject, fe.retry_count)
                db.session.delete(fe)
                sent += 1
            else:
                current_app.logger.warning('FailedEmail retry still failing id=%s to=%s subject=%s attempts=%s', fe.id, fe.to_address, fe.subject, fe.retry_count)
        except Exception as e:  # noqa: BLE001
            fe.error = str(e)
            current_app.logger.exception('FailedEmail retry exception id=%s to=%s subject=%s', fe.id, fe.to_address, fe.subject)
    db.session.commit()
    return sent

# Convenience singleton accessor
_client_singleton: Optional[MailtrapEmailClient] = None

def get_mail_client() -> MailtrapEmailClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = MailtrapEmailClient()
    return _client_singleton


def safe_send_mail(subject: str, recipients: List[str], body: str, category: str = 'transactional'):
    client = get_mail_client()
    ok = client.send(subject, recipients, body, category=category)
    if ok:
        current_app.logger.info('safe_send_mail dispatched subject=%s to=%s category=%s', subject, ','.join(recipients), category)
    else:
        current_app.logger.warning('safe_send_mail failed/queued subject=%s to=%s category=%s', subject, ','.join(recipients), category)
    return ok
