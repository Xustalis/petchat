import requests
import logging
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
from .base import AIProvider
from .retry import retry_with_backoff, RetryError

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "http://127.0.0.1:1235/v1", timeout: float = 60.0):
        super().__init__(api_key, model, base_url, timeout)
        self.base_url = self.base_url.rstrip('/')

    def generate_content(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            logger.error("[OpenAI] Invalid API key")
            return None
        if not isinstance(self.model, str) or not self.model.strip():
            logger.error("[OpenAI] Invalid model")
            return None
        if not isinstance(messages, list) or not messages:
            logger.error("[OpenAI] Invalid messages payload")
            return None
        if not isinstance(self.base_url, str) or not self.base_url.startswith("http"):
            logger.error("[OpenAI] Invalid base URL")
            return None
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        
        @retry_with_backoff(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=(requests.Timeout, requests.ConnectionError, ConnectionError)
        )
        def _do_request() -> str:
            req_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            start_time = time.perf_counter()
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            body_size = len(response.content or b"")
            logger.info(
                f"[OpenAI] Response: ts={req_ts} status={response.status_code} bytes={body_size} latency_ms={latency_ms}"
            )
            response.raise_for_status()
            
            data = response.json()
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError("Missing choices in response")
            first_choice = choices[0] if isinstance(choices[0], dict) else {}
            message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str):
                content = first_choice.get("text") if isinstance(first_choice, dict) else None
            if not isinstance(content, str):
                delta = first_choice.get("delta") if isinstance(first_choice, dict) else None
                content = delta.get("content") if isinstance(delta, dict) else None
            if not isinstance(content, str):
                raise ValueError("Missing content in response")
            content = content.strip()
            if not content:
                raise ValueError("Empty content in response")

            logger.info(
                f"[OpenAI] Request completed: ts={req_ts} model={self.model} payload_bytes={payload_size} latency_ms={latency_ms}"
            )
            return content
        
        try:
            req_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            logger.info(
                f"[OpenAI] Request: ts={req_ts} url={url} model={self.model} payload_bytes={payload_size} timeout={self.timeout}"
            )
            return _do_request()
        except RetryError as e:
            logger.exception(f"[OpenAI] All retries exhausted: {e.last_exception}")
            return None
        except requests.HTTPError as e:
            resp = getattr(e, "response", None)
            status = resp.status_code if resp else "unknown"
            size = len(resp.content or b"") if resp else 0
            logger.exception(
                f"[OpenAI] HTTP error (not retried): ts={datetime.utcnow().isoformat(timespec='seconds')}Z status={status} bytes={size}"
            )
            return None
        except (KeyError, IndexError, ValueError, TypeError) as e:
            logger.exception(f"[OpenAI] Failed to parse response: {e}")
            return None
        except Exception as e:
            logger.exception(f"[OpenAI] Request failed: {e}")
            return None
