from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes
from llm_genai import GeminiChatService
from util import load_resource_text, to_plain_text


class BotMode:
    """Base class for all strategies of handling career documents."""
    prompt_filename: str = None
    image_filename: str = None

    def __init__(self, llm_service: GeminiChatService):
        self.llm = llm_service

    def get_system_prompt(self) -> str:
        if self.prompt_filename:
            prompt = load_resource_text("prompts", self.prompt_filename)
        else:
            prompt = "You are an expert executive career coach."
        return (
            f"{prompt}\n\n"
            "Output requirements: use plain text only. Do not use Markdown, "
            "asterisks, hash headings, backticks, or Markdown bullet syntax. "
            "Use short plain-text section headings and concise, clearly separated lines. "
            "Do not invent facts that are not in the supplied CV or vacancy. "
            "The current date is supplied with the input; use it for date comparisons. "
            "Do not describe a date as future unless it is after that current date."
        )

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Generate a mode result using the saved CV and vacancy."""
        cv_text = context.user_data.get("cv_text", "")
        vacancy_text = context.user_data.get("vacancy_text", "")

        system_instruction = self.get_system_prompt()
        payload = (
            f"CURRENT DATE (UTC): {datetime.now(timezone.utc).date().isoformat()}\n\n"
            f"CANDIDATE CV:\n{cv_text}\n\nTARGET VACANCY:\n{vacancy_text}"
        )

        answer = await self.llm.send_question(system_instruction, payload)
        return to_plain_text(answer)

    async def refine(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        corrections: list[str],
    ) -> str:
        """Revise the last result using the user's corrections and saved source data."""
        cv_text = context.user_data.get("cv_text", "")
        vacancy_text = context.user_data.get("vacancy_text", "")
        previous_result = context.user_data.get("last_result", "")
        correction_text = "\n".join(
            f"{index}. {correction}" for index, correction in enumerate(corrections, start=1)
        )
        system_instruction = (
            f"{self.get_system_prompt()}\n\n"
            "The user is correcting or refining your previous result. Re-check every "
            "relevant claim against the supplied CV, vacancy, current date, and corrections. "
            "Treat explicit statements about the candidate's experience or background as "
            "candidate-confirmed facts, even when the original CV omitted them. Incorporate "
            "those facts into the revised result; do not continue calling them missing or "
            "undocumented. Treat explicit corrections to dates or other CV details as updated "
            "source information. Follow stylistic instructions where possible. If a correction "
            "is ambiguous or conflicts with an earlier correction, ask a concise clarification "
            "instead of silently ignoring it. Return the complete revised result, not commentary "
            "about edits."
        )
        payload = (
            f"CURRENT DATE (UTC): {datetime.now(timezone.utc).date().isoformat()}\n\n"
            f"CANDIDATE CV:\n{cv_text}\n\n"
            f"TARGET VACANCY:\n{vacancy_text}\n\n"
            f"PREVIOUS RESULT:\n{previous_result}\n\n"
            f"USER-CONFIRMED FACTS AND ADJUSTMENTS (treat these as updates to the source "
            f"information, not as unverified suggestions):\n{correction_text}"
        )
        answer = await self.llm.send_question(system_instruction, payload)
        return to_plain_text(answer)