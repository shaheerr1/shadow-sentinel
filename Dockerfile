FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY models/    ./models/
COPY gateway/   ./gateway/
COPY logger/    ./logger/
COPY frontend/  ./frontend/

# Directory for persistent data
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]