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
import datetime
import uuid
import time
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import Depends, Form, UploadFile, File
from database import SessionLocal, engine, get_db
from models import RoadComplaint, HealthComplaint, BankingFraud
from sqlalchemy import func
from ai_engine import analyze_complaint_nlp, verify_image_cv, predict_fraud_risk

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
UPLOAD_DIR = os.path.join(BASE_DIR, "api", "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount Static Files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "api", "static")), name="static")
DATA_DIR = os.path.join(BASE_DIR, "data")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

# Mount Static Files
# We mount this at the end or use a specific route to avoid conflicting with /api
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")

USER_DIR = os.path.join(BASE_DIR, "user")
if os.path.isdir(USER_DIR):
    app.mount("/user", StaticFiles(directory=USER_DIR, html=True), name="user")

# --- Helpers ---
def to_dict(obj):
    """Convert SQLAlchemy model to dict, removing internal state."""
    if not obj: return None
    d = obj.__dict__.copy()
    d.pop("_sa_instance_state", None)
    return d

# --- Global Stats Cache ---
cached_stats = {}

def update_stats_cache(db: Session):
    global cached_stats
    print("[*] Calculating dashboard statistics...")
    try:
        # 1. Counts
        road_count = db.query(RoadComplaint).count()
        health_count = db.query(HealthComplaint).count()
        fraud_count = db.query(BankingFraud).count()
        
        counts = {
            "road": road_count,
            "health": health_count,
            "fraud": fraud_count,
            "total": road_count + health_count + fraud_count
        }
        
        # 2. Trends (Simple distributed simulation for large dataset)
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        # Basic curve simulation instead of flat line
        r_data = [int(road_count * f) for f in [0.15, 0.17, 0.16, 0.18, 0.16, 0.18]]
        h_data = [int(health_count * f) for f in [0.16, 0.15, 0.18, 0.17, 0.16, 0.18]]
        f_data = [int(fraud_count * f) for f in [0.17, 0.16, 0.15, 0.16, 0.18, 0.18]]
        total_data = [r + h + f for r, h, f in zip(r_data, h_data, f_data)]
        
        # 3. Alerts (Merged and sorted by Date)
        alerts = []
        
        # Helper to normalize dates for sorting
        def parse_date(date_str):
            try:
                if 'T' in date_str: # Fraud format: YYYY-MM-DDTHH:MM:SS
                    return date_str
                # Road/Health format: DD-MM-YYYY
                parts = date_str.split('-')
                if len(parts) == 3:
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"
                return date_str
            except:
                return "0000-00-00"

        latest_roads = db.query(RoadComplaint).order_by(RoadComplaint.id.desc()).limit(10).all()
        for r in latest_roads:
            alerts.append({
                "source": "Road", 
                "date": r.date_reported, 
                "sort_date": parse_date(r.date_reported),
                "description": r.description, 
                "city": r.city, 
                "id": r.id,
                "evidence_url": r.evidence_url if r.evidence_url else None
            })
            
        latest_health = db.query(HealthComplaint).order_by(HealthComplaint.id.desc()).limit(10).all()
        for h in latest_health:
            alerts.append({
                "source": "Health", 
                "date": h.date_reported, 
                "sort_date": parse_date(h.date_reported),
                "description": h.complaint_text, 
                "city": h.city, 
                "id": h.id,
                "evidence_url": h.evidence_url if h.evidence_url else None
            })
            
        latest_fraud = db.query(BankingFraud).order_by(BankingFraud.id.desc()).limit(10).all()
        for f in latest_fraud:
            alerts.append({
                "source": "Fraud", 
                "date": f.timestamp[:10], 
                "sort_date": f.timestamp,
                "description": f.merchant_category, 
                "city": f.location_city, 
                "id": f.id
            })
            
        # Sort by sort_date (YYYY-MM-DD) descending
        alerts.sort(key=lambda x: x.get('sort_date', ""), reverse=True)
        final_alerts = alerts[:10]
        
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
def reload_endpoint(db: Session = Depends(get_db)):
    """Force update of cached stats from DB."""
    update_stats_cache(db)
    return {"status": "reloaded"}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    if not cached_stats:
        update_stats_cache(db)
    return cached_stats

@app.get("/")
def read_root():
    return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))

# --- ROAD ---
@app.get("/api/road/summary")
def road_summary(db: Session = Depends(get_db)):
    results = db.query(RoadComplaint.city, func.count(RoadComplaint.id)).group_by(RoadComplaint.city).all()
    return {"complaints_by_city": dict(results)}

@app.get("/api/road/areas/{city}")
def get_city_areas(city: str, db: Session = Depends(get_db)):
    results = db.query(RoadComplaint.area, func.count(RoadComplaint.id))\
                .filter(func.lower(RoadComplaint.city) == city.lower())\
                .group_by(RoadComplaint.area).limit(15).all()
    return {"area_counts": dict(results)}

@app.get("/api/road/complaints/{city}/{area}")
def get_complaints(city: str, area: str, db: Session = Depends(get_db)):
    results = db.query(RoadComplaint)\
                .filter(func.lower(RoadComplaint.city) == city.lower())\
                .filter(func.lower(RoadComplaint.area) == area.lower()).all()
    return {"complaints": [to_dict(r) for r in results]}

@app.get("/api/road/area-status/{city}/{area}")
def get_area_status(city: str, area: str, db: Session = Depends(get_db)):
    result = db.query(RoadComplaint.area_status)\
               .filter(func.lower(RoadComplaint.city) == city.lower())\
               .filter(func.lower(RoadComplaint.area) == area.lower()).first()
    return {"status": result[0] if result else "Pending"}

@app.post("/api/road/area-status/{city}/{area}")
def update_area_status(city: str, area: str, body: StatusUpdate, db: Session = Depends(get_db)):
    db.query(RoadComplaint)\
      .filter(func.lower(RoadComplaint.city) == city.lower())\
      .filter(func.lower(RoadComplaint.area) == area.lower())\
      .update({"area_status": body.status})
    db.commit()
    return {"status": "updated"}

@app.post("/api/road/area-resolve/{city}/{area}")
def resolve_area(city: str, area: str, db: Session = Depends(get_db)):
    deleted = db.query(RoadComplaint)\
                .filter(func.lower(RoadComplaint.city) == city.lower())\
                .filter(func.lower(RoadComplaint.area) == area.lower()).delete()
    db.commit()
    return {"removed_count": deleted}

# --- HEALTH ---
@app.get("/api/health/summary")
def health_summary(db: Session = Depends(get_db)):
    results = db.query(HealthComplaint.city, func.count(HealthComplaint.id)).group_by(HealthComplaint.city).all()
    return {"complaints_by_city": dict(results)}

@app.get("/api/health/areas/{city}")
def get_health_areas(city: str, db: Session = Depends(get_db)):
    results = db.query(HealthComplaint.area, func.count(HealthComplaint.id))\
                .filter(func.lower(HealthComplaint.city) == city.lower())\
                .group_by(HealthComplaint.area).limit(15).all()
    return {"area_counts": dict(results)}

@app.get("/api/health/area-status/{city}/{area}")
def get_health_area_status(city: str, area: str, db: Session = Depends(get_db)):
    result = db.query(HealthComplaint.area_status)\
               .filter(func.lower(HealthComplaint.city) == city.lower())\
               .filter(func.lower(HealthComplaint.area) == area.lower()).first()
    return {"status": result[0] if result else "Pending"}

@app.post("/api/health/area-status/{city}/{area}")
def update_health_area_status(city: str, area: str, body: StatusUpdate, db: Session = Depends(get_db)):
    db.query(HealthComplaint)\
      .filter(func.lower(HealthComplaint.city) == city.lower())\
      .filter(func.lower(HealthComplaint.area) == area.lower())\
      .update({"area_status": body.status})
    db.commit()
    return {"status": "updated"}

# --- FRAUD ---
@app.get("/api/fraud/summary")
def fraud_summary(db: Session = Depends(get_db)):
    results = db.query(BankingFraud.location_city, func.count(BankingFraud.id)).group_by(BankingFraud.location_city).all()
    return {"fraud_by_city": dict(results)}

@app.get("/api/fraud/areas/{city}")
def get_fraud_areas(city: str, db: Session = Depends(get_db)):
    results = db.query(BankingFraud.area, func.count(BankingFraud.id))\
                .filter(func.lower(BankingFraud.location_city) == city.lower())\
                .group_by(BankingFraud.area).limit(15).all()
    return {"area_counts": dict(results)}

@app.get("/api/fraud/area-status/{city}/{area}")
def get_fraud_area_status(city: str, area: str, db: Session = Depends(get_db)):
    result = db.query(BankingFraud.area_status)\
               .filter(func.lower(BankingFraud.location_city) == city.lower())\
               .filter(func.lower(BankingFraud.area) == area.lower()).first()
    return {"status": result[0] if result else "Pending"}

@app.post("/api/fraud/area-status/{city}/{area}")
def update_fraud_area_status(city: str, area: str, body: StatusUpdate, db: Session = Depends(get_db)):
    db.query(BankingFraud)\
      .filter(func.lower(BankingFraud.location_city) == city.lower())\
      .filter(func.lower(BankingFraud.area) == area.lower())\
      .update({"area_status": body.status})
    db.commit()
    return {"status": "updated"}

@app.post("/api/health/area-resolve/{city}/{area}")
def resolve_health_area(city: str, area: str, db: Session = Depends(get_db)):
    deleted = db.query(HealthComplaint)\
                .filter(func.lower(HealthComplaint.city) == city.lower())\
                .filter(func.lower(HealthComplaint.area) == area.lower()).delete()
    db.commit()
    return {"status": "resolved", "removed_count": deleted}

@app.post("/api/fraud/area-resolve/{city}/{area}")
def resolve_fraud_area(city: str, area: str, db: Session = Depends(get_db)):
    deleted = db.query(BankingFraud)\
                .filter(func.lower(BankingFraud.location_city) == city.lower())\
                .filter(func.lower(BankingFraud.area) == area.lower()).delete()
    db.commit()
    return {"status": "resolved", "removed_count": deleted}

# --- SUBMISSION ENDPOINTS ---

@app.post("/api/submit/road")
async def submit_road(
    city: str = Form(...),
    area: str = Form(...),
    issue_type: str = Form(...),
    description: str = Form(...),
    evidence: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    new_id = str(uuid.uuid4())
    
    # 1. AI Triage (NLP)
    triage = analyze_complaint_nlp(description)
    
    # 2. AI Image Verification (CV)
    cv_status = "No image"
    evidence_url = None
    if evidence and evidence.filename:
        file_extension = Path(evidence.filename).suffix
        safe_filename = f"{new_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        content = await evidence.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        cv_result = verify_image_cv(content)
        if not cv_result["verified"]:
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=400, detail=cv_result["reason"])
        cv_status = "Verified"
        evidence_url = f"/static/uploads/{safe_filename}"

    new_row = RoadComplaint(
        complaint_id=new_id,
        date_reported=datetime.datetime.now().strftime("%d-%m-%Y"),
        city=city,
        area=area,
        issue_type=issue_type,
        description=f"[{triage['sentiment'].upper()}] {description}",
        status=cv_status,
        priority=triage['priority'],
        latitude="23.0225",
        longitude="72.5714",
        area_status="pending",
        evidence_url=evidence_url
    )
    db.add(new_row)
    db.commit()
    update_stats_cache(db)
    return {"status": "submitted", "id": new_id, "ai_triage": triage, "ai_cv": cv_status, "evidence_url": evidence_url}

@app.post("/api/submit/health")
async def submit_health(
    patient_id: str = Form(None),
    city: str = Form(...),
    area: str = Form(...),
    facility: str = Form(...),
    category: str = Form(...),
    complaint_text: str = Form(...),
    evidence: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    new_id = str(uuid.uuid4())
    
    # 1. AI Triage (NLP)
    triage = analyze_complaint_nlp(complaint_text)
    
    # 2. AI Image Verification (CV)
    cv_status = "No image"
    evidence_url = None
    if evidence and evidence.filename:
        file_extension = Path(evidence.filename).suffix
        safe_filename = f"{new_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        content = await evidence.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        cv_result = verify_image_cv(content)
        if not cv_result["verified"]:
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=400, detail=cv_result["reason"])
        cv_status = "Verified"
        evidence_url = f"/static/uploads/{safe_filename}"

    new_row = HealthComplaint(
        complaint_id=new_id,
        patient_id=patient_id or "Unknown",
        date_reported=datetime.datetime.now().strftime("%d-%m-%Y"),
        city=city,
        area=area,
        facility=facility,
        category=category,
        severity=triage['priority'], # Mapped Priority to Severity
        complaint_text=f"[{triage['sentiment'].upper()}] {complaint_text}",
        area_status="pending",
        evidence_url=evidence_url
    )
    db.add(new_row)
    db.commit()
    update_stats_cache(db)
    return {"status": "submitted", "id": new_id, "ai_triage": triage, "ai_cv": cv_status, "evidence_url": evidence_url}

@app.post("/api/submit/banking")
def submit_banking(
    account_id: str = Form(...),
    amount: str = Form(...),
    merchant_category: str = Form(...),
    transaction_type: str = Form(...),
    device_type: str = Form(...),
    location_city: str = Form(...),
    area: str = Form(...),
    db: Session = Depends(get_db)
):
    new_id = str(uuid.uuid4())
    
    # AI Predictive Analytics
    try:
        amt = float(amount)
    except:
        amt = 0.0
        
    hour = datetime.datetime.now().hour
    ai_risk = predict_fraud_risk(amt, hour, device_type)

    new_row = BankingFraud(
        transaction_id=new_id,
        account_id=account_id,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        amount=str(amt),
        merchant_category=merchant_category,
        transaction_type=transaction_type,
        device_type=device_type,
        location_city=location_city,
        risk_score=str(ai_risk["risk_score"]),
        is_fraud="1" if ai_risk["is_fraud_flag"] else "0",
        area_status=ai_risk["status"], # Dynamic area status based on ML Output
        area=area
    )
    db.add(new_row)
    db.commit()
    update_stats_cache(db)
    return {"status": "submitted", "id": new_id, "ai_prediction": ai_risk}

@app.get("/api/road/list/{city}/{area}")
def list_road_complaints(city: str, area: str, db: Session = Depends(get_db)):
    items = db.query(RoadComplaint).filter(RoadComplaint.city == city, RoadComplaint.area == area).all()
    return [to_dict(i) for i in items]

@app.get("/api/health/list/{city}/{area}")
def list_health_complaints(city: str, area: str, db: Session = Depends(get_db)):
    items = db.query(HealthComplaint).filter(HealthComplaint.city == city, HealthComplaint.area == area).all()
    return [to_dict(i) for i in items]

@app.get("/api/fraud/list/{city}/{area}")
def list_fraud_complaints(city: str, area: str, db: Session = Depends(get_db)):
    items = db.query(BankingFraud).filter(BankingFraud.location_city == city, BankingFraud.area == area).all()
    return [to_dict(i) for i in items]

@app.get("/api/track/{complaint_id}")
def track_complaint(complaint_id: str, db: Session = Depends(get_db)):
    # Search in road
    road = db.query(RoadComplaint).filter(RoadComplaint.complaint_id == complaint_id).first()
    if road:
        return {"type": "Road", "status": road.area_status or "pending", "details": to_dict(road)}
    
    # Search in health
    health = db.query(HealthComplaint).filter(HealthComplaint.complaint_id == complaint_id).first()
    if health:
        return {"type": "Health", "status": health.area_status or "pending", "details": to_dict(health)}
            
    # Search in banking
    fraud = db.query(BankingFraud).filter(BankingFraud.transaction_id == complaint_id).first()
    if fraud:
        return {"type": "Banking", "status": fraud.area_status or "pending", "details": to_dict(fraud)}
            
    raise HTTPException(404, "Complaint ID not found")

# --- Auto-Open ---
def open_dashboard():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000/dashboard/index.html")

if __name__ == "__main__":
    # Initial cache build with a temp session
    db = SessionLocal()
    try:
        update_stats_cache(db)
    finally:
        db.close()
        
    threading.Thread(target=open_dashboard).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
