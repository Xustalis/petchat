import logging
from typing import Optional
from .base import AIProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

GEMINI_MODEL_PREFIXES = ("gemini-", "models/gemini")


def create_provider(
    api_key: str,
    model: str,
    base_url: Optional[str] = None,
    timeout: float = 60.0,
    provider_type: str = "auto"
) -> AIProvider:
    provider_type = provider_type.lower().strip()
    
    if provider_type == "auto":
        provider_type = _detect_provider(model, base_url)
    
    if provider_type == "gemini":
        logger.info(f"[Factory] Creating GeminiProvider for model={model}")
        return GeminiProvider(api_key=api_key, model=model, base_url=base_url, timeout=timeout)
    
    logger.info(f"[Factory] Creating OpenAIProvider for model={model}, base_url={base_url}")
    return OpenAIProvider(api_key=api_key, model=model, base_url=base_url or "http://127.0.0.1:1235/v1", timeout=timeout)


def _detect_provider(model: str, base_url: Optional[str]) -> str:
    model_lower = model.lower()
    
    for prefix in GEMINI_MODEL_PREFIXES:
        if model_lower.startswith(prefix):
            return "gemini"
    
    if base_url and "generativelanguage.googleapis.com" in base_url:
        return "gemini"
    
    return "openai"
