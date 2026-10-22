import asyncio
import logging
import os
import re
import time

from google import genai
from google.genai.errors import APIError
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiQuotaExceeded(Exception):
    """Raised when the Google GenAI project has exhausted a daily quota."""

    def __init__(self, retry_after_seconds: float | None = None):
        self.retry_after_seconds = retry_after_seconds
        message = "The Gemini daily request quota is exhausted."
        if retry_after_seconds is not None:
            message += f" Retry after approximately {int(retry_after_seconds)} seconds."
        super().__init__(message)


def _daily_quota_retry_seconds(error: APIError) -> float | None:
    """Return the provider's retry delay for a daily quota exhaustion, if present."""
    details = getattr(error, "details", {})
    error_body = details.get("error", details) if isinstance(details, dict) else {}
    quota_details = error_body.get("details", []) if isinstance(error_body, dict) else []
    daily_quota = False

    for detail in quota_details:
        if not isinstance(detail, dict):
            continue
        detail_type = detail.get("@type", "")
        if detail_type.endswith("QuotaFailure"):
            for violation in detail.get("violations", []):
                quota_id = violation.get("quotaId", "").lower()
                quota_metric = violation.get("quotaMetric", "").lower()
                if "perday" in quota_id or "per_day" in quota_metric:
                    daily_quota = True
        if detail_type.endswith("RetryInfo"):
            retry_delay = detail.get("retryDelay", "")
            match = re.fullmatch(r"(\d+(?:\.\d+)?)s", retry_delay)
            if match:
                retry_seconds = float(match.group(1))
                if daily_quota:
                    return retry_seconds

    message = getattr(error, "message", "") or ""
    if "free_tier_requests" in message.lower() and "daily" in message.lower():
        daily_quota = True
    if daily_quota:
        for detail in quota_details:
            if isinstance(detail, dict) and detail.get("@type", "").endswith("RetryInfo"):
                match = re.fullmatch(r"(\d+(?:\.\d+)?)s", detail.get("retryDelay", ""))
                if match:
                    return float(match.group(1))
        return 24 * 60 * 60
    return None


class GeminiChatService:
    """
    Service form interraction with Gemini API in stateless mode.
    Every query is isolated and don't save context from the past messages.
    """
    MAX_ATTEMPTS = 3
    RETRY_BASE_DELAY_SECONDS = 1
    _quota_blocked_until: float | None = None

    def __init__(self, token: str | None = None, model_name: str = "gemini-3.6-flash"):
        api_key = token or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        
        # Init new client SDK Google GenAI
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def send_question(self, prompt_text: str, message_text: str) -> str:
        """
        Sends isolated request to Gemini models.
        
        :param prompt_text: System instructions (System Instruction / Role)
        :param message_text: Main loadя (CV + Job Description)
        :return: Generated response from AI as a string
        """
        config = types.GenerateContentConfig(
            system_instruction=prompt_text,
            temperature=0.3,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )

        if self._quota_blocked_until is not None:
            remaining = self._quota_blocked_until - time.monotonic()
            if remaining > 0:
                raise GeminiQuotaExceeded(remaining)
            self._quota_blocked_until = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=message_text,
                    config=config,
                )
                if response.text:
                    return response.text
                return "⚠️ Model returned empty response."
            except APIError as error:
                quota_delay = _daily_quota_retry_seconds(error)
                if quota_delay is not None:
                    if quota_delay > 0:
                        self._quota_blocked_until = time.monotonic() + quota_delay
                    logger.warning(
                        "Gemini daily request quota is exhausted; skipping retries"
                    )
                    raise GeminiQuotaExceeded(quota_delay) from error

                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt == self.MAX_ATTEMPTS:
                    logger.exception(
                        "Gemini API request failed after %d attempt(s)",
                        attempt,
                    )
                    raise

                delay = self.RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Gemini API returned HTTP %s; retrying in %s second(s) "
                    "(attempt %d/%d)",
                    error.code,
                    delay,
                    attempt,
                    self.MAX_ATTEMPTS,
                )
                await asyncio.sleep(delay)
            except Exception:
                logger.exception("Unexpected error while calling Gemini API")
                raise

        raise RuntimeError("Gemini API retry loop ended unexpectedly.")