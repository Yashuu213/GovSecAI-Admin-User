import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    print(f"Loading {path}...")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
            print(f"  Success: {len(df)} rows")
            return df
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print(f"  Path does not exist")
    return pd.DataFrame()

road_df = load_csv("road_complaints.csv")
health_df = load_csv("health_complaints.csv")
fraud_df = load_csv("banking_fraud.csv")

print("\nRoad DF Columns:", road_df.columns.tolist())
print("Health DF Columns:", health_df.columns.tolist())
print("Fraud DF Columns:", fraud_df.columns.tolist())
