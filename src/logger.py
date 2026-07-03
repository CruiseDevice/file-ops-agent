import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.load import dumpd

LOG_DIR = Path(__file__).parent.parent / "logs" / "runs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_run(messages: list, final_response: str, latency: float, error: str | None = None) -> Path:
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()
    log_file = LOG_DIR / f"{timestamp.replace(':', '-')}_{run_id}.json"

    log_entry = {                                                         
        "run_id": run_id,
        "timestamp": timestamp,
        "query": _extract_query(messages),
        "messages": [dumpd(m) for m in messages],
        "final_response": final_response,
        "latency_seconds": latency,
        "error": error,
    }

    log_file.write_text(json.dumps(log_entry, indent=2, default=str), encoding="utf-8")

    return log_file


def _extract_query(messages: list) -> str:                                
    for m in messages:
        if getattr(m, "type", None) == "human":
            return str(m.content)
    return ""