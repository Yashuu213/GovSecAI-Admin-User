import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path, dtype=str)
    return pd.DataFrame()

road_df = load_csv("road_complaints.csv")
health_df = load_csv("health_complaints.csv")
fraud_df = load_csv("banking_fraud.csv")

print("--- Samples ---")
print("Road head:\n", road_df[["date_reported", "city"]].head())
print("Health head:\n", health_df[["date_reported", "city"]].head())
print("Fraud head:\n", fraud_df[["timestamp", "location_city"]].head())

def parse_dates(df, date_col):
    if df.empty or date_col not in df.columns: return df
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
    return df

r_df = parse_dates(road_df.copy(), "date_reported")
f_df = parse_dates(fraud_df.copy(), "timestamp")

print("\n--- Parsed Dates ---")
print("Road date head:\n", r_df["date_reported"].head())
print("Fraud date head:\n", f_df["timestamp"].head())

print("\nRoad counts:", len(road_df))
print("Health counts:", len(health_df))
print("Fraud counts:", len(fraud_df))
