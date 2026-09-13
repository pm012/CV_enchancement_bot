from modes.base import BotMode
from util import send_photo, send_text, extract_text_from_file

class ResumeReviewMode(BotMode):
    async def start(self, update, context):
        context.user_data["cv_text"] = None
        context.user_data["cv_step"] = "WAITING_CV"
        await send_photo(update, context, "CV_improvement.jpeg")
        await send_text(
            update, context, 
            "🔍 Let's perform a thorough **Resume Review** against a job specification.\n\n"
            "Please **upload your resume** or paste its text structure here:"
        )

    async def handle_message(self, update, context):
        step = context.user_data.get("cv_step")

        if step == "WAITING_CV":
            if update.message.document:
                doc_file = await update.message.document.get_file()
                file_bytes = await doc_file.download_as_bytearray()
                cv_text = extract_text_from_file(bytes(file_bytes), update.message.document.file_name)
            else:
                cv_text = update.message.text

            if not cv_text:
                await send_text(update, context, "No text found. Please provide your resume details.")
                return

            context.user_data["cv_text"] = cv_text
            context.user_data["cv_step"] = "WAITING_VACANCY"
            await send_text(update, context, "Resume saved. Now, please **paste the targeted vacancy text** to audit against:")
            
        elif step == "WAITING_VACANCY":
            vacancy_text = update.message.text
            cv_text = context.user_data.get("cv_text")
            
            my_message = await send_text(update, context, "Analyzing your resume structure and calculating keyword coverage...")
            
            prompt_instruction = (
                "You are a critical ATS system auditor and resume reviewer. Analyze the provided CV against the Vacancy.\n"
                "Provide feedback structured exactly into three markdown categories:\n"
                "1. **ATS Keyword Gap**: List critical keywords found in the vacancy that are missing from the CV.\n"
                "2. **Structural & Formatting Critique**: Actionable advice on how to reorganize experience bullet points to emphasize impact.\n"
                "3. **Overall Match Rating**: Provide a constructive score from 0-100% with a one-sentence justification."
            )
            payload = f"--- CURRENT CV ---\n{cv_text}\n\n--- VACANCY SPECIFICATION ---\n{vacancy_text}"
            
            try:
                answer = await self.llm.send_question(prompt_instruction, payload)
                await my_message.edit_text(answer, parse_mode="Markdown")
            except Exception as e:
                await my_message.edit_text(f"Error communicating with Gemini API: {e}")
                
            context.user_data["current_mode"] = None
