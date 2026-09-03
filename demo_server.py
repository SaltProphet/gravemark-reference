"""Small local server for the public Gravemark reference console."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from gravemark.enrichment import enrich_finding
from gravemark.evidence import Evidence
from gravemark.local_model import LocalModelClient
from gravemark.pipeline import run_pipeline


ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures"


def _evidence_from_dict(item: dict) -> Evidence:
    return Evidence(
        evidence_id=item["evidence_id"], source_id=item["source_id"], pattern_id=item["pattern_id"],
        quote=item["quote"], matched_terms=tuple(item["matched_terms"]),
        sentence_index=item["sentence_index"], start_char=item["start_char"], end_char=item["end_char"],
        deterministic_score=item["deterministic_score"], provenance=tuple(sorted(item.get("provenance", {}).items())),
    )


def _local_client() -> LocalModelClient:
    return LocalModelClient(
        base_url=os.getenv("GRAVEMARK_LOCAL_MODEL_URL", ""),
        model=os.getenv("GRAVEMARK_LOCAL_MODEL", ""),
        timeout_seconds=float(os.getenv("GRAVEMARK_LOCAL_MODEL_TIMEOUT", "15")),
    )


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/fixtures":
            fixtures = []
            for item in sorted(FIXTURES.glob("*.json")):
                fixtures.append({"id": item.name, "label": item.stem.replace("_", " ").title(), "records": json.loads(item.read_text(encoding="utf-8"))})
            return self._send(200, {"fixtures": fixtures})
        if path == "/api/health":
            return self._send(200, {"status": "ok", "analysis": "enabled" if _local_client().enabled else "disabled"})
        if path in {"/", "/index.html"}:
            return self._send(200, (ROOT / "web" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path in {"/app.js", "/styles.css"}:
            kind = "application/javascript" if path.endswith(".js") else "text/css"
            return self._send(200, (ROOT / "web" / path.lstrip("/")).read_bytes(), kind)
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/run":
                return self._send(200, run_pipeline(payload.get("source_records", [])))
            if path == "/api/enrich":
                evidence = {_item["evidence_id"]: _evidence_from_dict(_item) for _item in payload.get("detected_evidence", [])}
                return self._send(200, enrich_finding(payload["candidate_finding"], evidence, _local_client()))
            return self._send(404, {"error": "not found"})
        except Exception as exc:
            return self._send(400, {"error": str(exc)})

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    print("Gravemark console: http://127.0.0.1:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
