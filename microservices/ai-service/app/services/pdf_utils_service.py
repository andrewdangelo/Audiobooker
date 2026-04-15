import ast
from app.services.ai_text_service import AITextService

# TODO: Obliderate this service after re-homing this method?
class PDFUtilsService:
    @staticmethod
    async def validate_characters(characters_list, book_title):
        # Prompt
        messages = [
            ("system", "You are an expert book analyzer. Your main task is to take the provided Character List and use the provided Web Context to correct the characters' info. You shall only return the CORRECTED list itself and NOT any other words or context or explanation."),
            ("human", "Character List: {chars_list} \nWeb Context: {web_context} \nReturn the corrected characters list in the same exact json format.")
        ]
        
        # Search query generator
        search_query_template = "{book_title} book characters list wikipedia"

        answer, web_context = await AITextService.chat_rag_web_context(
            prompt_messages=messages,
            search_query_template=search_query_template,
            inputs={"book_title": book_title, "chars_list": str(characters_list)},
            deployment_name="qwen2-5-7b-instruct-bnb-4bit-001"
        )

        return ast.literal_eval(answer), web_context