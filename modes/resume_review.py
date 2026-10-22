from datetime import datetime, timezone
import hashlib
import json

from modes.base import BotMode
from telegram.ext import ContextTypes
from util import load_resource_text, to_plain_text


class ResumeReviewMode(BotMode):
    prompt_filename = "resume_review.txt"
    image_filename = "CV_improvement.jpeg"

    async def generate_tailored_resume(
        self, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        """Generate a tailored resume using source facts and accepted corrections."""
        adjustments = context.user_data.get("mode_adjustments", [])
        cache_inputs = {
            "cv_text": context.user_data["cv_text"],
            "vacancy_text": context.user_data["vacancy_text"],
            "last_result": context.user_data.get("last_result", ""),
            "adjustments": adjustments,
        }
        cache_key = hashlib.sha256(
            json.dumps(cache_inputs, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        if (
            context.user_data.get("tailored_resume_cache_key") == cache_key
            and context.user_data.get("tailored_resume_cache")
        ):
            return context.user_data["tailored_resume_cache"]

        adjustment_text = "\n".join(
            f"{index}. {adjustment}"
            for index, adjustment in enumerate(adjustments, start=1)
        ) or "No additional user corrections."
        payload = (
            f"CURRENT DATE (UTC): {datetime.now(timezone.utc).date().isoformat()}\n\n"
            f"CANDIDATE CV:\n{context.user_data['cv_text']}\n\n"
            f"TARGET VACANCY:\n{context.user_data['vacancy_text']}\n\n"
            f"LATEST AUDIT AND USER-REVISED RESULT:\n"
            f"{context.user_data.get('last_result', '')}\n\n"
            f"USER CORRECTIONS AND ADJUSTMENTS:\n{adjustment_text}"
        )
        prompt = load_resource_text("prompts", "tailored_resume.txt")
        answer = await self.llm.send_question(prompt, payload)
        resume_text = to_plain_text(answer)
        if not resume_text or resume_text == "⚠️ Model returned empty response.":
            raise RuntimeError("The model returned no tailored resume content.")
        context.user_data["tailored_resume_cache"] = resume_text
        context.user_data["tailored_resume_cache_key"] = cache_key
        return resume_text