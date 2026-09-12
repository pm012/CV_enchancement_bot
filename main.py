import os
import asyncio
from dotenv import load_dotenv
from llm_genai import GeminiChatService

# Load variables from .env file into environment variables
load_dotenv()

# Safely extract them
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")
PROXY = os.getenv("PROXY_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT")

async def llm_test():
    print("Starting LLM test...")
    # Initialize the GeminiChatService with the GEMINI_TOKEN
    chat_service = GeminiChatService(token=GEMINI_TOKEN)

    system_prompt = ("You are AI security expert. Answer the following question in detail."
    "Keep your answer short, concise and to the point. Avoid unnecessary elaboration.")

    test_question = "What types of vulnerabilities are commonly found in ai applications, and how can they be mitigated? E.g. prompt injection, data poisoning, model inversion, adversarial attacks, etc.  "

    print("Sending test question to GeminiChatService...")
    try:
        response = await chat_service.send_question(prompt_text=system_prompt, message_text=test_question)
        print("Response from GeminiChatService:")
        print(response)
    except Exception as e:
        print(f"An error occurred while testing GeminiChatService: {e}")

if __name__ == "__main__":    
    asyncio.run(llm_test())
