from app import create_app
import os

app = create_app()

def run_migrations_on_startup():
    """Run migrations automatically on startup in production."""
    try:
        from flask_migrate import upgrade
        with app.app_context():
            upgrade()
        print("✓ Database migrations completed successfully")
    except Exception as e:
        print(f"Migration error (continuing anyway): {e}")

if __name__ == "__main__":
    # Run migrations on startup if in production
    if os.getenv('RENDER'):  # Render sets this environment variable
        run_migrations_on_startup()
    
    app.run(host="0.0.0.0", port=8000, debug=False)