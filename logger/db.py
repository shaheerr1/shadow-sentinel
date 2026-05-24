import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
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

def log_prediction(input_text, model_a_label, model_a_score,
                   model_b_label, model_b_score, agreed):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO predictions
        (input_text, model_a_label, model_a_score, model_b_label, model_b_score, agreed)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (input_text, model_a_label, model_a_score,
          model_b_label, model_b_score, int(agreed)))
    conn.commit()
    conn.close()

def get_recent_predictions(limit=100):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, input_text, model_a_label, model_a_score,
               model_b_label, model_b_score, agreed
        FROM predictions
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_agreement_rate(limit=100):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT AVG(agreed) * 100
        FROM (
            SELECT agreed FROM predictions
            ORDER BY timestamp DESC
            LIMIT %s
        ) sub
    """, (limit,))
    result = c.fetchone()[0]
    conn.close()
    return round(float(result), 1) if result else 0.0