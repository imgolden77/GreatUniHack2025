import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import asyncio
import math
import os
from openai import AsyncOpenAI


mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity =1,
    enable_segmentation = False,
    min_detection_confidence =0.5
)
mp_drawing = mp.solutions.drawing_utils

# client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client =None
AI_MODEL ="gpt-4o-mini"
STABILITY_THRESHOLD =5.0

app = FastAPI()
cap =cv2.VideoCapture(0)

analysis_active = False #
current_ai_task = None
ai_feedback_message = "Click the start button to begin analysis."


VISIBILITY_THRESHOLD = 0.8

def calculate_angle(p1, p2):
    delta_y =p2.y -p1.y
    delta_x =p2.x -p1.x
    angle_rad =math.atan2(delta_y, delta_x)
    angle_deg =math.degrees(angle_rad)
    # angle_deg = (angle_deg + 360) % 360
    # if angle_deg > 180:
    #     angle_norm = 360 - angle_norm
    if angle_deg >90:
        angle_deg = -(180 - angle_deg)
    elif angle_deg < -90:
        angle_deg = 180 + angle_deg
    return angle_deg

def process_frame(frame):
    image =cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable =False
    results = pose.process(image)
    image.flags.writeable = True
    image =cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    hip_angle = None
    
    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
        color = (255, 255, 255)  # 기본 흰색
        if (left_hip.visibility > VISIBILITY_THRESHOLD and 
            right_hip.visibility > VISIBILITY_THRESHOLD):

            hip_angle = calculate_angle(left_hip, right_hip)
            hip_tilt_degree = abs(hip_angle)

            color = (0, 255, 0)
            if hip_tilt_degree > STABILITY_THRESHOLD:
                color = (0, 0, 255) #RED
                status_message = f'TILT: {hip_tilt_degree:.2f} degrees'
            else:
                status_message = f'STABLE: {hip_tilt_degree:.2f} degrees'

            mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
            )
        else: 
            status_message = f"❌ Please show your hips fully (Visibility Low)"

        status_color = color 
        cv2.putText(image, status_message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2, cv2.LINE_AA)
        return image, hip_angle
    
    return image, None


async def get_ai_feedback(angle):
    global ai_feedback_message, client
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if client is None:
        if not OPENAI_API_KEY:
            ai_feedback_message = "AI Coach: ❌ OPENAI_API_KEY is not set."
            print("---[AI ERROR] OPENAI_API_KEY is not set.")
            return
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    # direction = "right" if angle > 0 else "left"

    system_prompt = (
        "You are a helpful AI assistant that provides posture correction advice. "
        "When the user's hip tilt angle exceeds the stability threshold, "
        "advise them to adjust their posture by shifting weight to the opposite side."
    )
    user_prompt = (f"The user's hip tilt angle is {angle:.2f} degrees. Please provide feedback."
    )
    
    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7
        )
        ai_message = response.choices[0].message.content.strip()
        ai_feedback_message = f"AI Coach: {ai_message}"
        print(f"---[AI RESPONSE] {ai_message}")

    except Exception as e:
        ai_feedback_message = f"AI Error: {e.__class__.__name__}"
        print(f"---[AI ERROR] {e}")

async def ai_analysis_task():
    global analysis_active, ai_feedback_message
    ai_feedback_message = "AI Coach: Awaiting posture data..."
    while analysis_active:

        if abs(last_calculated_angle) > STABILITY_THRESHOLD:
            temp_angle = last_calculated_angle
            ai_feedback_message = f"AI Coach: {abs(temp_angle):.2f} degrees tilt detected. Generating advice... "
            await get_ai_feedback(temp_angle)
        else:
            ai_feedback_message = "AI Coach: Posture is stable. Keep it up!"

    ai_feedback_message = "AI Coach: Analysis stopped."

@app.post("/control/start")
async def start_analysis():
    global analysis_active, current_ai_task, ai_feedback_message
    if not analysis_active:
        analysis_active = True
        ai_feedback_message = "AI Coach: Analysis started. Monitoring posture..."
        current_ai_task = asyncio.create_task(ai_analysis_task())
        print("--- [AGENT] ANALYSIS STARTED ---")
    return {"status": "started"}

@app.post("/control/stop")
async def stop_analysis():
    global analysis_active, current_ai_task, ai_feedback_message
    if analysis_active:
        analysis_active = False
        if current_ai_task:
            current_ai_task.cancel()
            current_ai_task = None
        ai_feedback_message = "AI Coach: Analysis stopped."
        print("--- [AGENT] ANALYSIS STOPPED ---")
    return {"status": "stopped"}

last_calculated_angle = 0.0

async def generate_frames():
    global analysis_active, last_calculated_angle

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_to_stream = frame.copy() 
        hip_angle = None
        
        if analysis_active:
            # MediaPipe 분석 및 골격선 그리기 (2단계 로직 사용)
            frame_to_stream, hip_angle = process_frame(frame)
            
            # --- 2단계 디버깅용 로그 (유지) ---
            if hip_angle is not None:
                print(f"Calculated Hip Angle: {hip_angle:.2f} degrees")
        else:
            pass

        ret, buffer =cv2.imencode('.jpg', frame_to_stream)
        frame_bytes =buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(0.01)

@app.get("/", response_class = HTMLResponse)
async def index(request: Request):
    html_content =f"""
       <html>
        <head>
            <title>FastAPI Pose Agent</title>
            <style>
                body {{ font-family: sans-serif; text-align: center; background-color: #f0f4f8; }}
                h1 {{ color: #007bff; }}
                img {{ border: 5px solid #007bff; border-radius: 8px; }}
                button {{ padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; border-radius: 5px; }}
                #startButton {{ background-color: #28a745; color: white; border: none; }}
                #stopButton {{ background-color: #dc3545; color: white; border: none; }}
                #status, #ai-feedback {{ margin-top: 15px; padding: 10px; border-radius: 5px; font-size: 1.1em; font-weight: bold; }}
                #ai-feedback {{ background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }}
            </style>
        </head>
        <body>
            <h1>🚶 AI 자세 분석 코치 에이전트 🧠</h1>
            <p>분석을 시작하고 5도 이상 기울어지면 AI 코치가 교정 메시지를 보냅니다.</p>
            
            <div id="controls">
                <button id="startButton">Start Analysis</button>
                <button id="stopButton" disabled>Stop Analysis</button>
            </div>
            
            <div id="ai-feedback">{ai_feedback_message}</div> 
            
            <img id="videoFeed" width="640" height="480">
            
            <script>
                const videoFeed = document.getElementById('videoFeed');
                const startButton = document.getElementById('startButton');
                const stopButton = document.getElementById('stopButton');
                const aiFeedbackDiv = document.getElementById('ai-feedback');
                
                let analysisActive = false;
                let feedbackInterval; // AI 피드백 업데이트를 위한 타이머

                // AI 피드백을 주기적으로 가져와서 업데이트하는 함수
                const updateAIFeedback = async () => {{
                    try {{
                        const response = await fetch('/ai_feedback');
                        const data = await response.json();
                        aiFeedbackDiv.textContent = data.message;
                    }} catch (e) {{
                        aiFeedbackDiv.textContent = '❌ API 통신 오류';
                    }}
                }};
                
                // 분석 시작 함수
                startButton.onclick = async () => {{
                    if (analysisActive) return;
                    analysisActive = true;
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    
                    // FastAPI 백엔드에 분석 시작을 알리는 요청
                    await fetch('/control/start', {{ method: 'POST' }});
                    
                    // 영상 스트림 시작 및 AI 피드백 업데이트 시작
                    videoFeed.src = '/video_feed'; 
                    feedbackInterval = setInterval(updateAIFeedback, 500); // 0.5초마다 AI 메시지 업데이트
                }};

                // 분석 정지 함수
                stopButton.onclick = async () => {{
                    if (!analysisActive) return;
                    analysisActive = false;
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    
                    // 타이머 및 영상 스트림 정지
                    clearInterval(feedbackInterval);
                    videoFeed.src = '';
                    
                    // FastAPI 백엔드에 분석 정지를 알리는 요청
                    await fetch('/control/stop', {{ method: 'POST' }});
                }};

                // 초기 AI 피드백 메시지 설정
                aiFeedbackDiv.textContent = '{ai_feedback_message}';
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/ai_feedback")
async def get_current_ai_feedback():
    return {"message": ai_feedback_message}

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


    

