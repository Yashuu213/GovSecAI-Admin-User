import pandas as pd
import os
from fastapi import FastAPI
from pydantic import BaseModel

# Mocking the setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str)
        return df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    return pd.DataFrame()

def parse_dates(df, date_col):
    if df.empty or date_col not in df.columns: return df
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
    return df

road_df = load_csv("road_complaints.csv")
health_df = load_csv("health_complaints.csv")
fraud_df = load_csv("banking_fraud.csv")

def get_stats():
    try:
        counts = {
            "road": len(road_df),
            "health": len(health_df),
            "fraud": len(fraud_df),
            "total": len(road_df) + len(health_df) + len(fraud_df)
        }
        
        r_df = parse_dates(road_df.copy(), "date_reported")
        h_df = parse_dates(health_df.copy(), "date_reported")
        f_df = parse_dates(fraud_df.copy(), "timestamp")
        
        def get_monthly(df, date_col):
            if df.empty: return pd.Series(dtype=int)
            return df.groupby(df[date_col].dt.to_period("M")).size()

        r_trend = get_monthly(r_df, "date_reported")
        h_trend = get_monthly(h_df, "date_reported")
        f_trend = get_monthly(f_df, "timestamp")
        
        all_months = sorted(list(set(r_trend.index) | set(h_trend.index) | set(f_trend.index)))
        labels = [str(m) for m in all_months]
        
        r_data = r_trend.reindex(all_months, fill_value=0).tolist()
        h_data = h_trend.reindex(all_months, fill_value=0).tolist()
        f_data = f_trend.reindex(all_months, fill_value=0).tolist()
        total_data = [r + h + f for r, h, f in zip(r_data, h_data, f_data)]
        
        print("Stats success!")
        print("Counts:", counts)
        print("Trends labels (head):", labels[:5])
        return True
    except Exception as e:
        print("Stats FAILED with error:", e)
        import traceback
        traceback.print_exc()
        return False

get_stats()
