import cv2
import numpy as np
from textblob import TextBlob
from sklearn.ensemble import RandomForestClassifier
import random

# ==========================================
# 1. Automated Triage (NLP)
# ==========================================
def analyze_complaint_nlp(text: str):
    """
    Analyzes complaint text to determine sentiment and assign priority.
    Uses TextBlob for rapid local sentiment analysis without heavy LLMs.
    """
    if not text:
        return {"sentiment": "neutral", "score": 0.0, "priority": "Medium"}
        
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # Range: -1 (negative) to 1 (positive)
    
    # Priority Heuristics
    text_lower = text.lower()
    urgent_keywords = ["urgent", "emergency", "accident", "blood", "death", "critical", "severe", "fatal"]
    
    is_urgent = any(word in text_lower for word in urgent_keywords)
    
    if polarity < -0.4 or is_urgent:
        priority = "High"
    elif polarity > 0.4 and not is_urgent:
        priority = "Low"
    else:
        priority = "Medium"
        
    sentiment_label = "negative" if polarity < 0 else "positive" if polarity > 0 else "neutral"
    
    return {
        "sentiment": sentiment_label,
        "score": round(polarity, 2),
        "priority": priority
    }


# ==========================================
# 2. Computer Vision (Image Verification)
# ==========================================
def verify_image_cv(file_bytes: bytes):
    """
    Fast image analysis using OpenCV.
    Calculates structural complexity (edges/variance) to verify if an image 
    actually contains anomalous features (like potholes or accumulated garbage)
    rather than just a flat surface (spam image).
    """
    try:
        # Convert bytes to numpy array for OpenCV
        nparr = np.frombuffer(file_bytes, np.uint8)
        # --- Standardization: Resize for consistent analysis ---
        img_color = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_color = cv2.resize(img_color, (256, 256))
        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        
        # 1. Texture Check (Laplacian Variance)
        # Real photos have natural grain/detail. Cartoons are often too "clean".
        texture_score = cv2.Laplacian(img_gray, cv2.CV_64F).var()
        
        # 2. Saturation Check (HSV)
        hsv = cv2.cvtColor(img_color, cv2.COLOR_BGR2HSV)
        avg_saturation = np.mean(hsv[:,:,1])
        
        # 3. Color Depth (Unique Grayscale values)
        unique_shades = len(np.unique(img_gray))
        
        # 4. Structural Complexity (Canny Edge Density)
        edges = cv2.Canny(img_gray, 100, 200)
        edge_density = np.sum(edges) / 255.0
        
        is_verified = True
        reason = "Photo evidence verified."
        
        # --- Strict Thresholds ---
        if avg_saturation > 145: 
            is_verified = False
            reason = "Image detected as a graphic/cartoon (Hyper-Saturation)."
        elif unique_shades < 90:
            is_verified = False
            reason = "Image too flat/unrealistic (Low Color Depth)."
        elif texture_score < 100: # Real photos usually have variance > 100
            is_verified = False
            reason = "Image lacks realistic texture (Too Smooth/Blurry)."
        elif edge_density < 300: # Standardized for 256x256
            is_verified = False
            reason = "Image is too simple or out of focus."
            
        return {
            "verified": is_verified,
            "texture": round(texture_score, 1),
            "vibrancy": round(avg_saturation, 1),
            "shades": unique_shades,
            "edges": round(edge_density, 1),
            "reason": reason
        }
    except Exception as e:
        return {"verified": False, "score": 0, "reason": f"CV Processing Error: {str(e)}"}


# ==========================================
# 3. Predictive Analytics (Fraud ML Model)
# ==========================================
# Initialize and train a micro-model in-memory on module load for blazing fast predictions.
_fraud_model = RandomForestClassifier(n_estimators=10, random_state=42)

def _train_mock_fraud_model():
    """Trains a micro-RandomForest on synthetic data patterns representing fraud."""
    # Features: [Amount, Hour_of_Day, Device_Risk (0=Mobile, 1=Unknown/Desktop), Prior_Issues]
    X_train = [
        [50, 14, 0, 0],    # Normal coffee purchase
        [500, 11, 0, 0],   # Normal grocery
        [15000, 3, 1, 1],  # Huge transfer, 3 AM, Unknown Device, Prior issues -> Fraud
        [20000, 2, 1, 0],  # Huge transfer, 2 AM -> Fraud
        [100, 18, 0, 1],   # Small transfer but prior issues -> Suspicious
        [10, 1, 1, 0],     # Random micro-charge -> Normal
    ]
    # 0 = Safe, 1 = Fraud
    y_train = [0, 0, 1, 1, 1, 0]
    _fraud_model.fit(X_train, y_train)

# Execute fast training
_train_mock_fraud_model()

def predict_fraud_risk(amount: float, hour: int, device_type: str):
    """
    Predicts the risk percentage of a transaction using the trained Random Forest.
    """
    device_risk = 1 if device_type.lower() in ["desktop", "unknown", "tablet"] else 0
    # Simulate a "prior issues" flag randomly for demonstration unpredictability, 
    # normally this would be a DB lookup for the account.
    prior_issues = 1 if random.random() > 0.8 else 0 
    
    features = [[amount, hour, device_risk, prior_issues]]
    
    # Predict probability of class '1' (Fraud)
    probabilities = _fraud_model.predict_proba(features)
    risk_score_percentage = probabilities[0][1] * 100
    
    # Determine Status
    if risk_score_percentage > 70:
        status = "high_risk"
    elif risk_score_percentage > 40:
        status = "suspicious"
    else:
        status = "safe"
        
    return {
        "risk_score": round(risk_score_percentage, 1),
        "status": status,
        "is_fraud_flag": risk_score_percentage > 70
    }
