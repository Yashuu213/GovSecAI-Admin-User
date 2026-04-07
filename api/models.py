from sqlalchemy import Column, Integer, String
from database import Base

class RoadComplaint(Base):
    __tablename__ = "road_complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, index=True)
    date_reported = Column(String)
    city = Column(String, index=True)
    area = Column(String, index=True)
    issue_type = Column(String)
    description = Column(String)
    status = Column(String)
    priority = Column(String)
    latitude = Column(String)
    longitude = Column(String)
    area_status = Column(String)
    evidence_url = Column(String)

class HealthComplaint(Base):
    __tablename__ = "health_complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, index=True)
    patient_id = Column(String)
    date_reported = Column(String)
    city = Column(String, index=True)
    area = Column(String, index=True)
    facility = Column(String)
    category = Column(String)
    severity = Column(String)
    complaint_text = Column(String)
    area_status = Column(String)
    evidence_url = Column(String)

class BankingFraud(Base):
    __tablename__ = "banking_fraud"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, index=True)
    account_id = Column(String)
    timestamp = Column(String)
    amount = Column(String)
    merchant_category = Column(String)
    transaction_type = Column(String)
    device_type = Column(String)
    location_city = Column(String, index=True)
    risk_score = Column(String)
    is_fraud = Column(String)
    area_status = Column(String)
    area = Column(String, index=True)
