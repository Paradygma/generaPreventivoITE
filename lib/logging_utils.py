"""Structured stdout logging so every step shows up in Vercel runtime logs."""

import json
import sys
import time


def log(event, **fields):
    """Print one JSON line to stdout: {"ts":..., "event": "...", ...fields}.

    Vercel captures stdout/stderr from serverless functions as runtime logs,
    so this is the only "dashboard" this function gets - keep every step visible."""
    record = {"ts": round(time.time(), 3), "event": event}
    record.update(fields)
    print(json.dumps(record, default=str, ensure_ascii=False), flush=True)


def log_error(event, exc, **fields):
    log(event, error=str(exc), error_type=type(exc).__name__, **fields)
    import traceback
    traceback.print_exc(file=sys.stdout)
