import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from ai_coach import get_ai_feedback_from_gpt
import asyncio
import math

templates = Jinja2Templates(directory="templates")

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity =1,
    enable_segmentation = False,
    min_detection_confidence =0.5
)
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(p1, p2):
    delta_y =-(p2.y -p1.y)
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

app = FastAPI()
analysis_active = False #
cap =cv2.VideoCapture(0)

VISIBILITY_THRESHOLD = 0.6
STABILITY_THRESHOLD = 5.0

current_ai_task = None
last_calculated_angle = 0.0
ai_feedback_message = "Waiting AI analysis..."

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
            status_message = f'Hip Angle: {hip_tilt_degree:.2f} degrees'
            color = (0, 255, 0)
            if hip_tilt_degree > 5:
                color = (0, 0, 255)

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
                last_calculated_angle = hip_angle
                print(f"Calculated Hip Angle: {hip_angle:.2f} degrees")

        ret, buffer =cv2.imencode('.jpg', frame_to_stream)
        frame_bytes =buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(0.01)

async def ai_analysis_task():
    global analysis_active, last_calculated_angle, ai_feedback_message
    
    # 루프 시작 시점 설정
    ai_feedback_message = "Waiting AI analysis..." 
    
    while analysis_active:
        current_angle = last_calculated_angle
        
        # 1. 비대칭 지속성 판단
        if abs(current_angle) > STABILITY_THRESHOLD:
             
             # 2. AI에게 요청
             # 사용자에게 요청 중임을 알림
             temp_angle = current_angle
             ai_feedback_message = f"🧠 AI Coach: {abs(temp_angle):.2f}° tilt. Generating feedback..."
             
             # ai_coach.py의 get_ai_feedback_from_gpt 함수 호출
             # (이 함수는 5도 미만일 때는 '안정적' 메시지를 반환하도록 ai_coach.py에 구현되어야 함)
             new_message = await get_ai_feedback_from_gpt(temp_angle)
             ai_feedback_message = new_message
             
        else:
             # 안정적일 때의 메시지
             ai_feedback_message = f"🧠 AI Coach: Stable, Keep going! ({abs(current_angle):.2f}°)"

        # 2초마다 AI 분석 실행 (OpenAI API 호출 빈도 조절)
        await asyncio.sleep(2.0) 
        
    ai_feedback_message = "Analsis has stopped."


@app.post("/control/start")
async def start_analysis():
    global analysis_active, current_ai_task, ai_feedback_message
    if not analysis_active:
        analysis_active = True
        ai_feedback_message = "Starting analysis..."
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
        ai_feedback_message = "Analysis stopped."
        print("--- [AGENT] ANALYSIS STOPPED ---")
    return {"status": "stopped"}

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/", response_class = HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ai_feedback")
async def get_current_ai_feedback():
    return {"message": ai_feedback_message}

