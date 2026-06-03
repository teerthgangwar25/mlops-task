FROM python:3.9-slim

WORKDIR /app

# Copy deps first — Docker caches this layer separately
# so code changes don't trigger a full pip reinstall
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files (includes data.csv, config.yaml, run.py)
COPY . .

CMD ["python", "run.py", \
     "--input",    "data.csv", \
     "--config",   "config.yaml", \
     "--output",   "metrics.json", \
     "--log-file", "run.log"]
