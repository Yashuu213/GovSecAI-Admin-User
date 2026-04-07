from api.database import engine, Base
from api.models import RoadComplaint, HealthComplaint, BankingFraud

try:
    print("[*] Creating Tables...")
    Base.metadata.create_all(bind=engine)
    print("[+] Tables Created successfully.")
except Exception as e:
    print(f"[!] Error: {e}")
