import os
from google import genai
from google.genai import types

class GeminiChatService:
    """
    Service form interraction with Gemini API in stateless mode.
    Every query is isolated and don't save context from the past messages.
    """
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
        try:
            # Set up generation configuration
            config = types.GenerateContentConfig(
                system_instruction=prompt_text,
                temperature=0.3,  # Low temperature from the keen and factological analysis of CV
            )

            # Call generation without automatic Function Calling
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=message_text,
                config=config
            )

            if response.text:
                return response.text
            return "⚠️ Model returned empty response."

        except Exception as e:
            print(f"Error in GeminiChatService: {e}")
            raise e