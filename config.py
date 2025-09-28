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

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False
