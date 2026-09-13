from modes.base import BotMode
from util import send_photo, send_text, extract_text_from_file

class LinkedInMode(BotMode):
    async def start(self, update, context):
        context.user_data["cv_text"] = None
        context.user_data["cv_step"] = "WAITING_CV"
        await send_photo(update, context, "LinkedInSummary.png")
        await send_text(update, context, "Let's craft your optimized **LinkedIn 'About' Summary**.\n\nPlease upload or paste your CV text:")

    async def handle_message(self, update, context):
        step = context.user_data.get("cv_step")

        if step == "WAITING_CV":
            if update.message.document:
                doc_file = await update.message.document.get_file()
                file_bytes = await doc_file.download_as_bytearray()
                cv_text = extract_text_from_file(bytes(file_bytes), update.message.document.file_name)
            else:
                cv_text = update.message.text

            context.user_data["cv_text"] = cv_text
            context.user_data["cv_step"] = "WAITING_VACANCY"
            await send_text(update, context, "CV loaded. Now, paste the vacancy text to optimize keywords against:")

        elif step == "WAITING_VACANCY":
            vacancy_text = update.message.text
            cv_text = context.user_data.get("cv_text")
            
            my_message = await send_text(update, context, "Structuring your profile summary...")
            
            prompt_instruction = (
                "You are an expert LinkedIn profile optimizer. Write an engaging, high-conversion "
                "'About' section for a LinkedIn profile based on the candidate's CV and target vacancy. "
                "Write it in first person, include an optimized skill keyword list, and keep it punchy."
            )
            payload = f"--- CV ---\n{cv_text}\n\n--- VACANCY ---\n{vacancy_text}"
            
            try:
                answer = await self.llm.send_question(prompt_instruction, payload)
                await my_message.edit_text(answer, parse_mode="Markdown")
            except Exception as e:
                await my_message.edit_text(f"Error: {e}")
                
            context.user_data["current_mode"] = None
