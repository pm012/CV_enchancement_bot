from telegram import Update
from telegram.ext import ContextTypes
from llm_genai import GeminiChatService
from util import load_resource_text

class BotMode:
    """Базовий клас для всіх стратегій обробки кар'єрних документів."""
    prompt_filename: str = None
    image_filename: str = None

    def __init__(self, llm_service: GeminiChatService):
        self.llm = llm_service

    def get_system_prompt(self) -> str:
        if self.prompt_filename:
            return load_resource_text("prompts", self.prompt_filename)
        return "You are an expert executive career coach."

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Отримує збережені CV та Vacancy з context.user_data і робить запит до Gemini."""
        cv_text = context.user_data.get("cv_text", "")
        vacancy_text = context.user_data.get("vacancy_text", "")

        system_instruction = self.get_system_prompt()
        payload = f"--- CANDIDATE CV ---\n{cv_text}\n\n--- TARGET VACANCY ---\n{vacancy_text}"

        answer = await self.llm.send_question(system_instruction, payload)
        return answer