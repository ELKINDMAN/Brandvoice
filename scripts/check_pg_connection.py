#!/usr/bin/env python3
"""
Simple Postgres connection checker that reads connection info from .env
and attempts to open a SQLAlchemy connection. Git-bash friendly.

Usage:
  python scripts/check_pg_connection.py
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # allow building from individual parts
    user = os.getenv("PG_USER")
    password = os.getenv("PG_PASSWORD")
    host = os.getenv("PG_HOST")
    port = os.getenv("PG_PORT", "5432")
    db = os.getenv("PG_DB")
    if user and password and host and db:
        DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?sslmode=require"

if not DATABASE_URL:
    print("No DATABASE_URL or PG_* env vars found in .env. Please add them.")
    raise SystemExit(2)


def main():
    print(f"Testing connection to: {DATABASE_URL}")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            dialect = engine.dialect.name
            # Use a dialect-appropriate version query
            if dialect == 'sqlite':
                res = conn.execute(text("select sqlite_version()"))
                v = res.fetchone()
                print("Connected successfully — sqlite_version:", v[0])
            else:
                res = conn.execute(text("select version()"))
                v = res.fetchone()
                print("Connected successfully — server version:", v[0])
    except Exception as e:
        print("Failed to connect:", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
