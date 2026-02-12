import logging
import time
from datetime import datetime
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from typing import List, Dict, Optional
from .base import AIProvider
from .retry import retry_with_backoff, RetryError

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, timeout: float = 60.0):
        super().__init__(api_key, model, base_url, timeout)
        genai.configure(api_key=api_key)

    def generate_content(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            logger.error("[Gemini] Invalid API key")
            return None
        if not isinstance(self.model, str) or not self.model.strip():
            logger.error("[Gemini] Invalid model")
            return None
        if not isinstance(messages, list) or not messages:
            logger.error("[Gemini] Invalid messages payload")
            return None
        gemini_history = []
        system_instruction = ""
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction += content + "\n\n"
            elif role == "user":
                gemini_history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_history.append({"role": "model", "parts": [content]})
        
        if not gemini_history:
            return None
            
        last_message = gemini_history.pop()
        if last_message["role"] != "user":
            return None

        @retry_with_backoff(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=(
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
                google_exceptions.ResourceExhausted,
                ConnectionError,
                TimeoutError
            )
        )
        def _do_request() -> str:
            req_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            start_time = time.perf_counter()
            
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_instruction if system_instruction else None
            )
            
            chat = model.start_chat(history=gemini_history)
            
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            response = chat.send_message(
                last_message["parts"][0],
                generation_config=config,
                request_options={"timeout": self.timeout}
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response_text = response.text if response else ""
            body_size = len((response_text or "").encode("utf-8"))
            logger.info(
                f"[Gemini] Response: ts={req_ts} bytes={body_size} latency_ms={latency_ms}"
            )
            if not isinstance(response_text, str):
                raise ValueError("Missing response text")
            response_text = response_text.strip()
            if not response_text:
                raise ValueError("Empty response text")
            logger.info(
                f"[Gemini] Request completed: ts={req_ts} model={self.model} latency_ms={latency_ms}"
            )
            return response_text
        
        try:
            req_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            prompt_size = len((last_message.get("parts", [""])[0] or "").encode("utf-8"))
            logger.info(
                f"[Gemini] Request: ts={req_ts} model={self.model} prompt_bytes={prompt_size} timeout={self.timeout}"
            )
            return _do_request()
        except RetryError as e:
            logger.exception(f"[Gemini] All retries exhausted: {e.last_exception}")
            return None
        except Exception as e:
            logger.exception(f"[Gemini] Request failed: {e}")
            return None
