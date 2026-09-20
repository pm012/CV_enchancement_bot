import os
from google import genai
from google.genai import types

class GeminiChatService:
    """
    Сервіс для взаємодії з Gemini API у stateless-режимі.
    Кожен запит є ізольованим і не зберігає контекст попередніх повідомлень.
    """
    def __init__(self, token: str | None = None, model_name: str = "gemini-3.6-flash"):
        api_key = token or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        
        # Ініціалізація нового клієнта SDK Google GenAI
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def send_question(self, prompt_text: str, message_text: str) -> str:
        """
        Відправляє ізольований запит до моделей Gemini.
        
        :param prompt_text: Системні інструкції (System Instruction / Role)
        :param message_text: Основне навантаження (CV + Job Description)
        :return: Згенерована відповідь від ШІ у вигляді рядка
        """
        try:
            # Налаштування конфігурації генерації
            config = types.GenerateContentConfig(
                system_instruction=prompt_text,
                temperature=0.3,  # Низька температура для більш точного та фактологічного аналізу CV
            )

            # Виклик генерування без автоматичного Function Calling
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=message_text,
                config=config
            )

            if response.text:
                return response.text
            return "⚠️ Модель повернула порожню відповідь."

        except Exception as e:
            print(f"Error in GeminiChatService: {e}")
            raise e