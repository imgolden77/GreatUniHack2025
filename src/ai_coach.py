# ai_coach.py
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from openai import APIError, APIConnectionError, RateLimitError, BadRequestError

# ⚠️ 환경 변수 설정 확인
load_dotenv()

try:
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    if not os.environ.get("OPENAI_API_KEY"):
        print("--- [AI_COACH_ERROR] OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. ---")
except Exception as e:
    print(f"--- [AI_COACH_ERROR] OpenAI 클라이언트 초기화 실패: {e} ---")
    client = None

async def get_ai_feedback(report1: str, report2: str, mode: str) -> str:
    """
    분석 리포트 문자열을 기반으로 OpenAI에 코칭 조언을 요청합니다.
    
    Args:
        report1 (str): 첫 번째 부위 분석 결과 (예: "✅ Hip: Stable...")
        report2 (str): 두 번째 부위 분석 결과 (예: "⚠️ Shoulder: Imbalance...")
        mode (str): 현재 분석 모드 ("frontal" 또는 "side")

    Returns:
        str: AI가 생성한 코칭 메시지 또는 오류 시 폴백 메시지
    """
    
    if client is None:
        print("--- [AI_COACH] OpenAI 클라이언트가 없어 API 호출을 건너뜁니다. ---")
        return f"(AI Disabled) Diagnosis: {report1} | {report2}"
        
    # [2] AI에게 역할을 부여하는 시스템 프롬프트
    system_prompt = (
        "You are an expert AI posture coach. "
        "Your user has just completed a 10-second posture analysis. "
        "You will receive one or two summary lines about their posture. "
        "Based on this, provide a concise (2-3 sentences), encouraging, and actionable piece of advice. "
        "Start with an emoji. Respond in English."
    )
    
    # [3] AI에게 전달할 사용자 메시지
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
            model="gpt-4o-mini", # 비용 효율적인 모델 사용
            temperature=0.7,
            max_tokens=200, # 한국어 응답을 위해 넉넉하게
        )
        
        ai_message = chat_completion.choices[0].message.content
        print(f"--- [AGENT] AI Feedback Received: {ai_message} ---")
        return ai_message
        
    # except Exception as e:
    #     return f"⚠️ AI Error: {e.__class__.__name__}"
    except BadRequestError as e:
        # 400 에러 처리: 잘못된 요청 데이터 (프롬프트/모델명 등) 확인
        print(f"--- [API ERROR: BAD REQUEST] Code: {e.code}, Message: {e.message}")
        return "⚠️ AI Error: 요청 형식이 잘못되었습니다. (프롬프트 확인 필요)"
    except RateLimitError:
        # 요청 한도 초과 에러 처리
        return "⚠️ AI Error: API 사용 한도를 초과했습니다. 잠시 후 시도해 주세요."
    except APIConnectionError:
        # 네트워크 연결 에러 처리
        return "⚠️ AI Error: OpenAI 서버 연결 실패. 네트워크 상태를 확인하세요."
    except APIError as e:
        # 그 외 모든 API 에러 처리 (인증 실패, 서버 오류 등)
        print(f"--- [API ERROR] Status: {e.status_code}, Message: {e.message}")
        return "⚠️ AI Error: OpenAI API 통신 중 알 수 없는 오류 발생"
    except Exception as e:
        # 예상치 못한 기타 에러 처리
        print(f"--- [INTERNAL ERROR] {e}")
        return f"⚠️ 내부 오류: {e.__class__.__name__}"