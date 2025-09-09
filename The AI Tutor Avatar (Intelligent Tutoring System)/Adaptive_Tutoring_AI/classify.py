from memory import ChatMemory
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Set the GEMINI_API_KEY environment variable.")
genai.configure(api_key=gemini_api_key)

memory = ChatMemory()
model_name = "gemini-2.0-flash"
client = genai.GenerativeModel(model_name)

def classify_mode(user_input: str, context_chunks=None) -> str:

    full_conversation = memory.get_all_messages()
    convo_text = "\n".join([f"{m['role']}: {m['content']}" for m in full_conversation])

    prompt = f"""
        You are an intent classification system for a tutoring chatbot.
        Read the student's LAST message and the previous conversation for context.
        Based on the context and student's last message Return ONLY one of these exact labels:

        - Tutor mode
        - Motivation mode
        - FAQs mode
        - Casual mode
        - Gibberish mode

        Rules:
        1. Tutor mode → if the message is clearly about learning, solving study cases, math, science, or course content. 
        2. Motivation mode → if the student is stressed, frustrated, or demotivated (e.g. "I can't do this").
        3. FAQs mode → if the message is about university/lecture systems (e.g. "how to log in", "forgot password").
        4. Casual mode → if it’s everyday conversation (jokes, stories, food, hobbies, personal life, celebration, etc.) OR a continuation of a casual topic.
        5. Gibberish mode → ONLY if the message has no meaning at all (random letters/symbols like "asdfgh" or "123#$@").

        ⚠️ CRITICAL:
        - If the message is a SHORT follow-up (e.g. "yes", "no", "ok", "from the start", "continue", "tell me more") → classify it in the SAME mode as the previous turn.
        - If the student’s last message is related to or builds upon the ongoing topic (even if poorly worded, casual, or with grammar mistakes), classify it in the SAME mode as the previous turn.
        - DO NOT classify as Gibberish if the message can be logically connected to the conversation context.
        - Context always overrides surface-level interpretation.

        Previous conversation:
        {convo_text}

        educational material:
        {context_chunks}

        student: "{user_input}"
        Answer with just the mode label, nothing else.
        """

    # Call Gemini
    response = client.generate_content(prompt)

    return response.text.strip()
