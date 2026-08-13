import os
import re
import json
import joblib
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_LR_PATH = os.path.join(BASE_DIR, "model_lr.joblib")
MODEL_NB_PATH = os.path.join(BASE_DIR, "model_nb.joblib")
MODEL_RF_PATH = os.path.join(BASE_DIR, "model_rf.joblib")
VEC_PATH = os.path.join(BASE_DIR, "vectorizer.joblib")
METRICS_PATH = os.path.join(BASE_DIR, "metrics.json")

# Global models & vectorizer
vectorizer = None
model_lr = None
model_nb = None
model_rf = None
metrics_data = None

def load_models():
    global vectorizer, model_lr, model_nb, model_rf, metrics_data
    try:
        if os.path.exists(VEC_PATH) and os.path.exists(MODEL_LR_PATH):
            vectorizer = joblib.load(VEC_PATH)
            model_lr = joblib.load(MODEL_LR_PATH)
            if os.path.exists(MODEL_NB_PATH):
                model_nb = joblib.load(MODEL_NB_PATH)
            if os.path.exists(MODEL_RF_PATH):
                model_rf = joblib.load(MODEL_RF_PATH)
            if os.path.exists(METRICS_PATH):
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    metrics_data = json.load(f)
            print("Successfully loaded pre-trained models!")
        else:
            print("Model files not found yet. Run train_model.py first.")
    except Exception as e:
        print(f"Error loading models: {e}")

load_models()

# Known heuristic trigger keywords with categories & weights
TRIGGER_DICTIONARY = {
    "urgency": [
        "immediate", "urgently", "urgent", "act now", "limited time", "don't wait", 
        "expire", "expires", "expires today", "instant", "last chance", "action required", 
        "attention", "running out", "today only", "final notice"
    ],
    "financial": [
        "cash", "dollar", "dollars", "credit", "loan", "interest", "investment", 
        "profit", "stocks", "stock", "bonus", "guaranteed", "earn", "payout", 
        "wire transfer", "bank account", "mortgage", "refund", "100% free", "cheap", "discount"
    ],
    "phishing": [
        "click here", "login", "password", "suspended", "verify account", "confirm account",
        "update billing", "security alert", "unauthorized", "ebay", "paypal", "bank",
        "credit union", "unconditional", "identity", "misrepresentation"
    ],
    "promotional": [
        "cialis", "viagra", "pharmacy", "pills", "weight loss", "medz", "teeth whitening",
        "casino", "lottery", "winner", "prize", "jackpot", "unbelievable", "miracle", "software cds"
    ]
}

def clean_input(text):
    if not text:
        return ""
    text = re.sub(r'^Subject:\s*', '', text, flags=re.IGNORECASE)
    return text.strip()

def analyze_triggers(text):
    text_lower = text.lower()
    triggers = []
    
    # 1. Word / Phrase triggers
    for category, phrases in TRIGGER_DICTIONARY.items():
        for phrase in phrases:
            # find all occurrences
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            for match in pattern.finditer(text):
                triggers.append({
                    "phrase": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "category": category,
                    "explanation": f"High risk {category} trigger keyword/phrase."
                })

    # 2. Currency & Money Symbols
    currency_pattern = re.compile(r'(\$[\d,]+|\b\d+\s*dollars?\b|\b\d+%\s*off\b)', re.IGNORECASE)
    for match in currency_pattern.finditer(text):
        triggers.append({
            "phrase": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "category": "financial",
            "explanation": "Promotional currency/monetary value patterns detected."
        })

    # 3. Suspicious Links / URLs
    url_pattern = re.compile(r'(https?://[^\s]+|www\.[^\s]+|\b[a-z0-9.-]+\.(com|net|org|info|biz|site)\b)', re.IGNORECASE)
    for match in url_pattern.finditer(text):
        triggers.append({
            "phrase": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "category": "phishing",
            "explanation": "External hyperlink/domain reference detected."
        })

    # Deduplicate overlapping triggers
    triggers.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    dedup_triggers = []
    last_end = -1
    for tr in triggers:
        if tr["start"] >= last_end:
            dedup_triggers.append(tr)
            last_end = tr["end"]
            
    return dedup_triggers

def compute_signal_scores(text, triggers, spam_prob):
    # Urgency score (0-100)
    urgency_count = sum(1 for t in triggers if t["category"] == "urgency")
    urgency_score = min(100, int(urgency_count * 30 + (25 if "!" in text else 0)))

    # Financial score (0-100)
    financial_count = sum(1 for t in triggers if t["category"] == "financial")
    financial_score = min(100, int(financial_count * 25 + (30 if "$" in text else 0)))

    # Phishing score (0-100)
    phishing_count = sum(1 for t in triggers if t["category"] == "phishing")
    has_url = 1 if re.search(r'http|www|\.com|\.net', text, re.I) else 0
    phishing_score = min(100, int(phishing_count * 30 + has_url * 35))

    # Formatting Anomaly score (0-100)
    words = text.split()
    caps_words = sum(1 for w in words if w.isupper() and len(w) > 1)
    caps_ratio = (caps_words / max(1, len(words)))
    excl_count = text.count("!")
    anomaly_score = min(100, int(caps_ratio * 100 + min(40, excl_count * 10)))

    return {
        "urgency_score": urgency_score,
        "financial_score": financial_score,
        "phishing_score": phishing_score,
        "formatting_anomaly_score": anomaly_score
    }

def sanitize_text(text, triggers):
    # Sanitize / clean up suspicious wording for AI Spam Fixer innovation
    clean = text
    # Replace aggressive currency / urgency words
    replacements = {
        "act now": "please review at your convenience",
        "immediate action required": "action requested",
        "click here": "visit our official website",
        "100% free": "complimentary",
        "cheap": "affordable",
        "guaranteed": "assured",
        "buy now": "learn more",
        "urgent": "important"
    }
    for orig, rep in replacements.items():
        clean = re.sub(re.escape(orig), rep, clean, flags=re.IGNORECASE)

    # Remove excessive exclamation marks
    clean = re.sub(r'!{2,}', '!', clean)
    return clean

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return send_from_directory(".", path)
    return send_from_directory(".", "index.html")

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True) or {}
    text = data.get("text", "")
    
    cleaned = clean_input(text)
    if not cleaned:
        return jsonify({
            "error": "Empty text provided"
        }), 400

    triggers = analyze_triggers(text)
    
    # ML Prediction
    if vectorizer and model_lr:
        vec_text = vectorizer.transform([cleaned.lower()])
        
        # Logistic Regression
        prob_lr = float(model_lr.predict_proba(vec_text)[0][1])
        
        # Naive Bayes
        if model_nb:
            prob_nb = float(model_nb.predict_proba(vec_text)[0][1])
        else:
            prob_nb = prob_lr
            
        # Random Forest
        if model_rf:
            prob_rf = float(model_rf.predict_proba(vec_text)[0][1])
        else:
            prob_rf = prob_lr
            
        # Weighted Ensemble: LR 50%, NB 30%, RF 20%
        ensemble_prob = (prob_lr * 0.50) + (prob_nb * 0.30) + (prob_rf * 0.20)
    else:
        # Fallback heuristic score if model is not yet compiled
        trigger_weight = len(triggers) * 0.2
        ensemble_prob = min(0.99, max(0.05, trigger_weight))
        prob_lr = ensemble_prob
        prob_nb = ensemble_prob
        prob_rf = ensemble_prob

    is_spam = ensemble_prob >= 0.5
    confidence_pct = round(ensemble_prob * 100, 1) if is_spam else round((1 - ensemble_prob) * 100, 1)
    spam_pct = round(ensemble_prob * 100, 1)

    # Determine Risk Category
    if spam_pct >= 85:
        risk_level = "Critical Risk"
        risk_color = "danger"
    elif spam_pct >= 60:
        risk_level = "High Risk"
        risk_color = "warning"
    elif spam_pct >= 40:
        risk_level = "Moderate Risk"
        risk_color = "caution"
    else:
        risk_level = "Safe / Genuine Email"
        risk_color = "success"

    signals = compute_signal_scores(text, triggers, ensemble_prob)
    sanitized = sanitize_text(text, triggers)

    return jsonify({
        "status": "success",
        "prediction": "Spam" if is_spam else "Ham",
        "spam_probability": spam_pct,
        "confidence": confidence_pct,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "models": {
            "logistic_regression": round(prob_lr * 100, 1),
            "naive_bayes": round(prob_nb * 100, 1),
            "random_forest": round(prob_rf * 100, 1),
            "ensemble": spam_pct
        },
        "triggers": triggers,
        "signals": signals,
        "ai_suggestion": {
            "clean_rewrite": sanitized,
            "advice": "Remove urgent call-to-actions, aggressive financial symbols, and unverified hyperlinks to lower spam rating." if is_spam else "This message exhibits normal email formatting and legitimate phrasing."
        }
    })

@app.route("/api/batch", methods=["POST"])
def batch_predict():
    data = request.get_json(force=True) or {}
    items = data.get("messages", [])
    if not isinstance(items, list):
        return jsonify({"error": "messages must be a list"}), 400

    results = []
    for idx, item in enumerate(items[:50]):  # limit batch to 50 items
        text = str(item).strip()
        if not text:
            continue
        cleaned = clean_input(text)
        if vectorizer and model_lr:
            vec = vectorizer.transform([cleaned.lower()])
            prob = float(model_lr.predict_proba(vec)[0][1])
        else:
            prob = 0.1
        results.append({
            "id": idx + 1,
            "preview": text[:80] + ("..." if len(text) > 80 else ""),
            "prediction": "Spam" if prob >= 0.5 else "Ham",
            "score": round(prob * 100, 1)
        })

    return jsonify({
        "status": "success",
        "count": len(results),
        "results": results
    })

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    if metrics_data:
        return jsonify(metrics_data)
    elif os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    else:
        return jsonify({
            "status": "pending",
            "message": "Metrics not generated yet. Please run train_model.py."
        })

if __name__ == "__main__":
    print("Starting Apple-Style Spam Classifier Server on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
