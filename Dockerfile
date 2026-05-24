FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models at build time so startup is instant
RUN python -c "\
from transformers import pipeline; \
pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english'); \
pipeline('sentiment-analysis', model='siebert/sentiment-roberta-large-english'); \
print('Models cached.')"

COPY models/    ./models/
COPY gateway/   ./gateway/
COPY logger/    ./logger/
COPY frontend/  ./frontend/

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]