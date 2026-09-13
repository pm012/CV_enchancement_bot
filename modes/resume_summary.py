from modes.base import BotMode
from util import send_photo, send_text, extract_text_from_file

class ResumeSummaryMode(BotMode):
    async def start(self, update, context):
        context.user_data["cv_text"] = None
        context.user_data["cv_step"] = "WAITING_CV"
        await send_photo(update, context, "AI_CV_Summary.png")
        await send_text(
            update, context, 
            "Let's generate a professional **Resume Summary**.\n\n"
            "Please **upload your CV** or paste your experience details as text here:"
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
                await send_text(update, context, "No text found. Please upload or paste text again.")
                return

            context.user_data["cv_text"] = cv_text
            context.user_data["cv_step"] = "WAITING_VACANCY"
            await send_text(update, context, "Experience received! Now, please **paste the target vacancy description**:")
            
        elif step == "WAITING_VACANCY":
            vacancy_text = update.message.text
            cv_text = context.user_data.get("cv_text")
            
            my_message = await send_text(update, context, "Synthesizing a tailored resume summary...")
            
            prompt_instruction = (
                "You are an expert technical recruiter. Based on the user's CV and the target vacancy, "
                "generate a compelling 3-4 sentence professional Summary section. Below that summary, "
                "provide a bulleted list of 6 Core Competencies tailored directly to matching the job's main requirements."
            )
            payload = f"--- CANDIDATE CV ---\n{cv_text}\n\n--- TARGET VACANCY ---\n{vacancy_text}"
            
            try:
                answer = await self.llm.send_question(prompt_instruction, payload)
                await my_message.edit_text(answer, parse_mode="Markdown")
            except Exception as e:
                await my_message.edit_text(f"Error communicating with Gemini API: {e}")
                
            context.user_data["current_mode"] = None
