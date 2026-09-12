from modes.base import BotMode
from util import send_text, extract_text_from_file

class CoverLetterMode(BotMode):
    async def start(self, update, context):
        context.user_data["cv_text"] = None
        context.user_data["cv_step"] = "WAITING_CV"
        await send_text(
            update, context, 
            "📄 Let's create your tailored **Cover Letter**.\n\n"
            "Please **upload your CV** (.pdf or .docx) or paste your resume details as text here:"
        )

    async def handle_message(self, update, context):
        step = context.user_data.get("cv_step")

        if step == "WAITING_CV":
            # Handle Document Upload or Plain Text
            if update.message.document:
                doc_file = await update.message.document.get_file()
                file_bytes = await doc_file.download_as_bytearray()
                cv_text = extract_text_from_file(bytes(file_bytes), update.message.document.file_name)
            else:
                cv_text = update.message.text

            if not cv_text:
                await send_text(update, context, "I couldn't read any text. Please paste text or re-upload your file.")
                return

            context.user_data["cv_text"] = cv_text
            context.user_data["cv_step"] = "WAITING_VACANCY"
            await send_text(update, context, "CV received! Now, please **paste the vacancy description** you are applying for:")
            
        elif step == "WAITING_VACANCY":
            vacancy_text = update.message.text
            cv_text = context.user_data.get("cv_text")
            
            my_message = await send_text(update, context, "🤖 Crafting a cover letter matching your profile to the target job...")
            
            prompt_instruction = (
                "You are an elite executive career coach. Write a compelling, punchy cover letter "
                "matching the user's CV to the provided vacancy description. Highlight relevant skills "
                "without repeating things word-for-word. Keep it under 350 words, formatted professionally."
            )
            
            payload = f"--- CANDIDATE CV ---\n{cv_text}\n\n--- TARGET VACANCY ---\n{vacancy_text}"
            
            try:
                answer = await self.llm.send_question(prompt_instruction, payload)
                await my_message.edit_text(answer, parse_mode="Markdown")
            except Exception as e:
                await my_message.edit_text(f"Error communicating with Gemini API: {e}")
                
            # Clear user mode status out of state memory
            context.user_data["current_mode"] = None
