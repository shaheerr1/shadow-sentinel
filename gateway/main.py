from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, os, sqlite3
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.model_loader import load_models
from logger.db import init_db, log_prediction, get_agreement_rate

app = FastAPI(title="Shadow Sentinel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model_a, model_b = None, None

class PredictRequest(BaseModel):
    text: str

@app.on_event("startup")
def startup():
    global model_a, model_b
    init_db()
    model_a, model_b = load_models()

@app.post("/predict")
def predict(req: PredictRequest):
    result_a = model_a(req.text)[0]
    result_b = model_b(req.text)[0]
    label_a = result_a["label"].lower()
    label_b = result_b["label"].lower()
    agreed = label_a == label_b
    log_prediction(req.text, label_a, result_a["score"], label_b, result_b["score"], agreed)
    return {
        "prediction": label_a,
        "model_a": {"label": label_a, "score": round(result_a["score"], 3)},
        "model_b": {"label": label_b, "score": round(result_b["score"], 3)},
        "agreed": agreed,
        "agreement_rate": get_agreement_rate()
    }

@app.get("/stats")
def stats():
    init_db()  # ensures table exists even if db was wiped
    conn = sqlite3.connect("shadow_sentinel.db")
    df = pd.read_sql_query("SELECT * FROM predictions ORDER BY timestamp ASC", conn)
    conn.close()

    if df.empty:
        return {"agreement_rate": 0, "total": 0, "disagreements": 0,
                "model_b_status": "no_data", "chart_data": [], "recent": []}

    df["rolling"] = df["agreed"].rolling(5, min_periods=1).mean() * 100
    chart_data = [{"index": i + 1, "value": round(row["rolling"], 1)}
                  for i, (_, row) in enumerate(df.iterrows())]

    recent = df.sort_values("timestamp", ascending=False).head(15)
    recent_list = recent[["timestamp", "input_text", "model_a_label", "model_a_score",
                           "model_b_label", "model_b_score", "agreed"]].to_dict("records")

    rate = round(df.tail(100)["agreed"].mean() * 100, 1)

    return {
        "agreement_rate": rate,
        "total": len(df),
        "disagreements": int((df["agreed"] == 0).sum()),
        "model_b_status": "promotable" if rate >= 80 else "unstable",
        "chart_data": chart_data,
        "recent": recent_list
    }

@app.get("/health")
def health():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")