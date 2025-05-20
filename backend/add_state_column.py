#!/usr/bin/env python3
"""
Migration script to add state_json column to the Session table.

This script should be run once to update the database schema.
"""
import sqlite3
import os

# Path to the SQLite database
DATABASE_PATH = "app.db"  # Adjust this if your database is in a different location

def run_migration():
    """Add state_json column to the session table if it doesn't exist."""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(session)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'state_json' not in column_names:
            print("Adding state_json column to session table...")
            cursor.execute("ALTER TABLE session ADD COLUMN state_json JSON")
            conn.commit()
            print("✅ Column added successfully!")
        else:
            print("✅ state_json column already exists. No changes needed.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error adding state_json column: {str(e)}")
        return False

if __name__ == "__main__":
    print("Running migration to add state_json column to session table...")
    success = run_migration()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. See error messages above.")
