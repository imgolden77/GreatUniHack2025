
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from openai import APIError, APIConnectionError, RateLimitError, BadRequestError

load_dotenv()

try:
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    if not os.environ.get("OPENAI_API_KEY"):
        print("--- [AI_COACH_ERROR] OPENAI_API_KEY has not been set. ---")
except Exception as e:
    print(f"--- [AI_COACH_ERROR] Failed to initialize OpenAI client: {e} ---")
    client = None

async def get_ai_feedback(report1: str, report2: str, mode: str) -> str:
    
    if client is None:
        print("--- [AI_COACH] OpenAI client is not available, skipping API call. ---")
        return f"(AI Disabled) Diagnosis: {report1} | {report2}"
        
    system_prompt = (
        "You are an expert AI posture coach. "
        "Your user has just completed a 10-second posture analysis. "
        "You will receive one or two summary lines about their posture. "
        "Based on this, provide a concise (2-3 sentences), encouraging, and actionable piece of advice. "
        "Start with an emoji. Respond in English."
    )

    user_prompt = (
        f"My analysis mode was '{mode}'. The results are:\n"
        f"1. {report1}\n"
        f"2. {report2}\n\n"
        "What is your coaching advice for me?"
    )

    try:
        print("--- [AGENT] Requesting AI Feedback from OpenAI... ---")
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="gpt-4o-mini", 
            temperature=0.7,
            max_tokens=200, 
        )
        
        ai_message = chat_completion.choices[0].message.content
        print(f"--- [AGENT] AI Feedback Received: {ai_message} ---")
        return ai_message
        

    except BadRequestError as e:
        print(f"--- [API ERROR: BAD REQUEST] Code: {e.code}, Message: {e.message}")
        return "⚠️ AI Error: BadRequestError"
    except RateLimitError:
        return "⚠️ AI Error: RateLimitError"
    except APIConnectionError:
        return "⚠️ AI Error: APIConnectionError"
    except APIError as e:
        print(f"--- [API ERROR] Status: {e.status_code}, Message: {e.message}")
        return "⚠️ AI Error: APIError"
    except Exception as e: 
        print(f"--- [INTERNAL ERROR] {e}")
        return f"INTERNAL ERROR: {e.__class__.__name__}"