import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from google.genai.errors import ClientError, ServerError
from google.genai import _extra_utils

from llm_genai import GeminiChatService, GeminiQuotaExceeded


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.last_kwargs = None

    async def generate_content(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class GeminiRetryTests(unittest.TestCase):
    def create_service(self, outcomes):
        service = GeminiChatService.__new__(GeminiChatService)
        service.client = type(
            "Client",
            (),
            {"aio": type("Aio", (), {"models": FakeModels(outcomes)})()},
        )()
        service.model_name = "test-model"
        return service

    def test_retries_transient_503_then_returns_success(self):
        service = self.create_service(
            [
                ServerError(503, {"error": {"message": "busy"}}),
                ServerError(503, {"error": {"message": "busy"}}),
                type("Response", (), {"text": "Updated result"})(),
            ]
        )

        with patch("llm_genai.asyncio.sleep", new=AsyncMock()) as sleep:
            result = asyncio.run(service.send_question("prompt", "input"))

        self.assertEqual(result, "Updated result")
        self.assertEqual(service.client.aio.models.calls, 3)
        config = service.client.aio.models.last_kwargs["config"]
        self.assertTrue(config.automatic_function_calling.disable)
        self.assertTrue(_extra_utils.should_disable_afc(config))
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            [1, 2],
        )

    def test_raises_after_bounded_retries(self):
        error = ServerError(503, {"error": {"message": "busy"}})
        service = self.create_service([error, error, error])

        with patch("llm_genai.asyncio.sleep", new=AsyncMock()) as sleep:
            with self.assertRaises(ServerError):
                asyncio.run(service.send_question("prompt", "input"))

        self.assertEqual(service.client.aio.models.calls, 3)
        self.assertEqual(sleep.await_count, 2)

    def test_daily_quota_error_skips_retries_and_blocks_followup_calls(self):
        quota_error = ClientError(
            429,
            {
                "error": {
                    "code": 429,
                    "message": "Quota exceeded for daily free tier request limit.",
                    "status": "RESOURCE_EXHAUSTED",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                            "violations": [
                                {
                                    "quotaId": "GenerateRequestsPerDayPerModel-FreeTier",
                                    "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                                }
                            ],
                        },
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "72943s",
                        },
                    ],
                }
            },
        )
        service = self.create_service([quota_error])
        service._quota_blocked_until = None

        with patch("llm_genai.time.monotonic", return_value=100):
            with self.assertRaises(GeminiQuotaExceeded) as first:
                asyncio.run(service.send_question("prompt", "input"))
            with self.assertRaises(GeminiQuotaExceeded) as second:
                asyncio.run(service.send_question("prompt", "input"))

        self.assertEqual(first.exception.retry_after_seconds, 72943)
        self.assertEqual(second.exception.retry_after_seconds, 72943)
        self.assertEqual(service.client.aio.models.calls, 1)


if __name__ == "__main__":
    unittest.main()
