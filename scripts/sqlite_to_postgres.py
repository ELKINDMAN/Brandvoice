#!/usr/bin/env python3
"""
Resumable SQLite -> PostgreSQL transfer script.

Usage examples (git-bash):
  # dry-run 10 rows
  python scripts/sqlite_to_postgres.py --dry-run --limit 10

  # actual run
  python scripts/sqlite_to_postgres.py

This script will attempt to import rows table-by-table using SQLAlchemy Core for portability.
It prefers to use your app models if available (imports `app.models`), but will fall back to
reflecting table metadata when necessary.

It is intentionally conservative: it checks for existing primary keys and skips inserts that
would collide. It also runs `setval` on sequences where appropriate.
"""
from sqlalchemy import create_engine, MetaData, Table, select, insert, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
import argparse
import sys
import time

load_dotenv()

DEFAULT_SQLITE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'brandvoice.db'))
SQLITE_URL = os.getenv('SQLITE_URL', f'sqlite:///{DEFAULT_SQLITE}')
PG_URL = os.getenv('DATABASE_URL')

parser = argparse.ArgumentParser(description='Transfer data from SQLite to Postgres')
parser.add_argument('--sqlite', default=SQLITE_URL, help='SQLite URL (file:// or sqlite:///path)')
parser.add_argument('--pg', default=PG_URL, help='Postgres SQLAlchemy URL (postgresql+psycopg2://...)')
parser.add_argument('--dry-run', action='store_true', help='Do not perform inserts; only show counts')
parser.add_argument('--limit', type=int, default=0, help='Limit rows per table (0 = no limit)')
parser.add_argument('--batch', type=int, default=500, help='Batch size for inserts')
parser.add_argument('--tables', nargs='*', help='Optional list of tables to transfer (in order)')
parser.add_argument('--sleep', type=float, default=0.01, help='Sleep between batches to reduce DB load')
args = parser.parse_args()

if not args.pg:
    print('No Postgres URL provided. Set DATABASE_URL in .env or pass --pg')
    sys.exit(2)


def reflect_tables(engine):
    md = MetaData()
    md.reflect(bind=engine)
    return md


def table_ordering(metadata):
    # Correct ordering: parent tables first, then child tables that reference them
    ordered = []
    preferred = ['user', 'business_profile', 'invoice', 'invoice_item', 'payment', 'subscription', 'webhook_log', 'payment_callback_log', 'failed_email', 'alembic_version']
    for p in preferred:
        if p in metadata.tables:
            ordered.append(p)
    for t in metadata.tables:
        if t not in ordered:
            ordered.append(t)
    return ordered


def copy_table(sqlite_engine, pg_engine, table_name, dry_run=False, limit=0, batch=500, sleep=0.01):
    s_meta = reflect_tables(sqlite_engine)
    p_meta = reflect_tables(pg_engine)

    if table_name not in s_meta.tables:
        print(f"Source table {table_name} not found, skipping.")
        return 0

    s_table = s_meta.tables[table_name]
    if table_name not in p_meta.tables:
        print(f"Target table {table_name} not found in Postgres — creating using reflected DDL is not supported by this script.\nPlease run migrations first.")
        return 0

    p_table = p_meta.tables[table_name]

    # Count rows in source
    with sqlite_engine.connect() as s_conn:
        cnt_res = s_conn.execute(select(text('count(1)')).select_from(s_table))
        src_count = cnt_res.scalar() if cnt_res is not None else 0

    print(f"Table {table_name}: source rows = {src_count}")
    if dry_run:
        return src_count

    offset = 0
    inserted = 0
    while True:
        with sqlite_engine.connect() as s_conn:
            sel = select(s_table).limit(batch)
            if limit > 0:
                sel = select(s_table).limit(min(batch, limit - offset))
            rows = list(s_conn.execute(sel))

        if not rows:
            break

        # Prepare insert for target; skip rows that already exist (by primary key)
        pk_cols = [c.name for c in p_table.primary_key] if p_table.primary_key is not None else []

        insert_rows = []
        for r in rows:
            row = r._asdict() if hasattr(r, '_asdict') else dict(r._mapping)
            if pk_cols:
                pk_vals = {k: row.get(k) for k in pk_cols}
                # Simple existence check - if we get an error, assume it doesn't exist and try to insert
                try:
                    with pg_engine.connect() as p_conn:
                        q = select(text('count(1)')).select_from(p_table)
                        for k, v in pk_vals.items():
                            q = q.where(text(f"{k} = :{k}"))
                        exists = p_conn.execute(q, pk_vals).scalar() > 0
                    if exists:
                        continue  # skip existing
                except Exception as e:
                    print(f"Warning: Could not check existence for {table_name}, attempting insert anyway: {e}")
                    # Continue with insert attempt

            insert_rows.append(row)

        if not insert_rows:
            offset += len(rows)
            if limit > 0 and offset >= limit:
                break
            continue

        # Perform batched inserts
        chunk = []
        for r in insert_rows:
            chunk.append(r)
            if len(chunk) >= batch:
                with pg_engine.begin() as p_conn:
                    try:
                        p_conn.execute(p_table.insert(), chunk)
                        inserted += len(chunk)
                    except IntegrityError as e:
                        print('IntegrityError during insert chunk:', e)
                chunk = []
                time.sleep(sleep)
        if chunk:
            with pg_engine.begin() as p_conn:
                try:
                    p_conn.execute(p_table.insert(), chunk)
                    inserted += len(chunk)
                except IntegrityError as e:
                    print('IntegrityError during final insert chunk:', e)

        offset += len(rows)
        if limit > 0 and offset >= limit:
            break

    print(f"Inserted {inserted} rows into {table_name} (skipped existing rows).")

    # Try to fix sequence if table has integer primary key named 'id'
    if 'id' in p_table.c:
        try:
            with pg_engine.begin() as p_conn:
                p_conn.execute(text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), (SELECT COALESCE(MAX(id),0) FROM " + table_name + "))"), {'tbl': table_name})
            print(f"Sequence for {table_name}.id updated.")
        except Exception:
            print(f"Could not update sequence for {table_name}; you may need to run setval manually.")

    return inserted


def main():
    sqlite_engine = create_engine(args.sqlite)
    pg_engine = create_engine(args.pg)

    # Reflect source metadata to get recommended table ordering
    s_meta = reflect_tables(sqlite_engine)
    if args.tables:
        tables = args.tables
    else:
        tables = table_ordering(s_meta)

    print('Planned table order:', tables)

    total_inserted = 0
    for t in tables:
        print('---')
        n = copy_table(sqlite_engine, pg_engine, t, dry_run=args.dry_run, limit=args.limit, batch=args.batch, sleep=args.sleep)
        total_inserted += n if isinstance(n, int) else 0

    print('---')
    print('Done. Total inserted (approx):', total_inserted)


if __name__ == '__main__':
    main()
