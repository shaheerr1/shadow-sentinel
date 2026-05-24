import sqlite3
import os

DB_PATH = "shadow_sentinel.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            input_text TEXT,
            model_a_label TEXT,
            model_a_score REAL,
            model_b_label TEXT,
            model_b_score REAL,
            agreed INTEGER
        )
    """)
    conn.commit()
    conn.close()

def log_prediction(input_text, model_a_label, model_a_score, model_b_label, model_b_score, agreed):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO predictions 
        (input_text, model_a_label, model_a_score, model_b_label, model_b_score, agreed)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (input_text, model_a_label, model_a_score, model_b_label, model_b_score, int(agreed)))
    conn.commit()
    conn.close()

def get_recent_predictions(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, input_text, model_a_label, model_a_score,
               model_b_label, model_b_score, agreed
        FROM predictions
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_agreement_rate(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT AVG(agreed) * 100
        FROM (
            SELECT agreed FROM predictions
            ORDER BY timestamp DESC
            LIMIT ?
        )
    """, (limit,))
    result = c.fetchone()[0]
    conn.close()
    return round(result, 1) if result else 0.0