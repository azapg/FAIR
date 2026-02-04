import pytest
import importlib
from unittest.mock import patch, MagicMock


class TestAIService:

    def test_get_ai_client_returns_configured_client(self):
        mock_async_openai = MagicMock()
        mock_client_instance = MagicMock()
        mock_async_openai.return_value = mock_client_instance

        with patch.dict("os.environ", {
            "FAIR_LLM_API_KEY": "test-api-key",
            "FAIR_LLM_BASE_URL": "https://test.api.com/v1",
            "FAIR_LLM_MODEL": "test-model",
        }, clear=False):
            with patch("openai.AsyncOpenAI", mock_async_openai):
                import fair_platform.backend.services.ai_service as ai_service
                importlib.reload(ai_service)

                client = ai_service.get_ai_client()

                mock_async_openai.assert_called_once_with(
                    api_key="test-api-key",
                    base_url="https://test.api.com/v1",
                )
                assert client is mock_client_instance

    def test_get_ai_client_returns_same_instance(self):
        mock_async_openai = MagicMock()
        mock_client_instance = MagicMock()
        mock_async_openai.return_value = mock_client_instance

        with patch("openai.AsyncOpenAI", mock_async_openai):
            import fair_platform.backend.services.ai_service as ai_service
            importlib.reload(ai_service)

            client1 = ai_service.get_ai_client()
            client2 = ai_service.get_ai_client()

            assert client1 is client2
            assert mock_async_openai.call_count == 1

    def test_get_llm_model_returns_configured_model(self):
        with patch.dict("os.environ", {"FAIR_LLM_MODEL": "gpt-4-turbo"}, clear=False):
            import fair_platform.backend.services.ai_service as ai_service
            importlib.reload(ai_service)

            model = ai_service.get_llm_model()

            assert model == "gpt-4-turbo"

    def test_default_base_url_when_not_set(self):
        env_without_base_url = {k: v for k, v in __import__("os").environ.items() if k != "FAIR_LLM_BASE_URL"}
        with patch.dict("os.environ", env_without_base_url, clear=True):
            import fair_platform.backend.services.ai_service as ai_service
            importlib.reload(ai_service)

            assert ai_service.FAIR_LLM_BASE_URL == "https://api.openai.com/v1"
