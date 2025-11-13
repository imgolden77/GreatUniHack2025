import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import asyncio
import math

from src.detectors import hip, front_shoulder, neck, side_shoulder
from src import ai_coach

templates = Jinja2Templates(directory="templates")

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
cap = cv2.VideoCapture(0)

analysis_active = False
current_task = None
is_collecting_data = False 
feedback_message = "Waiting for analysis to start..."
ai_feedback_message = ""
countdown_message = ""  

VIEW_MODE = "frontal" 
VISIBILITY_THRESHOLD = 0.6
ANGLE_COLLECTION_DURATION = 10  
ADVICE_RATIO_THRESHOLD = 0.33


FRONTAL_STABILITY_THRESHOLD = 5.0   
SIDE_NECK_THRESHOLD = 0.03          
SIDE_SHOULDER_THRESHOLD = 0.03      
angle_history = {
    "part1": [],
    "part2": []
}

def process_frame(frame):
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = pose.process(image)
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    part1_value, msg1, color1 = (None, "Waiting", (255, 255, 0))
    part2_value, msg2, color2 = (None, "", (255, 255, 0))
    
    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark

        if VIEW_MODE == "frontal":
            part1_value, msg1, color1 = hip.analyze_hip_tilt(
                landmarks, is_collecting_data, FRONTAL_STABILITY_THRESHOLD, VISIBILITY_THRESHOLD
            )
            part2_value, msg2, color2 = front_shoulder.analyze_shoulder_tilt(
                landmarks, is_collecting_data, FRONTAL_STABILITY_THRESHOLD, VISIBILITY_THRESHOLD
            )
        elif VIEW_MODE == "side":
            part1_value, msg1, color1 = neck.analyze_forward_neck(
                landmarks, is_collecting_data, SIDE_NECK_THRESHOLD, VISIBILITY_THRESHOLD
            )
            part2_value, msg2, color2 = side_shoulder.analyze_round_shoulder(
                landmarks, is_collecting_data, SIDE_SHOULDER_THRESHOLD, VISIBILITY_THRESHOLD
            )


        mp_drawing.draw_landmarks(
            image,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
        )
    else: 
        msg1 = "❌ No pose detected"
        msg2 = ""

    cv2.putText(image, msg1, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color1, 2, cv2.LINE_AA)
    cv2.putText(image, msg2, (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color2, 2, cv2.LINE_AA)
    
    return image, part1_value, part2_value

def _analyze_angle_list(angle_list, part_name, threshold, ratio_threshold):
    if not angle_list:
        return f"{part_name}: No valid data."

    threshold_frames = [angle for angle in angle_list if abs(angle) > threshold]
    
    tilt_ratio = len(threshold_frames) / len(angle_list) if len(angle_list) > 0 else 0
        
    print(f"--- [{part_name} ANALYSIS] Total: {len(angle_list)}, Tilted: {len(threshold_frames)}, Ratio: {tilt_ratio:.2f} ---")

    if tilt_ratio > ratio_threshold:
        percentage = int(tilt_ratio * 100)
        worst_angle = max(angle_list, key=abs)

        direction = "right" if worst_angle > 0 else "left" 
        if VIEW_MODE == "side":
            direction = "forward" 
            
        return (
            f"⚠️ {part_name}: Imbalance ({percentage}%)! "
            f"Mainly tilted {direction}."
        )
    else:
        return f"✅ {part_name}: Stable. Great job!"
    
async def trigger_ai_feedback(report1, report2, mode):
    global ai_feedback_message
    ai_feedback_message = "🧠 AI coach is analyzing..." 
    try:
        ai_message = await ai_coach.get_ai_feedback(report1, report2, mode)
        ai_feedback_message = ai_message
    except Exception as e:
        print(f"--- [AGENT] AI Task Error: {e} ---")
        ai_feedback_message = "🤖 AI feedback request failed."


async def batch_analysis_task():
    global analysis_active, angle_history, feedback_message, is_collecting_data, countdown_message

    try:
        for i in range(3, 0, -1):
            countdown_message = str(i)
            feedback_message = f"Get Ready: {i}"
            print(f"--- [AGENT] COUNTDOWN {i} ---")
            await asyncio.sleep(1)
            if not analysis_active:
                countdown_message = ""
                feedback_message = "Analysis stopped during countdown."
                return
        countdown_message = ""
        feedback_message = "Collecting data..."
    except asyncio.CancelledError:
        countdown_message = ""
        return

    loop = asyncio.get_event_loop()
    start_time = loop.time()
    end_time = start_time + ANGLE_COLLECTION_DURATION

    angle_history["part1"].clear()
    angle_history["part2"].clear()
    
    is_collecting_data = True
    print(f"--- [AGENT] DATA COLLECTION STARTED ({VIEW_MODE} mode) ---")

    while loop.time() < end_time and analysis_active:
        elapsed_time = int(loop.time() - start_time)
        feedback_message = f"Collecting data... ({elapsed_time} seconds elapsed)"
        await asyncio.sleep(1) 

    is_collecting_data = False
    
    if not analysis_active or (not angle_history["part1"] and not angle_history["part2"]):
        feedback_message = "Analysis stopped or insufficient valid data."
        analysis_active = False
        return

    feedback_message = "Data collection complete. Analyzing posture..."

    if VIEW_MODE == "frontal":
        report1 = _analyze_angle_list(
            angle_history["part1"], "Hip", FRONTAL_STABILITY_THRESHOLD, ADVICE_RATIO_THRESHOLD
        )
        report2 = _analyze_angle_list(
            angle_history["part2"], "Shoulder", FRONTAL_STABILITY_THRESHOLD, ADVICE_RATIO_THRESHOLD
        )
    elif VIEW_MODE == "side":
        report1 = _analyze_angle_list(
            angle_history["part1"], "Neck", SIDE_NECK_THRESHOLD, ADVICE_RATIO_THRESHOLD
        )
        report2 = _analyze_angle_list(
            angle_history["part2"], "Back", SIDE_SHOULDER_THRESHOLD, ADVICE_RATIO_THRESHOLD
        )
    else:
        report1 = "Error"
        report2 = "Invalid Mode"
        
    feedback_message = f"Final Diagnosis: {report1} | {report2}"
    asyncio.create_task(trigger_ai_feedback(report1, report2, VIEW_MODE))

    analysis_active = False 
    print("--- [AGENT] BATCH ANALYSIS FINISHED ---")


async def generate_frames():
    global analysis_active, angle_history, countdown_message, VIEW_MODE

    while True:
        success, frame = cap.read()
        if not success:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Camera Error", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        frame_to_stream = frame.copy() 
        
        if analysis_active:
            frame_to_stream, part1_value, part2_value = process_frame(frame)
            
            if is_collecting_data:
                if part1_value is not None:
                    angle_history["part1"].append(part1_value)
                if part2_value is not None:
                    angle_history["part2"].append(part2_value)
                    
            if countdown_message:
                (h, w) = frame_to_stream.shape[:2]
                font_scale = 6
                thickness = 10
                text = countdown_message
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
                text_x = (w - text_size[0]) // 2
                text_y = (h + text_size[1]) // 2
                cv2.putText(frame_to_stream, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 
                            font_scale, (0, 0, 0), thickness + 5, cv2.LINE_AA)
                cv2.putText(frame_to_stream, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 
                            font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        else:
            mode_text = f"Mode: {VIEW_MODE.capitalize()}. Press Start."
            cv2.putText(frame_to_stream, mode_text, (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            if VIEW_MODE == "side":
                 cv2.putText(frame_to_stream, "Show your LEFT side", (50, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame_to_stream)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(0.03)

@app.post("/control/start")
async def start_analysis():
    global analysis_active, current_task, feedback_message, VIEW_MODE, ai_feedback_message
    if not analysis_active:
        ai_feedback_message = ""
        analysis_active = True
        
        if current_task:
            current_task.cancel()
        current_task = asyncio.create_task(batch_analysis_task())
        feedback_message = f"{VIEW_MODE.capitalize()} analysis started!"
        if VIEW_MODE == "side":
            feedback_message += " (Showing LEFT side)"
    print(f"--- [AGENT] ANALYSIS STARTED (Mode: {VIEW_MODE}) ---")
    return {"status": "started", "mode": VIEW_MODE}

@app.post("/control/stop")
async def stop_analysis():
    global analysis_active, current_task, feedback_message, is_collecting_data, countdown_message
    if analysis_active:
        ai_feedback_message = ""
        analysis_active = False
        is_collecting_data = False 
        countdown_message = ""  
        
        if current_task:
            current_task.cancel()
            current_task = None

        feedback_message = "Analysis stopped."
        print("--- [AGENT] ANALYSIS STOPPED ---")
    return {"status": "stopped"}

@app.post("/control/set_view/{view_name}")
async def set_view(view_name: str):
    global VIEW_MODE, feedback_message, analysis_active
    if analysis_active:
        return {"status": "error", "message": "Cannot change mode during analysis."}
        
    if view_name == "frontal":
        VIEW_MODE = "frontal"
        feedback_message = "Mode: Frontal. Ready."
        return {"status": "frontal mode set"}
    elif view_name == "side":
        VIEW_MODE = "side"
        feedback_message = "Mode: Side. Stand showing your LEFT side. Ready."
        return {"status": "side mode set"}
    else:
        return {"status": "error", "message": "Invalid mode. Use 'frontal' or 'side'."}

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/feedback")
async def get_current_feedback():
    return {
        "message": feedback_message,        # (e.g. "Final Diagnosis: ...")
        "ai_message": ai_feedback_message,  # (e.g. "AI coach is analyzing...")
        "active": analysis_active,
        "collecting": is_collecting_data,
        "mode": VIEW_MODE 
    }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index_ai.html", {"request": request})