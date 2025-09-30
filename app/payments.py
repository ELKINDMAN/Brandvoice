# Payment integration stubs for Paystack and Flutterwave
# Fill in with real API calls later.

import os
import requests

class Paystack:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.base_url = 'https://api.paystack.co'

    def initialize_transaction(self, email: str, amount_kobo: int, callback_url: str):
        url = f'{self.base_url}/transaction/initialize'
        headers = {'Authorization': f'Bearer {self.secret_key}', 'Content-Type': 'application/json'}
        payload = { 'email': email, 'amount': amount_kobo, 'callback_url': callback_url }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

class Flutterwave:
    def __init__(self, secret_key: str, base_url: str | None = None):
        self.secret_key = secret_key
        # Allow caller to inject base_url (fallback to env-configured default)
        self.base_url = base_url or 'https://api.flutterwave.com/v3'

    def initialize_payment(
        self,
        tx_ref: str,
        amount: str,
        currency: str,
        redirect_url: str,
        customer: dict,
        payment_options: str = None,
        meta: dict | None = None,
        customizations: dict | None = None,
    ):
        url = f'{self.base_url}/payments'
        headers = {'Authorization': f'Bearer {self.secret_key}', 'Content-Type': 'application/json'}
        payload = {
            'tx_ref': tx_ref,
            'amount': amount,
            'currency': currency,
            'redirect_url': redirect_url,
            'customer': customer,
        }
        if payment_options:
            payload['payment_options'] = payment_options  # e.g. "card,banktransfer,applepay,googlepay"
        if meta:
            payload['meta'] = meta
        if customizations:
            payload['customizations'] = customizations
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def verify_transaction_by_ref(self, tx_ref: str):
        """Verify a transaction by reference (server-side integrity check)."""
        url = f'{self.base_url}/transactions/verify_by_reference'
        headers = {'Authorization': f'Bearer {self.secret_key}'}
        params = {'tx_ref': tx_ref}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
