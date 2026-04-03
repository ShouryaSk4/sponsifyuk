import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobs.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if email column already exists
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

if 'email' not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    print("Added 'email' column to users table")
else:
    print("'email' column already exists in users table")

conn.commit()

# Verify 
cursor.execute("PRAGMA table_info(users)")
print("\nCurrent users table schema:")
for col in cursor.fetchall():
    print(f"  {col[1]:25s} {col[2]:15s} {'NOT NULL' if col[3] else 'NULLABLE':10s} default={col[4]}")

conn.close()
print("\nDB migration complete!")
