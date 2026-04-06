from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import os
import webbrowser
import threading
import uvicorn
import time
import uuid
import datetime

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

# Mount Static Files
# We mount this at the end or use a specific route to avoid conflicting with /api
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

USER_DIR = os.path.join(BASE_DIR, "user")
if os.path.isdir(USER_DIR):
    app.mount("/user", StaticFiles(directory=USER_DIR, html=True), name="user")

# --- Data Loading ---
def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    print(f"[*] Loading {filename}...")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
            # Efficient strip: only on object columns
            for col in df.select_dtypes(['object']).columns:
                df[col] = df[col].str.strip()
            print(f"[+] Loaded {len(df)} rows.")
            return df
        except Exception as e:
            print(f"[!] Error loading {filename}: {e}")
    return pd.DataFrame()

def save_csv(df, filename):
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)

# Load DataFrames
road_df = load_csv("road_complaints.csv")
health_df = load_csv("health_complaints.csv")
fraud_df = load_csv("banking_fraud.csv")

def reload_data():
    """Re-read CSVs from disk to pick up new entries."""
    global road_df, health_df, fraud_df
    road_df = load_csv("road_complaints.csv")
    health_df = load_csv("health_complaints.csv")
    fraud_df = load_csv("banking_fraud.csv")
    update_stats_cache()

# --- Global Stats Cache ---
cached_stats = {}

def update_stats_cache():
    global cached_stats
    print("[*] Calculating dashboard statistics...")
    try:
        # 1. Counts
        counts = {
            "road": len(road_df),
            "health": len(health_df),
            "fraud": len(fraud_df),
            "total": len(road_df) + len(health_df) + len(fraud_df)
        }
        
        # 2. Trends
        r_df = parse_dates(road_df.copy(), "date_reported")
        h_df = parse_dates(health_df.copy(), "date_reported")
        f_df = parse_dates(fraud_df.copy(), "timestamp")
        
        def get_monthly(df, date_col):
            if df.empty or date_col not in df.columns: return pd.Series(dtype=int)
            # Filter NaT
            valid = df.dropna(subset=[date_col])
            if valid.empty: return pd.Series(dtype=int)
            return valid.groupby(valid[date_col].dt.to_period("M")).size()

        r_trend = get_monthly(r_df, "date_reported")
        h_trend = get_monthly(h_df, "date_reported")
        f_trend = get_monthly(f_df, "timestamp")
        
        all_months = sorted(list(set(r_trend.index) | set(h_trend.index) | set(f_trend.index)))
        labels = [str(m) for m in all_months]
        
        r_data = r_trend.reindex(all_months, fill_value=0).tolist()
        h_data = h_trend.reindex(all_months, fill_value=0).tolist()
        f_data = f_trend.reindex(all_months, fill_value=0).tolist()
        total_data = [r + h + f for r, h, f in zip(r_data, h_data, f_data)]
        
        # 3. Alerts
        alerts = []
        def add_alerts_to_list(df, date_col, source, desc_col, city_col):
            if df.empty or date_col not in df.columns: return
            temp = df.copy()
            temp['dt_obj'] = temp[date_col]
            temp = temp.dropna(subset=['dt_obj']).sort_values('dt_obj', ascending=False).head(10)
            for _, row in temp.iterrows():
                alerts.append({
                    "source": source,
                    "date": str(row['dt_obj'].date()),
                    "description": str(row.get(desc_col, "New Alert")),
                    "city": str(row.get(city_col, "Unknown")),
                    "dt": row['dt_obj']
                })

        add_alerts_to_list(r_df, "date_reported", "Road", "description", "city")
        add_alerts_to_list(h_df, "date_reported", "Health", "complaint_text", "city")
        add_alerts_to_list(f_df, "timestamp", "Fraud", "merchant_category", "location_city")
        
        alerts.sort(key=lambda x: x['dt'], reverse=True)
        final_alerts = alerts[:10]
        for a in final_alerts: del a['dt']
        
        cached_stats = {
            "counts": counts,
            "trends": {
                "labels": labels,
                "road": r_data,
                "health": h_data,
                "fraud": f_data,
                "total": total_data
            },
            "alerts": final_alerts
        }
        print("[+] Stats cache updated.")
    except Exception as e:
        print(f"[!] Error calculating stats: {e}")
        cached_stats = {"counts": {"road":0,"health":0,"fraud":0,"total":0}, "trends": {"labels":[], "road":[], "health":[], "fraud":[], "total":[]}, "alerts": []}

# --- Models ---
class StatusUpdate(BaseModel):
    status: str

class RoadComplaintSubmit(BaseModel):
    city: str
    area: str
    issue_type: str
    description: str

class HealthComplaintSubmit(BaseModel):
    patient_id: str
    city: str
    area: str
    facility: str
    category: str
    complaint_text: str

class BankingFraudSubmit(BaseModel):
    account_id: str
    amount: str
    merchant_category: str
    transaction_type: str
    device_type: str
    location_city: str
    area: str

# --- Endpoints ---

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/reload")
def reload_endpoint():
    """Force reload all CSVs from disk."""
    reload_data()
    return {"status": "reloaded", "counts": {"road": len(road_df), "health": len(health_df), "fraud": len(fraud_df)}}

@app.get("/api/stats")
def get_stats():
    reload_data()
    return cached_stats

@app.get("/")
def read_root():
    return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))

# --- ROAD ---
@app.get("/api/road/summary")
def road_summary():
    if road_df.empty: return {}
    city_counts = road_df["city"].value_counts().to_dict() if "city" in road_df.columns else {}
    return {"complaints_by_city": city_counts}

@app.get("/api/road/areas/{city}")
def get_city_areas(city: str):
    if road_df.empty: return {"area_counts": {}}
    subset = road_df[road_df["city"].str.lower() == city.lower()]
    if subset.empty or "area" not in subset.columns: return {"area_counts": {}}
    area_counts = subset["area"].value_counts().head(15).to_dict()
    return {"area_counts": area_counts}

@app.get("/api/road/complaints/{city}/{area}")
def get_complaints(city: str, area: str):
    if road_df.empty: return {"complaints": []}
    mask = (road_df["city"].str.lower() == city.lower()) & (road_df["area"].str.lower() == area.lower())
    filtered = road_df[mask]
    return {"complaints": filtered.to_dict(orient="records")}

@app.get("/api/road/area-status/{city}/{area}")
def get_area_status(city: str, area: str):
    if road_df.empty: return {"status": "Pending"}
    mask = (road_df["city"].str.lower() == city.lower()) & (road_df["area"].str.lower() == area.lower())
    filtered = road_df[mask]
    if filtered.empty: return {"status": "Pending"}
    
    status = "Pending"
    if "area_status" in filtered.columns:
        val = filtered.iloc[0]["area_status"]
        if pd.notna(val) and str(val).strip():
            status = str(val).strip()
    return {"status": status}

@app.post("/api/road/area-status/{city}/{area}")
def update_area_status(city: str, area: str, body: StatusUpdate):
    global road_df
    if road_df.empty: raise HTTPException(404, "No data")
    
    mask = (road_df["city"].str.lower() == city.lower()) & (road_df["area"].str.lower() == area.lower())
    if not mask.any(): raise HTTPException(404, "Area not found")
    
    if "area_status" not in road_df.columns:
        road_df["area_status"] = "Pending"
        
    road_df.loc[mask, "area_status"] = body.status
    save_csv(road_df, "road_complaints.csv")
    return {"status": "updated"}

@app.post("/api/road/area-resolve/{city}/{area}")
def resolve_area(city: str, area: str):
    global road_df
    if road_df.empty: raise HTTPException(404, "No data")
    
    mask = (road_df["city"].str.lower() == city.lower()) & (road_df["area"].str.lower() == area.lower())
    count = mask.sum()
    if count == 0: raise HTTPException(404, "Area not found")
    
    road_df = road_df[~mask]
    save_csv(road_df, "road_complaints.csv")
    return {"removed_count": int(count)}

# --- Helpers ---
def parse_dates(df, date_col):
    if df.empty or date_col not in df.columns: return df
    # Try multiple formats or let pandas infer
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
    return df

# --- Stats & Home ---
@app.get("/api/stats")
def get_stats():
    if not cached_stats:
        update_stats_cache()
    return cached_stats

# --- HEALTH ---
@app.get("/api/health/summary")
def health_summary():
    if health_df.empty: return {}
    city_counts = health_df["city"].value_counts().to_dict() if "city" in health_df.columns else {}
    return {"complaints_by_city": city_counts}

@app.get("/api/health/areas/{city}")
def get_health_areas(city: str):
    if health_df.empty: return {"area_counts": {}}
    subset = health_df[health_df["city"].str.lower() == city.lower()]
    if subset.empty or "area" not in subset.columns: return {"area_counts": {}}
    area_counts = subset["area"].value_counts().head(15).to_dict()
    return {"area_counts": area_counts}

@app.get("/api/health/area-status/{city}/{area}")
def get_health_area_status(city: str, area: str):
    if health_df.empty: return {"status": "Pending"}
    mask = (health_df["city"].str.lower() == city.lower()) & (health_df["area"].str.lower() == area.lower())
    filtered = health_df[mask]
    if filtered.empty: return {"status": "Pending"}
    
    status = "Pending"
    if "area_status" in filtered.columns:
        val = filtered.iloc[0]["area_status"]
        if pd.notna(val) and str(val).strip():
            status = str(val).strip()
    return {"status": status}

@app.post("/api/health/area-status/{city}/{area}")
def update_health_area_status(city: str, area: str, body: StatusUpdate):
    global health_df
    if health_df.empty: raise HTTPException(404, "No data")
    
    mask = (health_df["city"].str.lower() == city.lower()) & (health_df["area"].str.lower() == area.lower())
    if not mask.any(): raise HTTPException(404, "Area not found")
    
    if "area_status" not in health_df.columns:
        health_df["area_status"] = "Pending"
        
    health_df.loc[mask, "area_status"] = body.status
    save_csv(health_df, "health_complaints.csv")
    return {"status": "updated"}

# --- FRAUD ---
@app.get("/api/fraud/summary")
def fraud_summary():
    if fraud_df.empty: return {}
    city_counts = fraud_df["location_city"].value_counts().to_dict() if "location_city" in fraud_df.columns else {}
    return {"fraud_by_city": city_counts}

@app.get("/api/fraud/areas/{city}")
def get_fraud_areas(city: str):
    if fraud_df.empty: return {"area_counts": {}}
    subset = fraud_df[fraud_df["location_city"].str.lower() == city.lower()]
    if subset.empty or "area" not in subset.columns: return {"area_counts": {}}
    area_counts = subset["area"].value_counts().head(15).to_dict()
    return {"area_counts": area_counts}

@app.get("/api/fraud/area-status/{city}/{area}")
def get_fraud_area_status(city: str, area: str):
    if fraud_df.empty: return {"status": "Pending"}
    mask = (fraud_df["location_city"].str.lower() == city.lower()) & (fraud_df["area"].str.lower() == area.lower())
    filtered = fraud_df[mask]
    if filtered.empty: return {"status": "Pending"}
    
    status = "Pending"
    if "area_status" in filtered.columns:
        val = filtered.iloc[0]["area_status"]
        if pd.notna(val) and str(val).strip():
            status = str(val).strip()
    return {"status": status}

@app.post("/api/fraud/area-status/{city}/{area}")
def update_fraud_area_status(city: str, area: str, body: StatusUpdate):
    global fraud_df
    if fraud_df.empty: raise HTTPException(404, "No data")
    
    mask = (fraud_df["location_city"].str.lower() == city.lower()) & (fraud_df["area"].str.lower() == area.lower())
    if not mask.any(): raise HTTPException(404, "Area not found")
    
    if "area_status" not in fraud_df.columns:
        fraud_df["area_status"] = "Pending"
        
    fraud_df.loc[mask, "area_status"] = body.status
    save_csv(fraud_df, "banking_fraud.csv")
    return {"status": "updated"}

@app.post("/api/health/area-resolve/{city}/{area}")
def resolve_health_area(city: str, area: str):
    global health_df
    if health_df.empty: raise HTTPException(404, "No data")
    
    mask = (health_df["city"].str.lower() == city.lower()) & (health_df["area"].str.lower() == area.lower())
    if not mask.any(): raise HTTPException(404, "Area not found")
    
    removed_count = mask.sum()
    health_df = health_df[~mask]
    save_csv(health_df, "health_complaints.csv")
    return {"status": "resolved", "removed_count": int(removed_count)}

@app.post("/api/fraud/area-resolve/{city}/{area}")
def resolve_fraud_area(city: str, area: str):
    global fraud_df
    if fraud_df.empty: raise HTTPException(404, "No data")
    
    mask = (fraud_df["location_city"].str.lower() == city.lower()) & (fraud_df["area"].str.lower() == area.lower())
    if not mask.any(): raise HTTPException(404, "Area not found")
    
    removed_count = mask.sum()
    fraud_df = fraud_df[~mask]
    save_csv(fraud_df, "banking_fraud.csv")
    return {"status": "resolved", "removed_count": int(removed_count)}

# --- SUBMISSION ENDPOINTS ---

@app.post("/api/submit/road")
def submit_road(data: RoadComplaintSubmit):
    global road_df
    new_id = str(uuid.uuid4())
    new_row = {
        "complaint_id": new_id,
        "date_reported": datetime.datetime.now().strftime("%d-%m-%Y"),
        "city": data.city,
        "area": data.area,
        "issue_type": data.issue_type,
        "description": data.description,
        "status": "pending",
        "priority": "Medium",
        "latitude": "23.0225", # Default simulated
        "longitude": "72.5714", # Default simulated
        "area_status": "pending"
    }
    road_df = pd.concat([road_df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(road_df, "road_complaints.csv")
    reload_data()
    return {"status": "submitted", "id": new_id}

@app.post("/api/submit/health")
def submit_health(data: HealthComplaintSubmit):
    global health_df
    new_id = str(uuid.uuid4())
    new_row = {
        "complaint_id": new_id,
        "patient_id": data.patient_id,
        "date_reported": datetime.datetime.now().strftime("%d-%m-%Y"),
        "city": data.city,
        "area": data.area,
        "facility": data.facility,
        "category": data.category,
        "severity": "Medium",
        "complaint_text": data.complaint_text,
        "area_status": "pending"
    }
    health_df = pd.concat([health_df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(health_df, "health_complaints.csv")
    reload_data()
    return {"status": "submitted", "id": new_id}

@app.post("/api/submit/banking")
def submit_banking(data: BankingFraudSubmit):
    global fraud_df
    new_id = str(uuid.uuid4())
    new_row = {
        "transaction_id": new_id,
        "account_id": data.account_id,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "amount": data.amount,
        "merchant_category": data.merchant_category,
        "transaction_type": data.transaction_type,
        "device_type": data.device_type,
        "location_city": data.location_city,
        "risk_score": "0.0",
        "is_fraud": "0",
        "area_status": "pending",
        "area": data.area
    }
    fraud_df = pd.concat([fraud_df, pd.DataFrame([new_row])], ignore_index=True)
    save_csv(fraud_df, "banking_fraud.csv")
    reload_data()
    return {"status": "submitted", "id": new_id}

@app.get("/api/track/{complaint_id}")
def track_complaint(complaint_id: str):
    # Search in road
    if not road_df.empty:
        match = road_df[road_df["complaint_id"] == complaint_id]
        if not match.empty:
            return {"type": "Road", "status": match.iloc[0].get("area_status", "pending"), "details": match.iloc[0].to_dict()}
    
    # Search in health
    if not health_df.empty:
        match = health_df[health_df["complaint_id"] == complaint_id]
        if not match.empty:
            return {"type": "Health", "status": match.iloc[0].get("area_status", "pending"), "details": match.iloc[0].to_dict()}
            
    # Search in banking
    if not fraud_df.empty:
        match = fraud_df[fraud_df["transaction_id"] == complaint_id]
        if not match.empty:
            return {"type": "Banking", "status": match.iloc[0].get("area_status", "pending"), "details": match.iloc[0].to_dict()}
            
    raise HTTPException(404, "Complaint ID not found")

# --- Auto-Open ---
def open_dashboard():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000/dashboard/index.html")

if __name__ == "__main__":
    # Initial cache build
    update_stats_cache()
    threading.Thread(target=open_dashboard).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
