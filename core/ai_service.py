"""AI service integration for emotion recognition, memory extraction, and decision support.
Uses provider abstraction for compatibility with multiple AI backends (OpenAI, Gemini, local LLMs).
"""
import os
import json
import logging
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Optional
from dotenv import load_dotenv

from core.providers import create_provider, AIProvider
from core.providers.retry import CircuitBreaker

load_dotenv()

logger = logging.getLogger(__name__)


class AIService:
    """Handles all AI-related operations through unified provider interface"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, 
                 model: Optional[str] = None, timeout: float = 60.0,
                 provider_type: str = "auto", circuit_failure_threshold: int = 5,
                 circuit_recovery_timeout: float = 60.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "lm-studio")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1235/v1")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout = timeout
        
        self.api_base = self.api_base.rstrip('/')
        
        self.provider: AIProvider = create_provider(
            api_key=self.api_key,
            model=self.model,
            base_url=self.api_base,
            timeout=self.timeout,
            provider_type=provider_type
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout
        )
        self._metrics_lock = threading.Lock()
        self.total_requests = 0
        self.success_requests = 0
        self.failure_requests = 0
        self.consecutive_failures = 0
        self.last_alert_ts = 0.0
        logger.info(f"[AIService] Initialized with provider: {type(self.provider).__name__}")
    
    def _make_request(self, messages: List[Dict], temperature: float = 0.3, 
                      max_tokens: int = 500) -> Optional[str]:
        if not self._validate_config():
            self._record_result(False, 0)
            return None
        if not self.circuit_breaker.allow_request():
            logger.error("[AIService] Circuit open, request blocked")
            self._record_result(False, 0)
            return None
        if not isinstance(messages, list) or not messages:
            logger.error("[AIService] Invalid messages payload")
            self._record_result(False, 0)
            return None
        start_time = time.perf_counter()
        req_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        try:
            content = self.provider.generate_content(messages, temperature, max_tokens)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            if content and isinstance(content, str) and content.strip():
                size = len(content.encode("utf-8"))
                logger.info(
                    f"[AIService] Response ok: ts={req_ts} bytes={size} latency_ms={latency_ms}"
                )
                self.circuit_breaker.record_success()
                self._record_result(True, size)
                return content
            logger.error(f"[AIService] Empty response: ts={req_ts} latency_ms={latency_ms}")
            self.circuit_breaker.record_failure()
            self._record_result(False, 0)
            return None
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(f"[AIService] Request failed: ts={req_ts} latency_ms={latency_ms} error={e}")
            self.circuit_breaker.record_failure()
            self._record_result(False, 0)
            return None

    def _validate_config(self) -> bool:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            logger.error("[AIService] Invalid API key")
            return False
        if not isinstance(self.model, str) or not self.model.strip():
            logger.error("[AIService] Invalid model")
            return False
        if not isinstance(self.api_base, str) or not self.api_base.strip():
            logger.error("[AIService] Invalid API base")
            return False
        parsed = urlparse(self.api_base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            logger.error("[AIService] Invalid API base URL format")
            return False
        return True

    def _record_result(self, success: bool, response_bytes: int) -> None:
        with self._metrics_lock:
            self.total_requests += 1
            if success:
                self.success_requests += 1
                self.consecutive_failures = 0
            else:
                self.failure_requests += 1
                self.consecutive_failures += 1
            success_rate = self.success_requests / max(self.total_requests, 1)
            now = time.monotonic()
            if self.consecutive_failures >= 5 and now - self.last_alert_ts > 60:
                logger.error(
                    f"[AIService][ALERT] Consecutive failures={self.consecutive_failures}"
                )
                self.last_alert_ts = now
            if success_rate < 0.95 and self.total_requests >= 20 and now - self.last_alert_ts > 60:
                logger.error(
                    f"[AIService][ALERT] Success rate={success_rate:.2%} total={self.total_requests}"
                )
                self.last_alert_ts = now

    def get_health_stats(self) -> Dict[str, float]:
        with self._metrics_lock:
            success_rate = self.success_requests / max(self.total_requests, 1)
            data = {
                "total_requests": self.total_requests,
                "success_requests": self.success_requests,
                "failure_requests": self.failure_requests,
                "success_rate": success_rate,
                "consecutive_failures": self.consecutive_failures
            }
        data.update(self.circuit_breaker.snapshot())
        return data
    
    def analyze_emotion(self, recent_messages: List[Dict]) -> Dict[str, float]:
        """
        Analyze emotion from recent messages
        
        Returns:
            Dict with emotion types as keys and confidence scores as values
        """
        if len(recent_messages) == 0:
            return {"neutral": 1.0}
        
        # Prepare conversation context
        context = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in recent_messages])
        
        prompt = f"""分析以下对话的整体情绪氛围。注意：分析的是整个对话环境，而不是某个人的情绪。

对话内容：
{context}

请识别对话的整体情绪趋势，并给出概率分布。可能的情绪类型包括：
- neutral: 平和/轻松
- happy: 愉快/兴奋
- tense: 紧张/焦躁
- negative: 消极/冲突

返回JSON格式，包含每个情绪类型的置信度（0-1之间，总和为1）：
{{"neutral": 0.5, "happy": 0.3, "tense": 0.1, "negative": 0.1}}

只返回JSON，不要其他说明。"""

        messages = [
            {"role": "system", "content": "你是一个情绪分析助手，专注于分析对话的整体氛围。"},
            {"role": "user", "content": prompt}
        ]
        
        content = self._make_request(messages, temperature=0.3, max_tokens=200)
        
        if content:
            emotion_data = self._extract_json(content)
            if emotion_data and isinstance(emotion_data, dict):
                default_emotions = {"neutral": 0.0, "happy": 0.0, "tense": 0.0, "negative": 0.0}
                default_emotions.update({k: float(v) for k, v in emotion_data.items() if k in default_emotions})
                total = sum(default_emotions.values())
                if total > 0:
                    default_emotions = {k: v / total for k, v in default_emotions.items()}
                else:
                    default_emotions = {"neutral": 1.0}
                return default_emotions
        
        return {"neutral": 1.0}
    
    def extract_memories(self, recent_messages: List[Dict]) -> List[Dict]:
        """
        Extract key information (memories) from conversation
        
        Returns:
            List of memory dicts with 'content' and 'category' fields
        """
        if len(recent_messages) < 2:
            return []
        
        context = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in recent_messages])
        
        prompt = f"""从以下对话中提取关键信息。关注：
1. 共同提到的重要事件（出游、考试、截止日期等）
2. 已达成的明确约定
3. 需要记住的长期话题

对话内容：
{context}

返回JSON数组格式，每个元素包含：
- content: 记忆内容（摘要性描述）
- category: 类别（event/agreement/topic等）

如果没有关键信息，返回空数组 []。

只返回JSON数组，不要其他说明。"""

        messages = [
            {"role": "system", "content": "你是一个信息提取助手，专注于从对话中提取关键信息。"},
            {"role": "user", "content": prompt}
        ]
        
        content = self._make_request(messages, temperature=0.3, max_tokens=500)
        
        if content:
            memories = self._extract_json_array(content)
            return memories if isinstance(memories, list) else []
        
        return []
    
    def generate_suggestion(self, recent_messages: List[Dict]) -> Optional[Dict]:
        """
        Generate decision/planning suggestion if triggered
        
        Returns:
            Dict with 'title', 'content', and 'type' fields, or None if no suggestion
        """
        # Check if there are planning-related keywords
        context = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in recent_messages[-5:]])
        
        keywords = ['明天', '下周', '周末', '计划', '安排', '出去玩', '聚餐', '学习']
        if not any(keyword in context for keyword in keywords):
            return None
        
        prompt = f"""分析以下对话，如果涉及计划、安排或决策，请生成一个实用的建议。

对话内容：
{context}

如果对话中提到了时间（明天、下周、周末等）和行动（出去玩、安排、计划等），请生成一个建议，包括：
- title: 建议标题
- content: 具体建议内容（可以是行程建议、时间安排、可执行清单等）
- type: 类型（plan/schedule/checklist等）

如果不需要建议，返回null。

只返回JSON对象或null，不要其他说明。"""

        messages = [
            {"role": "system", "content": "你是一个决策辅助助手，帮助用户整理计划和安排。"},
            {"role": "user", "content": prompt}
        ]
        
        content = self._make_request(messages, temperature=0.5, max_tokens=300)
        
        if content:
            if content.lower() in ['null', 'none', '']:
                return None
            suggestion = self._extract_json(content)
            return suggestion if isinstance(suggestion, dict) else None
        
        return None
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON object from text"""
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        json_str = text[start_idx:i+1]
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _extract_json_array(self, text: str) -> List:
        """Extract JSON array from text"""
        bracket_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '[':
                if start_idx == -1:
                    start_idx = i
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0 and start_idx != -1:
                    try:
                        json_str = text[start_idx:i+1]
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1
        
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
