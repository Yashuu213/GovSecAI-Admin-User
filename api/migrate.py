import os
import pandas as pd
from sqlalchemy import create_engine, text
from models import Base
# Set path relative to this script's folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "govsecai.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

engine = create_engine(f"sqlite:///{DB_PATH}")

def migrate_csv(csv_name, table_name, chunk_size=10000):
    csv_path = os.path.join(DATA_DIR, csv_name)
    if not os.path.exists(csv_path):
        print(f"[!] File not found: {csv_path}")
        return
    print(f"[*] Migrating {csv_path} to {table_name}...")
    
    count = 0
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=chunk_size):
        chunk = chunk.fillna("")
        # We exclusively use append. Base.metadata.create_all already built the perfect table including the 'id' auto-increment column.
        chunk.to_sql(table_name, con=engine, if_exists='append', index=False)
        count += len(chunk)
        print(f"  [+] Migrated {count} rows...")
        
    print(f"[+] Finished {csv_name}: {count} total rows.")

def add_indices():
    print("[*] Adding indices for performance...")
    with engine.connect() as conn:
        # We manually add indices after the data is in
        try:
            conn.execute(text("CREATE INDEX idx_road_city ON road_complaints(city)"))
            conn.execute(text("CREATE INDEX idx_road_area ON road_complaints(area)"))
            conn.execute(text("CREATE INDEX idx_health_city ON health_complaints(city)"))
            conn.execute(text("CREATE INDEX idx_health_area ON health_complaints(area)"))
            conn.execute(text("CREATE INDEX idx_fraud_city ON banking_fraud(location_city)"))
            conn.execute(text("CREATE INDEX idx_fraud_area ON banking_fraud(area)"))
            conn.commit()
            print("[+] Indices created.")
        except Exception as e:
            print(f"[!] Warning on indices: {e}")

if __name__ == "__main__":
    import time
    time.sleep(1) # wait for db locks to release just in case
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("[*] Cleaned existing database.")
        except Exception as e:
            print(f"Could not remove DB, it might be in use: {e}")
            import sys
            sys.exit(1)
            
    print("[*] Initializing tables...")
    Base.metadata.create_all(bind=engine)
    
    migrate_csv("road_complaints.csv", "road_complaints")
    migrate_csv("health_complaints.csv", "health_complaints")
    migrate_csv("banking_fraud.csv", "banking_fraud")
    
    add_indices()
    
    print("[!] Migration Complete.")
