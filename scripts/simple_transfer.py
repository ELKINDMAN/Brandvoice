#!/usr/bin/env python3
"""
Simple SQLite -> PostgreSQL transfer script that handles duplicates via try/catch.
Faster and more robust than checking existence before each insert.

Usage:
  python scripts/simple_transfer.py --dry-run
  python scripts/simple_transfer.py
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
import argparse

load_dotenv()

DEFAULT_SQLITE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'brandvoice.db'))
SQLITE_URL = os.getenv('SQLITE_URL', f'sqlite:///{DEFAULT_SQLITE}')
PG_URL = os.getenv('DATABASE_URL')

parser = argparse.ArgumentParser(description='Simple transfer from SQLite to Postgres')
parser.add_argument('--dry-run', action='store_true', help='Just show counts, do not transfer')
args = parser.parse_args()

def main():
    if not PG_URL:
        print('No DATABASE_URL in .env')
        return

    # Table order: parents first, children second
    table_order = ['user', 'business_profile', 'invoice', 'invoice_item', 'payment', 'subscription', 'webhook_log', 'payment_callback_log', 'failed_email']
    
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(PG_URL)

    # Get table metadata
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)
    
    pg_meta = MetaData() 
    pg_meta.reflect(bind=pg_engine)

    total_transferred = 0

    for table_name in table_order:
        if table_name not in sqlite_meta.tables:
            continue
        if table_name not in pg_meta.tables:
            print(f"Skipping {table_name} - not in PostgreSQL")
            continue

        sqlite_table = sqlite_meta.tables[table_name]
        pg_table = pg_meta.tables[table_name]
        
        # Count source rows
        with sqlite_engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        
        print(f"{table_name}: {count} rows in source")
        
        if args.dry_run or count == 0:
            continue

        # Transfer all rows in one batch
        with sqlite_engine.connect() as s_conn:
            rows = s_conn.execute(text(f"SELECT * FROM {table_name}")).fetchall()
        
        if not rows:
            continue

        # Convert to list of dicts
        column_names = [col.name for col in sqlite_table.columns]
        data = []
        for row in rows:
            row_dict = dict(zip(column_names, row))
            data.append(row_dict)

        # Insert into PostgreSQL, ignoring duplicates
        inserted = 0
        skipped = 0
        
        for row_data in data:
            try:
                with pg_engine.begin() as pg_conn:
                    pg_conn.execute(pg_table.insert(), row_data)
                inserted += 1
            except IntegrityError:
                skipped += 1  # Duplicate or constraint violation
            except Exception as e:
                print(f"Error inserting into {table_name}: {e}")
                skipped += 1

        print(f"  -> Inserted: {inserted}, Skipped: {skipped}")
        total_transferred += inserted

        # Fix sequence if the table has an id column
        if 'id' in column_names:
            try:
                with pg_engine.begin() as pg_conn:
                    pg_conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), (SELECT COALESCE(MAX(id),0) FROM {table_name}))"))
                print(f"  -> Fixed sequence for {table_name}")
            except Exception as e:
                print(f"  -> Could not fix sequence for {table_name}: {e}")

    print(f"\nTotal transferred: {total_transferred} rows")

if __name__ == '__main__':
    main()