import sys
import os
import time
import logging
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.providers.retry import retry_with_backoff, RetryError, CircuitBreaker


class TestRetryDecorator(unittest.TestCase):
    
    def test_successful_first_attempt(self):
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)
    
    def test_retry_on_failure_then_success(self):
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = fail_then_succeed()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_max_retries_exceeded(self):
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")
        
        with self.assertRaises(RetryError) as context:
            always_fail()
        
        self.assertEqual(call_count, 3)
        self.assertIsInstance(context.exception.last_exception, ConnectionError)
    
    def test_exponential_backoff_timing(self):
        call_times = []
        
        @retry_with_backoff(max_attempts=3, base_delay=0.1, exponential_base=2.0)
        def track_timing():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Retry me")
            return "done"
        
        track_timing()
        
        self.assertEqual(len(call_times), 3)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        self.assertGreater(delay1, 0.05)
        self.assertLess(delay1, 0.3)
        self.assertGreater(delay2, delay1 * 1.5)
    
    def test_specific_exceptions_only(self):
        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def raise_different_error():
            raise TypeError("Not retryable")
        
        with self.assertRaises(TypeError):
            raise_different_error()


class TestCircuitBreaker(unittest.TestCase):
    
    def test_circuit_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        self.assertTrue(cb.allow_request())
        cb.record_failure()
        cb.record_failure()
        self.assertFalse(cb.allow_request())
    
    def test_circuit_half_open_then_close(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        self.assertTrue(cb.allow_request())
        cb.record_success()
        self.assertEqual(cb.state, "closed")


class TestOpenAIProvider(unittest.TestCase):
    
    @patch('core.providers.openai_provider.requests.post')
    def test_successful_request(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello, world!"}}]
        }
        mock_response.content = b'{"ok":true}'
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        from core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        
        result = provider.generate_content([{"role": "user", "content": "Hi"}])
        
        self.assertEqual(result, "Hello, world!")
        mock_post.assert_called_once()
    
    @patch('core.providers.openai_provider.requests.post')
    def test_retry_on_connection_error(self, mock_post):
        import requests
        
        mock_post.side_effect = [
            requests.ConnectionError("Connection failed"),
            requests.ConnectionError("Connection failed"),
            Mock(
                status_code=200,
                json=Mock(return_value={"choices": [{"message": {"content": "Success after retry"}}]}),
                content=b'{"ok":true}',
                raise_for_status=Mock()
            )
        ]
        
        from core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        
        result = provider.generate_content([{"role": "user", "content": "Hi"}])
        
        self.assertEqual(result, "Success after retry")
        self.assertEqual(mock_post.call_count, 3)

    @patch('core.providers.openai_provider.requests.post')
    def test_timeout_returns_none(self, mock_post):
        import requests
        mock_post.side_effect = requests.Timeout("timeout")
        
        from core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        
        result = provider.generate_content([{"role": "user", "content": "Hi"}])
        
        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 3)
    
    @patch('core.providers.openai_provider.requests.post')
    def test_empty_response_returns_none(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "   "}}]
        }
        mock_response.content = b'{"choices":[{"message":{"content":"   "}}]}'
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        from core.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        
        result = provider.generate_content([{"role": "user", "content": "Hi"}])
        
        self.assertIsNone(result)


class TestProviderFactory(unittest.TestCase):
    
    def test_auto_detect_gemini_by_model_prefix(self):
        from core.providers.factory import _detect_provider
        
        self.assertEqual(_detect_provider("gemini-1.5-pro", None), "gemini")
        self.assertEqual(_detect_provider("gemini-2.0-flash", None), "gemini")
        self.assertEqual(_detect_provider("models/gemini-pro", None), "gemini")
    
    def test_auto_detect_openai_for_other_models(self):
        from core.providers.factory import _detect_provider
        
        self.assertEqual(_detect_provider("gpt-4o-mini", None), "openai")
        self.assertEqual(_detect_provider("qwen/qwen3-vl-8b", None), "openai")
        self.assertEqual(_detect_provider("llama-3.1-8b", None), "openai")
    
    def test_auto_detect_gemini_by_url(self):
        from core.providers.factory import _detect_provider
        
        self.assertEqual(
            _detect_provider("some-model", "https://generativelanguage.googleapis.com/v1"),
            "gemini"
        )
    
    def test_create_openai_provider(self):
        from core.providers import create_provider, OpenAIProvider
        
        provider = create_provider(
            api_key="test-key",
            model="gpt-4o-mini",
            base_url="http://localhost:1235/v1",
            provider_type="openai"
        )
        
        self.assertIsInstance(provider, OpenAIProvider)
    
    def test_create_gemini_provider(self):
        from core.providers import create_provider, GeminiProvider
        
        provider = create_provider(
            api_key="test-key",
            model="gemini-1.5-pro",
            provider_type="gemini"
        )
        
        self.assertIsInstance(provider, GeminiProvider)
    
    def test_create_provider_auto_detection(self):
        from core.providers import create_provider, GeminiProvider, OpenAIProvider
        
        gemini = create_provider(api_key="k", model="gemini-2.0-flash", provider_type="auto")
        self.assertIsInstance(gemini, GeminiProvider)
        
        openai = create_provider(api_key="k", model="gpt-4o", base_url="http://api.openai.com/v1", provider_type="auto")
        self.assertIsInstance(openai, OpenAIProvider)


class TestGeminiProvider(unittest.TestCase):
    
    @patch('core.providers.gemini_provider.genai')
    def test_generate_content_success(self, mock_genai):
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "  Hello from Gemini!  "
        
        mock_genai.GenerativeModel.return_value = mock_model
        mock_model.start_chat.return_value = mock_chat
        mock_chat.send_message.return_value = mock_response
        
        from core.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider(api_key="test-key", model="gemini-1.5-pro")
        
        result = provider.generate_content([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"}
        ])
        
        self.assertEqual(result, "Hello from Gemini!")
        mock_genai.GenerativeModel.assert_called_once()


class TestAIServiceCircuitBreaker(unittest.TestCase):
    
    @patch('core.ai_service.create_provider')
    def test_ai_service_circuit_breaker_blocks(self, mock_create):
        mock_provider = Mock()
        mock_provider.generate_content.side_effect = Exception("fail")
        mock_create.return_value = mock_provider
        
        from core.ai_service import AIService
        service = AIService(
            api_key="k",
            api_base="http://localhost:1235/v1",
            model="gpt-4o-mini",
            circuit_failure_threshold=2,
            circuit_recovery_timeout=0.1
        )
        
        self.assertIsNone(service._make_request([{"role": "user", "content": "Hi"}]))
        self.assertIsNone(service._make_request([{"role": "user", "content": "Hi"}]))
        self.assertEqual(service.circuit_breaker.state, "open")
        self.assertIsNone(service._make_request([{"role": "user", "content": "Hi"}]))


if __name__ == "__main__":
    logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=logging_format)
    unittest.main(verbosity=2)
