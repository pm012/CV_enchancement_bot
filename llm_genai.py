import os
from google import genai
from google.genai import types

class GeminiChatService:
    client: genai.Client = None
    chat_session = None
    system_instruction: str = None
    model_name: str = "gemini-3.6-flash"  # Default light & fast model for free tier

    def __init__(self, token: str):
        # 1. Handle Proxy setup for Google GenAI SDK
        # Google's underlying HTTP client uses standard environment variables for routing
        proxy_url = os.getenv("PROXY_URL")        
        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url

        # 2. Clean up token prefix if needed
        clean_token = token.replace("gemini:", "") if token.startswith('gemini:') else token

        # 3. Initialize the official Google Gen AI Client
        self.client = genai.Client(api_key=clean_token)
        self.system_instruction = "You are a helpful assistant."
        self._reset_chat_session()

    def _reset_chat_session(self):
        """Helper to spin up a new async stateful chat session with current configuration"""
        # Pass the system prompt through standard GenerateContentConfig
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=0.9,
            max_output_tokens=3000
        )
        # Create a stateful async chat session
        self.chat_session = self.client.aio.chats.create(
            model=self.model_name,
            config=config
        )

    def set_prompt(self, prompt_text: str) -> None:
        """Sets a new system instructions context and wipes previous chat history"""
        self.system_instruction = prompt_text
        self._reset_chat_session()

    async def add_message(self, message_text: str) -> str:
        """Sends a message to the active chat session (retains previous conversation context)"""
        # Google's client updates session history automatically
        response = await self.chat_session.send_message(message_text)
        return response.text

    async def send_question(self, prompt_text: str, message_text: str) -> str:
        """Wipes history, applies a new system instruction, and sends a single question"""
        self.system_instruction = prompt_text
        self._reset_chat_session()
        response = await self.chat_session.send_message(message_text)
        return response.text
