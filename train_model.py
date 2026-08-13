import os
import re
import json
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Strip leading "Subject:" if present
    text = re.sub(r'^Subject:\s*', '', text, flags=re.IGNORECASE)
    # Convert text to lowercase
    text = text.lower()
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def train_and_evaluate():
    print("Loading emails dataset...")
    csv_path = os.path.join(os.path.dirname(__file__), "emails.csv")
    df = pd.read_csv(csv_path)
    
    print(f"Dataset loaded: {len(df)} records.")
    
    # Ensure correct column names
    if "text" not in df.columns or "spam" not in df.columns:
        raise ValueError("Dataset must contain 'text' and 'spam' columns.")

    df['cleaned_text'] = df['text'].apply(clean_text)
    
    X = df['cleaned_text']
    y = df['spam'].astype(int)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # Vectorizer
    print("Fitting TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        stop_words='english'
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    
    # Train Logistic Regression
    print("Training Logistic Regression...")
    clf_lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    clf_lr.fit(X_train_vec, y_train)
    y_pred_lr = clf_lr.predict(X_test_vec)
    
    # Train Naive Bayes
    print("Training Multinomial Naive Bayes...")
    clf_nb = MultinomialNB(alpha=0.1)
    clf_nb.fit(X_train_vec, y_train)
    y_pred_nb = clf_nb.predict(X_test_vec)
    
    # Train Random Forest
    print("Training Random Forest...")
    clf_rf = RandomForestClassifier(n_estimators=100, max_depth=20, random_state=42, n_jobs=-1)
    clf_rf.fit(X_train_vec, y_train)
    y_pred_rf = clf_rf.predict(X_test_vec)
    
    def get_metrics(y_true, y_pred):
        cm = confusion_matrix(y_true, y_pred).tolist()
        return {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "precision": round(float(precision_score(y_true, y_pred)), 4),
            "recall": round(float(recall_score(y_true, y_pred)), 4),
            "f1_score": round(float(f1_score(y_true, y_pred)), 4),
            "confusion_matrix": cm
        }

    metrics = {
        "dataset": {
            "total_emails": len(df),
            "spam_count": int((y == 1).sum()),
            "ham_count": int((y == 0).sum()),
            "train_count": len(X_train),
            "test_count": len(X_test)
        },
        "logistic_regression": get_metrics(y_test, y_pred_lr),
        "naive_bayes": get_metrics(y_test, y_pred_nb),
        "random_forest": get_metrics(y_test, y_pred_rf)
    }
    
    # Extract top spam indicator words from Logistic Regression coefficients
    feature_names = np.array(vectorizer.get_feature_names_out())
    coefs = clf_lr.coef_[0]
    top_spam_indices = np.argsort(coefs)[-25:][::-1]
    top_spam_words = [
        {"word": str(feature_names[i]), "weight": round(float(coefs[i]), 3)}
        for i in top_spam_indices
    ]
    metrics["top_spam_words"] = top_spam_words

    print("Saving models and metrics...")
    joblib.dump(vectorizer, os.path.join(os.path.dirname(__file__), "vectorizer.joblib"))
    joblib.dump(clf_lr, os.path.join(os.path.dirname(__file__), "model_lr.joblib"))
    joblib.dump(clf_nb, os.path.join(os.path.dirname(__file__), "model_nb.joblib"))
    joblib.dump(clf_rf, os.path.join(os.path.dirname(__file__), "model_rf.joblib"))
    
    with open(os.path.join(os.path.dirname(__file__), "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        
    print("Training complete successfully!")
    print(f"Logistic Regression Accuracy: {metrics['logistic_regression']['accuracy'] * 100:.2f}%")
    print(f"Naive Bayes Accuracy: {metrics['naive_bayes']['accuracy'] * 100:.2f}%")
    print(f"Random Forest Accuracy: {metrics['random_forest']['accuracy'] * 100:.2f}%")

if __name__ == "__main__":
    train_and_evaluate()
