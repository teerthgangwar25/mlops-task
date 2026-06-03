# MLOps Batch Job — Rolling Mean Signal Pipeline

A minimal MLOps-style batch job demonstrating reproducibility, observability, and deployment readiness.

---

## What it does

1. Loads configuration from `config.yaml`
2. Reads an OHLCV CSV dataset
3. Computes a rolling mean on the `close` column
4. Generates a binary signal: `1` if `close > rolling_mean`, else `0`
5. Writes structured metrics JSON and detailed logs

---

## Project structure

```
mlops-task/
├── run.py            # main pipeline script
├── config.yaml       # seed, window, version
├── data.csv          # 10,000-row OHLCV dataset
├── requirements.txt  # pinned dependencies
├── Dockerfile        # containerised run
├── README.md         # this file
├── metrics.json      # sample output from a successful run
└── run.log           # sample log from a successful run
```

---

## Local run

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Run the pipeline**

```bash
python run.py \
  --input    data.csv \
  --config   config.yaml \
  --output   metrics.json \
  --log-file run.log
```

**3. Check outputs**

```bash
cat metrics.json
cat run.log
```

---

## Docker

**Build**

```bash
docker build -t mlops-task .
```

**Run**

```bash
docker run --rm mlops-task
```

The container includes `data.csv` and `config.yaml`. It prints the final metrics JSON to stdout and exits `0` on success, non-zero on failure.

---

## CLI reference

| Flag | Required | Description |
|------|----------|-------------|
| `--input` | Yes | Path to input CSV file |
| `--config` | Yes | Path to YAML config file |
| `--output` | Yes | Path to write metrics JSON |
| `--log-file` | Yes | Path to write log file |

---

## Config format (`config.yaml`)

```yaml
seed: 42       # integer — sets numpy random seed for determinism
window: 5      # integer — rolling mean window size
version: "v1"  # string — stamped into metrics output
```

---

## Example `metrics.json`

```json
{
  "version": "v1",
  "rows_processed": 9996,
  "metric": "signal_rate",
  "value": 0.4991,
  "latency_ms": 24,
  "seed": 42,
  "status": "success"
}
```

On error:

```json
{
  "version": "v1",
  "status": "error",
  "error_message": "Missing required column: close"
}
```

---

## Design notes

- **Determinism**: `numpy.random.seed(seed)` is set before any computation. Same config always produces the same output.
- **NaN handling**: The first `window - 1` rows produce a NaN rolling mean and are excluded from signal computation. `rows_processed` reflects only valid rows.
- **Error handling**: All failures (missing file, bad CSV, missing column, invalid config) write an error `metrics.json` and exit with code `1`.
- **No hardcoded paths**: all paths come from CLI flags only.
