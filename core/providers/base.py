from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class AIProvider(ABC):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    @abstractmethod
    def generate_content(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
        pass
