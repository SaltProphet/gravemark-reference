"""Minimal OpenAI-compatible local model adapter."""

import json
from dataclasses import dataclass
from urllib import request


class LocalModelError(Exception):
    """Transport or response error from the configured local model."""


@dataclass(frozen=True)
class LocalModelClient:
    base_url: str = ""
    model: str = ""
    timeout_seconds: float = 15.0

    @property
    def enabled(self) -> bool:
        return bool(self.base_url.strip() and self.model.strip())

    def generate_json(self, prompt: str) -> dict:
        if not self.enabled:
            raise LocalModelError("local model is disabled")
        url = self.base_url.rstrip("/")
        if not url.endswith("/v1"):
            url += "/v1"
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode("utf-8")
        req = request.Request(
            f"{url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer local-no-key"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as exc:
            raise LocalModelError("local model request failed") from exc
