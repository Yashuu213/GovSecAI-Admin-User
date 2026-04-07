import os
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "govsecai_simple.db")
engine = create_engine(f"sqlite:///{DB_PATH}")

DATA_DIR = os.path.join(BASE_DIR, "data")

def migrate_simple(csv_name, table_name):
    csv_path = os.path.join(DATA_DIR, csv_name)
    print(f"[*] Migrating {csv_name} (Simple)...")
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=5000):
        chunk.to_sql(table_name, con=engine, if_exists='append', index=False)
    print("[+] Done.")

if __name__ == "__main__":
    migrate_simple("road_complaints.csv", "road_complaints")
    migrate_simple("health_complaints.csv", "health_complaints")
    migrate_simple("banking_fraud.csv", "banking_fraud")
