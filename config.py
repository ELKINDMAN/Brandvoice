import os
from dotenv import load_dotenv

# Load .env at config import time (safe for dev/local)
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///brandvoice.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Payment keys (set via env in production)
    PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
    FLW_SECRET_KEY = os.environ.get("FLW_SECRET_KEY")
    FLW_HASH = os.environ.get("FLW_HASH")  # webhook verification hash
    # Base URL (allow override for sandbox if needed)
    FLW_BASE_URL = os.environ.get("FLW_BASE_URL", "https://api.flutterwave.com/v3")
    # Optional recurring plan IDs by currency (Flutterwave payment_plan IDs)
    FLW_PLAN_USD = os.environ.get("FLW_PLAN_USD")
    FLW_PLAN_NGN = os.environ.get("FLW_PLAN_NGN")
    FLW_PLAN_GBP = os.environ.get("FLW_PLAN_GBP")
    CRON_SECRET = os.environ.get("CRON_SECRET")

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False
