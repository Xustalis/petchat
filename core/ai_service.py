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
        self.total_attempts = 0
        self.retry_attempts = 0
        self.total_prompt_chars = 0
        self.total_response_bytes = 0
        self.latency_history = []
        self.latency_history_limit = int(os.getenv("AI_LATENCY_HISTORY_LIMIT", "200"))
        self.max_context_messages = int(os.getenv("AI_MAX_CONTEXT_MESSAGES", "20"))
        self.max_context_chars = int(os.getenv("AI_MAX_CONTEXT_CHARS", "4000"))
        self.empty_response_retries = int(os.getenv("AI_EMPTY_RESPONSE_RETRIES", "1"))
        self.retry_backoff_base = float(os.getenv("AI_EMPTY_RESPONSE_BACKOFF", "0.5"))
        self.retry_temperature = float(os.getenv("AI_RETRY_TEMPERATURE", "0.2"))
        self.retry_max_tokens_ratio = float(os.getenv("AI_RETRY_MAX_TOKENS_RATIO", "0.7"))
        self.suggestion_fallback = os.getenv("AI_SUGGESTION_FALLBACK", "1") == "1"
        self.prompt_templates = {
            "emotion": {
                "system": "你是一个情绪分析助手，专注于分析对话的整体氛围。",
                "user": (
                    "分析以下对话的整体情绪氛围。注意：分析的是整个对话环境，而不是某个人的情绪。\n\n"
                    "对话内容：\n{context}\n\n"
                    "请识别对话的整体情绪趋势，并给出概率分布。可能的情绪类型包括：\n"
                    "- neutral: 平和/轻松\n"
                    "- happy: 愉快/兴奋\n"
                    "- tense: 紧张/焦躁\n"
                    "- negative: 消极/冲突\n\n"
                    "返回JSON格式，包含每个情绪类型的置信度（0-1之间，总和为1）：\n"
                    "{\"neutral\": 0.5, \"happy\": 0.3, \"tense\": 0.1, \"negative\": 0.1}\n\n"
                    "只返回JSON，不要其他说明，不要代码块。"
                )
            },
            "memory": {
                "system": "你是一个信息提取助手，专注于从对话中提取关键信息。",
                "user": (
                    "从以下对话中提取关键信息。关注：\n"
                    "1. 共同提到的重要事件（出游、考试、截止日期等）\n"
                    "2. 已达成的明确约定\n"
                    "3. 需要记住的长期话题\n\n"
                    "对话内容：\n{context}\n\n"
                    "返回JSON数组格式，每个元素包含：\n"
                    "- content: 记忆内容（摘要性描述）\n"
                    "- category: 类别（event/agreement/topic等）\n\n"
                    "如果没有关键信息，返回空数组 []。\n\n"
                    "只返回JSON数组，不要其他说明，不要代码块。"
                )
            },
            "suggestion": {
                "system": "你是一个决策辅助助手，帮助用户整理计划和安排。",
                "user": (
                    "分析以下对话，如果涉及计划、安排或决策，请生成一个实用的建议。\n\n"
                    "对话内容：\n{context}\n\n"
                    "如果对话中提到了时间（明天、下周、周末等）和行动（出去玩、安排、计划等），请生成一个建议，包括：\n"
                    "- title: 建议标题\n"
                    "- content: 具体建议内容（可以是行程建议、时间安排、可执行清单等）\n"
                    "- type: 类型（plan/schedule/checklist等）\n\n"
                    "如果不需要建议，返回null。\n\n"
                    "只返回JSON对象或null，不要其他说明，不要代码块。"
                )
            }
        }
        logger.info(f"[AIService] Initialized with provider: {type(self.provider).__name__}")
    
    def _make_request(self, messages: List[Dict], temperature: float = 0.3, 
                      max_tokens: int = 500) -> Optional[str]:
        if not self._validate_config():
            self._record_result(False, 0, 0)
            return None
        if not self.circuit_breaker.allow_request():
            logger.error("[AIService] Circuit open, request blocked")
            self._record_result(False, 0, 0)
            return None
        if not isinstance(messages, list) or not messages:
            logger.error("[AIService] Invalid messages payload")
            self._record_result(False, 0, 0)
            return None
        request_start = time.perf_counter()
        req_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        prompt_chars = self._estimate_prompt_chars(messages)
        effective_temperature = temperature
        effective_max_tokens = max_tokens
        last_latency_ms = 0
        for attempt in range(self.empty_response_retries + 1):
            start_time = time.perf_counter()
            try:
                content = self.provider.generate_content(messages, effective_temperature, effective_max_tokens)
                last_latency_ms = int((time.perf_counter() - start_time) * 1000)
                size = len(content.encode("utf-8")) if isinstance(content, str) else 0
                self._record_attempt(prompt_chars, size, last_latency_ms, attempt > 0)
                if content and isinstance(content, str) and content.strip():
                    logger.info(
                        f"[AIService] Response ok: ts={req_ts} bytes={size} latency_ms={last_latency_ms}"
                    )
                    self.circuit_breaker.record_success()
                    total_latency_ms = int((time.perf_counter() - request_start) * 1000)
                    self._record_result(True, size, total_latency_ms)
                    return content
                logger.error(
                    f"[AIService] Empty response: ts={req_ts} latency_ms={last_latency_ms} attempt={attempt + 1}"
                )
            except Exception as e:
                last_latency_ms = int((time.perf_counter() - start_time) * 1000)
                self._record_attempt(prompt_chars, 0, last_latency_ms, attempt > 0)
                logger.exception(
                    f"[AIService] Request failed: ts={req_ts} latency_ms={last_latency_ms} attempt={attempt + 1} error={e}"
                )
            if attempt < self.empty_response_retries:
                effective_temperature = min(effective_temperature, self.retry_temperature)
                effective_max_tokens = max(16, int(effective_max_tokens * self.retry_max_tokens_ratio))
                time.sleep(self.retry_backoff_base * (attempt + 1))
        total_latency_ms = int((time.perf_counter() - request_start) * 1000)
        self.circuit_breaker.record_failure()
        self._record_result(False, 0, total_latency_ms)
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

    def _record_result(self, success: bool, response_bytes: int, latency_ms: int) -> None:
        with self._metrics_lock:
            self.total_requests += 1
            if success:
                self.success_requests += 1
                self.consecutive_failures = 0
            else:
                self.failure_requests += 1
                self.consecutive_failures += 1
            if latency_ms >= 0:
                self.latency_history.append(latency_ms)
                if len(self.latency_history) > self.latency_history_limit:
                    self.latency_history = self.latency_history[-self.latency_history_limit:]
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
            avg_latency = sum(self.latency_history) / max(len(self.latency_history), 1)
            p95_latency = self._percentile(self.latency_history, 95)
            avg_prompt_chars = self.total_prompt_chars / max(self.total_attempts, 1)
            avg_response_bytes = self.total_response_bytes / max(self.total_requests, 1)
            retry_rate = self.retry_attempts / max(self.total_attempts, 1)
            data = {
                "total_requests": self.total_requests,
                "success_requests": self.success_requests,
                "failure_requests": self.failure_requests,
                "success_rate": success_rate,
                "consecutive_failures": self.consecutive_failures,
                "total_attempts": self.total_attempts,
                "retry_attempts": self.retry_attempts,
                "retry_rate": retry_rate,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "avg_prompt_chars": avg_prompt_chars,
                "avg_response_bytes": avg_response_bytes
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
        
        context = self._build_context(recent_messages)
        messages = self._render_prompt("emotion", context)
        
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
        
        context = self._build_context(recent_messages)
        messages = self._render_prompt("memory", context)
        
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
        context = self._build_context(recent_messages[-5:], max_messages=5, max_chars=self.max_context_chars)
        keywords = ['明天', '下周', '周末', '计划', '安排', '出去玩', '聚餐', '学习']
        if not any(keyword in context for keyword in keywords):
            if self.suggestion_fallback:
                return {
                    "title": "暂无建议",
                    "content": "未检测到计划/安排相关内容。需要建议时可说明时间与行动。",
                    "type": "info"
                }
            return None
        
        messages = self._render_prompt("suggestion", context)
        
        content = self._make_request(messages, temperature=0.5, max_tokens=300)
        
        if content:
            if content.lower() in ['null', 'none', '']:
                return None
            suggestion = self._extract_json(content)
            return suggestion if isinstance(suggestion, dict) else None
        
        return None
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON object from text"""
        text = self._strip_code_fences(text)
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
        text = self._strip_code_fences(text)
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

    def _strip_code_fences(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        cleaned = text.strip()
        if "```" in cleaned:
            cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "")
        return cleaned.strip()

    def _sanitize_messages(self, recent_messages: List[Dict]) -> List[Dict]:
        sanitized = []
        for msg in recent_messages:
            if not isinstance(msg, dict):
                continue
            sender = msg.get("sender") or msg.get("sender_name") or msg.get("name") or msg.get("role") or "user"
            content = msg.get("content") or msg.get("text") or msg.get("message") or ""
            sender = str(sender).strip() if sender is not None else "user"
            content = str(content).strip() if content is not None else ""
            if content:
                sanitized.append({"sender": sender, "content": content})
        return sanitized

    def _build_context(self, recent_messages: List[Dict], max_messages: Optional[int] = None, max_chars: Optional[int] = None) -> str:
        max_messages = max_messages or self.max_context_messages
        max_chars = max_chars or self.max_context_chars
        sanitized = self._sanitize_messages(recent_messages)
        if max_messages > 0:
            sanitized = sanitized[-max_messages:]
        lines = [f"{msg['sender']}: {msg['content']}" for msg in sanitized]
        while max_chars > 0 and lines and len("\n".join(lines)) > max_chars:
            lines.pop(0)
        return "\n".join(lines).strip()

    def _render_prompt(self, name: str, context: str) -> List[Dict[str, str]]:
        template = self.prompt_templates.get(name)
        if not template:
            return [{"role": "user", "content": context}]
        system = template.get("system", "").replace("{context}", context)
        user = template.get("user", "").replace("{context}", context)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if user:
            messages.append({"role": "user", "content": user})
        return messages

    def update_prompt_template(self, name: str, system: str, user: str) -> None:
        if not isinstance(name, str) or not name.strip():
            return
        self.prompt_templates[name] = {
            "system": system or "",
            "user": user or ""
        }

    def _estimate_prompt_chars(self, messages: List[Dict]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            total += len(str(content))
        return total

    def _record_attempt(self, prompt_chars: int, response_bytes: int, latency_ms: int, is_retry: bool) -> None:
        with self._metrics_lock:
            self.total_attempts += 1
            if is_retry:
                self.retry_attempts += 1
            self.total_prompt_chars += max(0, prompt_chars)
            if response_bytes > 0:
                self.total_response_bytes += response_bytes

    def _percentile(self, values: List[int], percentile: int) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        k = int(round((percentile / 100) * (len(ordered) - 1)))
        return float(ordered[min(max(k, 0), len(ordered) - 1)])

    def build_performance_report(self, baseline: Optional[Dict[str, float]] = None) -> Dict[str, object]:
        current = self.get_health_stats()
        report = {
            "current": current,
            "comparison": {},
            "recommendations": []
        }
        if baseline:
            def delta(key: str) -> Optional[float]:
                if key in baseline and key in current:
                    return current[key] - baseline[key]
                return None
            report["comparison"] = {
                "success_rate_delta": delta("success_rate"),
                "avg_latency_ms_delta": delta("avg_latency_ms"),
                "p95_latency_ms_delta": delta("p95_latency_ms"),
                "retry_rate_delta": delta("retry_rate")
            }
        if current.get("success_rate", 1.0) < 0.95:
            report["recommendations"].append("提高模型可用性或降级到更稳定的模型")
        if current.get("avg_latency_ms", 0) > 0:
            if baseline and current.get("avg_latency_ms") > baseline.get("avg_latency_ms", 0) * 0.7:
                report["recommendations"].append("缩短上下文或降低max_tokens以改善延迟")
        if current.get("retry_rate", 0) > 0.2:
            report["recommendations"].append("排查网络抖动与服务端限流")
        return report
