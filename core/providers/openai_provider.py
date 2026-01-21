import requests
import logging
import time
from typing import List, Dict, Optional
from .base import AIProvider
from .retry import retry_with_backoff, RetryError

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "http://127.0.0.1:1235/v1", timeout: float = 60.0):
        super().__init__(api_key, model, base_url, timeout)
        self.base_url = self.base_url.rstrip('/')

    def generate_content(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
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
        
        @retry_with_backoff(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=(requests.Timeout, requests.ConnectionError, ConnectionError)
        )
        def _do_request() -> str:
            start_time = time.perf_counter()
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"[OpenAI] Request completed: model={self.model}, latency={latency_ms}ms")
            return content
        
        try:
            return _do_request()
        except RetryError as e:
            logger.error(f"[OpenAI] All retries exhausted: {e.last_exception}")
            return None
        except requests.HTTPError as e:
            logger.error(f"[OpenAI] HTTP error (not retried): {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"[OpenAI] Failed to parse response: {e}")
            return None
