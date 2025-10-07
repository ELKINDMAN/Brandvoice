# DB migration runbook — SQLite -> PostgreSQL (git-bash friendly)

This runbook shows a safe, resumable approach to migrate your existing SQLite DB (instance/brandvoice.db) into a managed PostgreSQL database (for example Supabase). It includes quick pgloader notes, and a Python transfer script that is safe to run from git-bash.

Prerequisites
- Install Python (3.10+ recommended) and the project virtual environment dependencies.
- Install `psycopg2-binary` and `sqlalchemy` in your venv (if not already). Example: `pip install psycopg2-binary sqlalchemy python-dotenv`
- Have the PostgreSQL connection string ready and stored in a `.env` file (see examples below).
- Make a backup copy of your SQLite DB before doing anything.

Files provided
- `scripts/check_pg_connection.py` — small script to validate connectivity to Postgres (reads `.env`).
- `scripts/sqlite_to_postgres.py` — resumable, batchable transfer script that copies data from a SQLite file into Postgres. Works best when the target schema already exists (recommended) but can also create tables if missing.

Quick backup (git-bash)
```bash
mkdir -p backups
cp instance/brandvoice.db backups/brandvoice-$(date +%Y%m%d%H%M%S).db
```

Set up a `.env` (example — do NOT commit this file):
```text
# .env
PG_USER=postgres.cttasemogybrglcltgil
PG_PASSWORD=KINDsupabase002
PG_HOST=aws-1-us-east-2.pooler.supabase.com
PG_PORT=5432
PG_DB=postgres
# Or full URL (preferred):
DATABASE_URL=postgresql+psycopg2://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DB?sslmode=require
```

Connection check (git-bash)
```bash
# activate your venv first
python scripts/check_pg_connection.py
```

Option A — recommended: Alembic-first + Python transfer (keeps migrations authoritative)
1. Create the Postgres database and user in your provider (enable backups/snapshots).
2. Run migrations to create the schema:
```bash
# from repo root, using git-bash
export FLASK_APP=app.py
export FLASK_ENV=production
export DATABASE_URL="postgresql+psycopg2://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DB?sslmode=require"
python -m flask db upgrade
```
3. Dry-run the transfer script (transfers a tiny sample):
```bash
python scripts/sqlite_to_postgres.py --dry-run --limit 10
```
4. Run the full transfer (no downtime if you can accept small window for final sync; for zero-loss, plan a short maintenance window):
```bash
python scripts/sqlite_to_postgres.py
```
5. After transfer, ensure sequences are set (the script will attempt this). Verify counts:
```bash
psql "$DATABASE_URL" -c "SELECT 'users', COUNT(*) FROM users;"
psql "$DATABASE_URL" -c "SELECT 'payment', COUNT(*) FROM payment;"
```

Option B — pgloader (fastest, bulk approach)
- Install pgloader (via Docker on Windows or on a Linux host). Pgloader can create the Postgres schema and load data quickly.
- If you let pgloader create schema, stamp Alembic to the current head afterwards:
```bash
# after pgloader completes successfully
export FLASK_APP=app.py
python -m flask db stamp head
```
- Example using Docker (git-bash):
```bash
# Put a pgload.load file alongside your sqlite file or use an inline script
docker run --rm -v "$(pwd):/data" dimitri/pgloader:latest pgloader /data/pgload.load
```

Notes and safety
- Always run a dry-run first. The Python script supports `--dry-run`.
- If your app is writing during migration, you'll need a short maintenance window or a final incremental sync.
- Keep the SQLite backup for at least 48–72 hours after cutover.

Verification checklist (post-migration)
- Start the application pointing to Postgres and confirm it starts.
- Check user counts and payment counts match the SQLite counts.
- Test a password reset (email delivery), and a small payment flow to ensure webhooks are processed.

Rollback (quick)
- Stop app
- Restore `.env` or `DATABASE_URL` to the original SQLite URI (e.g. `sqlite:///instance/brandvoice.db`) and start the app.
- Restore the SQLite file from the backup if the file was overwritten.

If you want, I can also: create a ready-to-run `pgload.load` tuned for your repo path and your Supabase URL, or iterate on the Python transfer script to add transformations for specific tables (for example, preserving created_at formats). Ask which you'd like next.
