# Shadow Sentinel

A production-grade MLOps system for shadow deployment monitoring. Run a challenger model silently alongside production, detect divergence in real time, diagnose root causes automatically, and gate promotion through a CI/CD pipeline.

**Live demo:** https://shadow-sentinel-1092599030143.europe-west2.run.app

---

## The Problem

Most teams focus on building models. Very few focus on what happens after deployment. A model can perform well in training but silently degrade in production due to data drift, distribution shift, or behavioural changes in users. By the time someone notices, the damage is done.

Shadow Sentinel addresses this by running a challenger model in parallel with production, monitoring their agreement in real time, and making automated promotion or rollback decisions.

---

## Architecture

```
User Request
     ↓
FastAPI Gateway
     ↓          ↓
Model A        Model B
(Production)   (Challenger)
     ↓          ↓
Comparison Layer
     ↓
PostgreSQL (Supabase)
     ↓
Live Dashboard + Automated Diagnosis
     ↓
GitHub Actions → Promote or Rollback
```

---

## Features

- **Shadow deployment** — challenger model runs silently on all live traffic
- **Real-time monitoring** — agreement rate tracked across every prediction
- **Automated diagnosis** — detects high-confidence conflicts, informal language sensitivity, short input failures
- **CI/CD pipeline** — GitHub Actions runs tests, validates models, checks shadow deployment, and gates promotion
- **Production dashboard** — live metrics, rolling agreement chart, prediction table, root cause analysis
- **Persistent storage** — PostgreSQL via Supabase, survives container restarts and multi-instance deployments

---

## Tech Stack

| Layer            | Technology               |
| ---------------- | ------------------------ |
| API Gateway      | FastAPI                  |
| ML Models        | HuggingFace Transformers |
| Database         | PostgreSQL (Supabase)    |
| Dashboard        | Vanilla JS + Chart.js    |
| Containerisation | Docker + Docker Compose  |
| Deployment       | Google Cloud Run         |
| CI/CD            | GitHub Actions           |

---

## Models

- **Model A (Production):** `distilbert-base-uncased-finetuned-sst-2-english` — trained on movie reviews
- **Model B (Challenger):** `siebert/sentiment-roberta-large-english` — trained on diverse English text

The two models deliberately differ in training data to demonstrate realistic divergence patterns. Model A tends to be more decisive on informal language while Model B is more conservative, creating natural disagreement on edge cases.

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/shaheerr1/shadow-sentinel
cd shadow-sentinel

# Set environment variables
echo "DATABASE_URL=your_supabase_connection_string" > .env

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn gateway.main:app --reload
```

Open `http://localhost:8000` for the dashboard and `http://localhost:8000/docs` for the API.

**With Docker:**

```bash
docker-compose up
```

---

## API Endpoints

| Endpoint   | Method | Description                                   |
| ---------- | ------ | --------------------------------------------- |
| `/predict` | POST   | Run text through both models, log comparison  |
| `/stats`   | GET    | Agreement rate, diagnosis, recent predictions |
| `/health`  | GET    | Health check                                  |
| `/docs`    | GET    | Interactive API documentation                 |

**Example request:**

```bash
curl -X POST https://shadow-sentinel-1092599030143.europe-west2.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is absolutely amazing"}'
```

**Example response:**

```json
{
  "prediction": "positive",
  "model_a": { "label": "positive", "score": 0.999 },
  "model_b": { "label": "positive", "score": 0.998 },
  "agreed": true,
  "agreement_rate": 83.3
}
```

---

## CI/CD Pipeline

On every push to `main`:

1. **Unit tests** — validate routes, response structure, model behaviour
2. **Shadow deployment check** — calls live `/stats` endpoint, reads agreement rate and conflict data
3. **Automated decision:**
   - Agreement ≥ 80% and zero critical conflicts → **PROMOTE**
   - Agreement ≥ 80% but critical conflicts detected → **HOLD**
   - Agreement < 80% → **ROLLBACK**

The pipeline uses GitHub Secrets for `DATABASE_URL` and `DEPLOY_URL` — no credentials are ever hardcoded.

---

## Automated Diagnosis

The diagnosis engine categorises failures beyond a simple agreement rate:

**Critical — High-confidence conflicts**
Both models are highly confident (>80%) but reach opposite conclusions. This is the most dangerous failure mode — in production it would silently serve wrong predictions with high confidence.

**Warning — Informal language sensitivity**
Model B misclassifies slang and informal text. Real users communicate this way constantly. This signals distribution shift — the model was not exposed to the actual language patterns present in production traffic.

**Warning — Short input sensitivity**
Model B struggles with short, context-sparse inputs. It may be over-relying on surface patterns that break down when there is minimal text to analyse.

---

## Key Engineering Decisions

**Why PostgreSQL instead of SQLite?**
SQLite breaks in multi-instance cloud deployments — each container instance has its own filesystem and therefore its own database. Discovered this during deployment when predictions written to one Cloud Run instance were invisible to another. Replaced with Supabase PostgreSQL which is shared across all instances.

**Why shadow deployment over A/B testing?**
A/B testing exposes real users to potentially worse predictions. Shadow deployment runs the challenger silently — users always get the production model's response while the system evaluates whether the challenger is ready.

**Why automated diagnosis?**
Agreement rate alone does not tell you why a model is failing. The diagnosis engine categorises failures by type — high-confidence conflicts are more dangerous than low-confidence disagreements, and informal language sensitivity points to a specific retraining need.

---

## Project Structure

```
shadow-sentinel/
├── gateway/
│   └── main.py              # FastAPI app, routing, diagnosis logic
├── models/
│   └── model_loader.py      # HuggingFace model loading
├── logger/
│   └── db.py                # PostgreSQL connection and queries
├── frontend/
│   └── index.html           # Single-file production dashboard
├── tests/
│   └── test_gateway.py      # Unit tests with mocked models
├── scripts/
│   └── shadow_check.py      # CI/CD shadow deployment check script
├── .github/
│   └── workflows/
│       └── ml-pipeline.yml  # GitHub Actions CI/CD pipeline
├── Dockerfile               # Multi-stage build with baked models
└── docker-compose.yml       # Local development setup
```

---

## What I Learned

Deploying ML models is the easy part. Keeping them reliable in production is the real engineering challenge.

This project taught me that distribution shift, confidence calibration, and multi-instance storage are problems you only discover after deployment — which is exactly why shadow deployment and automated monitoring exist. The most interesting moment was discovering that SQLite breaks silently in Cloud Run when traffic routes to different container instances. That single failure pointed directly to why production systems use shared databases.

The broader insight: the gap between a model that works in a notebook and a model that works reliably in production for 12 months is enormous. Most ML education stops at the notebook. This project starts where that stops.

---

## Roadmap

- [ ] Replace agreement rate threshold with statistical significance testing
- [ ] Add Slack/email alerting on rollback decisions
- [ ] Support multi-model comparison (more than two models)
- [ ] Add data drift detection on input features
- [ ] Migrate from Cloud Run to Kubernetes for persistent volume support
