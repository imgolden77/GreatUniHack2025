import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import asyncio
import math

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity =1,
    enable_segmentation = False,
    min_detection_confidence =0.5
)
mp_drawing = mp.solutions.drawing_utils

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

app = FastAPI()
analysis_active = False #
cap =cv2.VideoCapture(0)

VISIBILITY_THRESHOLD = 0.6

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
    global analysis_active

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

        ret, buffer =cv2.imencode('.jpg', frame_to_stream)
        frame_bytes =buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(0.01)


@app.post("/control/start")
async def start_analysis():
    global analysis_active
    analysis_active = True
    print("--- [AGENT] ANALYSIS STARTED ---")
    return {"status": "started"}

@app.post("/control/stop")
async def stop_analysis():
    global analysis_active
    analysis_active = False
    print("--- [AGENT] ANALYSIS STOPPED ---")
    return {"status": "stopped"}

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/", response_class = HTMLResponse)
async def index(request: Request):
    html_content ="""
        <html>
        <head>
            <title>FastAPI Pose Agent</title>
            <style>
                body { font-family: sans-serif; text-align: center; }
                img { border: 5px solid #007bff; border-radius: 8px; }
                button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>🚶 AI 자세 분석 에이전트 🏃</h1>
            <p>분석을 시작하려면 'Start Analysis'를 눌러주세요.</p>
            
            <div id="controls">
                <button id="startButton">Start Analysis</button>
                <button id="stopButton" disabled>Stop Analysis</button>
            </div>
            
            <img id="videoFeed" src="/video_feed" width="640" height="480">
            
            <div id="status">Analysis Not Started.</div>

            <script>
                const videoFeed = document.getElementById('videoFeed');
                const startButton = document.getElementById('startButton');
                const stopButton = document.getElementById('stopButton');
                const statusDiv = document.getElementById('status');
                
                let analysisActive = false;
                
                // 분석 시작 함수
                startButton.onclick = async () => {
                    if (analysisActive) return;
                    analysisActive = true;
                    statusDiv.textContent = 'Analysis Running...';
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    
                    // FastAPI 백엔드에 분석 시작을 알리는 요청을 보냅니다. (NEW)
                    await fetch('/control/start', { method: 'POST' });
                    // videoFeed.src = '/video_feed';
                };

                // 분석 정지 함수
                stopButton.onclick = async () => {
                    if (!analysisActive) return;
                    analysisActive = false;
                    statusDiv.textContent = 'Analysis Stopped.';
                    startButton.disabled = false;
                    stopButton.disabled = true;

                    // FastAPI 백엔드에 분석 정지를 알리는 요청을 보냅니다. (NEW)
                    await fetch('/control/stop', { method: 'POST' });
                    // videoFeed.src = '';
                };

                // 초기에는 영상 스트림 URL을 비워두어 분석 전에는 움직이지 않도록 합니다.
            </script>
        </body>
    </html>
    """

    return HTMLResponse(content=html_content, status_code=200)

