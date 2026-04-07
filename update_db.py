import sqlite3
import os

db_path = 'govsecai.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['road_complaints', 'health_complaints']
for table in tables:
    try:
        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [c[1] for c in cursor.fetchall()]
        if 'evidence_url' not in columns:
            print(f"Adding evidence_url to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN evidence_url TEXT")
            print("Done.")
        else:
            print(f"evidence_url already exists in {table}.")
    except Exception as e:
        print(f"Error updating {table}: {e}")

conn.commit()
conn.close()
