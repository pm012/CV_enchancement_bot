from telegram import Update
from telegram.ext import ContextTypes
from llm_genai import GeminiChatService

class BotMode:
    """Abstract Base Class for all bot feature strategies."""
    def __init__(self, llm_service: GeminiChatService):
        self.llm = llm_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Triggered when a user selects this mode via menu or command."""
        raise NotImplementedError

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Triggered when a user sends regular text while this mode is active."""
        raise NotImplementedError

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Optional: Handle inline button presses specific to this mode."""
        pass
