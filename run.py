"""
MLOps Batch Job — rolling mean signal pipeline
"""

import argparse
import json
import logging
import sys
import time

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="MLOps batch signal pipeline")
    parser.add_argument("--input",    required=True, help="Path to input CSV file")
    parser.add_argument("--config",   required=True, help="Path to YAML config file")
    parser.add_argument("--output",   required=True, help="Path to write metrics JSON")
    parser.add_argument("--log-file", required=True, dest="log_file",
                        help="Path to write log file")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_file_path: str) -> None:
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.FileHandler(log_file_path, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    try:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    if not isinstance(cfg, dict):
        raise ValueError("Config file is empty or not a valid YAML mapping")

    required_keys = ["seed", "window", "version"]
    for key in required_keys:
        if key not in cfg:
            raise ValueError(f"Missing required config key: '{key}'")

    if not isinstance(cfg["seed"], int):
        raise ValueError(f"Config 'seed' must be an integer, got: {type(cfg['seed']).__name__}")
    if not isinstance(cfg["window"], int) or cfg["window"] < 1:
        raise ValueError(f"Config 'window' must be a positive integer, got: {cfg['window']}")
    if not isinstance(cfg["version"], str) or not cfg["version"].strip():
        raise ValueError("Config 'version' must be a non-empty string")

    return cfg


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {path}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file '{path}': {e}")

    if df.empty:
        raise ValueError(f"Input file is empty: {path}")

    if "close" not in df.columns:
        raise ValueError(
            f"Required column 'close' not found. "
            f"Columns present: {list(df.columns)}"
        )

    if df["close"].isnull().all():
        raise ValueError("Column 'close' contains only null values")

    return df


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

def compute_signals(df: pd.DataFrame, window: int, seed: int) -> tuple[pd.DataFrame, int]:
    np.random.seed(seed)
    logging.info(f"Seed set: {seed}")

    df = df.copy()
    df["rolling_mean"] = df["close"].rolling(window=window).mean()
    logging.info(f"Rolling mean computed — window={window}, NaN rows={window - 1} (excluded)")

    # Drop rows where rolling_mean is NaN (first window-1 rows)
    df_valid = df.dropna(subset=["rolling_mean"]).copy()

    df_valid["signal"] = (df_valid["close"] > df_valid["rolling_mean"]).astype(int)
    rows_processed = len(df_valid)
    logging.info(f"Signals generated — valid rows={rows_processed}")

    return df_valid, rows_processed


# ---------------------------------------------------------------------------
# Metrics writer
# ---------------------------------------------------------------------------

def write_metrics(output_path: str, data: dict) -> None:
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    logging.info(f"Metrics written to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    setup_logging(args.log_file)

    logging.info("=" * 60)
    logging.info("Job started")
    logging.info(f"Input:    {args.input}")
    logging.info(f"Config:   {args.config}")
    logging.info(f"Output:   {args.output}")
    logging.info(f"Log file: {args.log_file}")
    logging.info("=" * 60)

    start_time = time.time()
    version = "unknown"

    try:
        # 1. Load + validate config
        cfg = load_config(args.config)
        version = cfg["version"]
        seed    = cfg["seed"]
        window  = cfg["window"]
        logging.info(f"Config loaded — seed={seed}, window={window}, version={version}")

        # 2. Load + validate data
        df = load_data(args.input)
        logging.info(f"Data loaded — {len(df)} rows, columns: {list(df.columns)}")

        # 3 + 4. Rolling mean + signal
        df_valid, rows_processed = compute_signals(df, window=window, seed=seed)

        # 5. Metrics
        signal_rate = round(float(df_valid["signal"].mean()), 4)
        latency_ms  = int((time.time() - start_time) * 1000)

        metrics = {
            "version":        version,
            "rows_processed": rows_processed,
            "metric":         "signal_rate",
            "value":          signal_rate,
            "latency_ms":     latency_ms,
            "seed":           seed,
            "status":         "success",
        }

        write_metrics(args.output, metrics)

        logging.info(f"Metrics summary — rows={rows_processed}, signal_rate={signal_rate}, latency={latency_ms}ms")
        logging.info("Job completed — status=success")
        logging.info("=" * 60)

        # Print final metrics to stdout (Docker requirement)
        print(json.dumps(metrics, indent=2))

        sys.exit(0)

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logging.error(f"Job failed: {e}")

        error_metrics = {
            "version":       version,
            "status":        "error",
            "error_message": str(e),
        }

        try:
            write_metrics(args.output, error_metrics)
        except Exception as write_err:
            logging.error(f"Also failed to write error metrics: {write_err}")

        logging.info("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
