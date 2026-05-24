from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.model_loader import load_models
from logger.db import init_db, log_prediction, get_agreement_rate

DATABASE_URL = os.getenv("DATABASE_URL")

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

def generate_diagnosis(df):
    disagreements = df[df["agreed"] == 0]

    if len(disagreements) == 0:
        return {
            "issues": [],
            "recommendation": "✅ No issues detected. Models are in full agreement. Continue monitoring.",
            "high_conf_conflicts": 0,
            "avg_confidence_gap": 0
        }

    issues = []

    high_conf = disagreements[
        (disagreements["model_a_score"] > 0.8) &
        (disagreements["model_b_score"] > 0.8)
    ]
    if len(high_conf) > 0:
        issues.append({
            "severity": "critical",
            "title": f"High-confidence conflicts ({len(high_conf)})",
            "detail": "Both models are highly confident but reach opposite conclusions. This is not random noise — it signals Model B has learned a fundamentally different decision boundary. In production, this would silently serve wrong predictions with high confidence, which is the most dangerous failure mode."
        })

    slang_words = ["ngl", "lol", "slaps", "meh", "lowkey", "idk", "tbh", "imo",
                   "bruh", "mid", "fire", "trash", "lit", "cap", "bussin"]
    informal_fails = disagreements[
        disagreements["input_text"].str.lower().apply(
            lambda x: any(w in str(x).split() for w in slang_words)
        )
    ]
    if len(informal_fails) > 0:
        issues.append({
            "severity": "warning",
            "title": f"Informal language sensitivity ({len(informal_fails)})",
            "detail": "Model B misclassifies informal or slang-heavy text. Real users communicate this way constantly. This is a distribution shift problem — the model was not exposed to the actual language patterns present in production traffic."
        })

    short_fails = disagreements[disagreements["input_text"].str.split().str.len() <= 5]
    already_counted = set(informal_fails.index)
    new_short = short_fails[~short_fails.index.isin(already_counted)]
    if len(new_short) > 0:
        issues.append({
            "severity": "warning",
            "title": f"Short input sensitivity ({len(new_short)})",
            "detail": "Model B struggles with short, context-sparse inputs. It may be over-relying on surface patterns that break down when there is minimal text to analyse — a common failure mode for models trained on longer content."
        })

    conf_gap = (disagreements["model_a_score"] - disagreements["model_b_score"]).abs().mean()
    conf_gap = float(conf_gap) if not pd.isna(conf_gap) else 0.0

    rate = df["agreed"].mean() * 100
    has_critical = any(i["severity"] == "critical" for i in issues)

    if rate < 50:
        rec = "🚨 Immediate rollback required. Agreement rate is critically low. Model B must not be promoted under any circumstances until retrained."
    elif rate < 80 and has_critical:
        rec = "🚨 Rollback recommended. High-confidence conflicts combined with low agreement rate indicate Model B is systematically unreliable. Retrain on a more diverse dataset that includes informal language and short-form text."
    elif rate < 80:
        rec = "⚠️ Rollback recommended. Agreement rate is below the 80% threshold. Investigate disagreement patterns and retrain Model B on production-representative data."
    elif has_critical:
        rec = "⚠️ Do not promote yet. Agreement rate is acceptable but high-confidence conflicts suggest systematic bias that could worsen at scale. Expand the monitoring window."
    else:
        rec = "✅ Model B appears stable. Extend the monitoring window to 500+ predictions before making a final promotion decision."

    return {
        "issues": issues,
        "recommendation": rec,
        "high_conf_conflicts": int(len(high_conf)),
        "avg_confidence_gap": round(conf_gap * 100, 1)
    }

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
    init_db()
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql_query(
        "SELECT * FROM predictions ORDER BY timestamp ASC",
        conn
    )
    conn.close()

    if df.empty:
        return {
            "agreement_rate": 0, "total": 0, "disagreements": 0,
            "model_b_status": "no_data", "chart_data": [], "recent": [],
            "diagnosis": {
                "issues": [], "recommendation": "No data yet.",
                "high_conf_conflicts": 0, "avg_confidence_gap": 0
            }
        }

    df["rolling"] = df["agreed"].rolling(5, min_periods=1).mean() * 100
    chart_data = [{"index": i + 1, "value": round(row["rolling"], 1)}
                  for i, (_, row) in enumerate(df.iterrows())]

    recent = df.sort_values("timestamp", ascending=False).head(15)
    recent_list = recent[["timestamp", "input_text", "model_a_label", "model_a_score",
                           "model_b_label", "model_b_score", "agreed"]].to_dict("records")

    rate = round(df.tail(100)["agreed"].mean() * 100, 1)
    diagnosis = generate_diagnosis(df.tail(100))
    has_critical = diagnosis.get("high_conf_conflicts", 0) > 0

    return {
        "agreement_rate": rate,
        "total": len(df),
        "disagreements": int((df["agreed"] == 0).sum()),
        "model_b_status": "promotable" if (rate >= 80 and not has_critical) else "unstable",
        "chart_data": chart_data,
        "recent": recent_list,
        "diagnosis": diagnosis
    }

@app.get("/health")
def health():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")