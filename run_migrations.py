#!/usr/bin/env python3
"""
Run database migrations - safe to run multiple times.
This can be called during app startup or as a separate process.
"""
import os
import subprocess
import sys

def run_migrations():
    """Run Flask-Migrate database migrations."""
    try:
        # Set Flask app environment variable
        os.environ['FLASK_APP'] = 'app.py'
        
        # Run the migration upgrade
        result = subprocess.run([
            sys.executable, '-m', 'flask', 'db', 'upgrade'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("✓ Database migrations completed successfully")
            if result.stdout:
                print("Migration output:", result.stdout)
        else:
            print("✗ Migration failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Error running migrations: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)