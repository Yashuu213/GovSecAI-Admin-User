import sqlite3
import os
import subprocess
import time

def kill_port_8000():
    print("[*] Attempting to clear Port 8000...")
    try:
        # Get PID on port 8000
        cmd = 'netstat -ano | findstr :8000'
        output = subprocess.check_output(cmd, shell=True).decode()
        for line in output.splitlines():
            if "LISTENING" in line or "ESTABLISHED" in line:
                pid = line.strip().split()[-1]
                if pid != "0":
                    print(f"[*] Killing process {pid} on port 8000...")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    time.sleep(1)
    except Exception as e:
        print(f"[*] Port 8000 is already clear or no process found: {e}")

def fix_schema():
    db_path = 'govsecai.db'
    if not os.path.exists(db_path):
        print(f"[!] Error: {db_path} not found")
        return

    print(f"[*] Fixing schema for {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ["road_complaints", "health_complaints", "banking_fraud"]
    
    for table in tables:
        try:
            # Check if 'id' column exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'id' not in columns:
                print(f"[*] Adding 'id' column to {table}...")
                # SQLite doesn't support easy 'ADD COLUMN PRIMARY KEY' so we rebuild
                cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
                
                # Get old schema to mimic columns
                cursor.execute(f"PRAGMA table_info({table}_old)")
                cols_info = cursor.fetchall()
                col_defs = []
                col_names = []
                for c in cols_info:
                    col_names.append(c[1])
                    col_defs.append(f"{c[1]} {c[2]}")
                
                # Create new table with ID
                new_schema = f"CREATE TABLE {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {', '.join(col_defs)})"
                cursor.execute(new_schema)
                
                # Copy data
                cursor.execute(f"INSERT INTO {table} ({', '.join(col_names)}) SELECT {', '.join(col_names)} FROM {table}_old")
                cursor.execute(f"DROP TABLE {table}_old")
                print(f"[+] {table} rebuilt with 'id' column.")
            else:
                print(f"[+] 'id' column already exists in {table}.")

            # Check for evidence_url and status columns (for AI)
            if 'evidence_url' not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN evidence_url TEXT")
                print(f"[+] Added evidence_url to {table}")
            
            if table == "road_complaints" and "priority" not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN priority TEXT")
            if table == "health_complaints" and "severity" not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN severity TEXT")

        except Exception as e:
            print(f"[!] Error processing {table}: {e}")

    conn.commit()
    conn.close()
    print("[+] Database schema fix complete.")

if __name__ == "__main__":
    kill_port_8000()
    fix_schema()
