import mediapipe as mp
from src.utils import calculate_angle  

mp_pose = mp.solutions.pose

def analyze_shoulder_tilt(landmarks, is_collecting_data, stability_threshold, visibility_threshold):

    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    
    shoulder_angle = None
    status_message = "No Shoulders Detected"
    status_color = (0, 255, 255)  # Yellow

    if (left_shoulder.visibility > visibility_threshold and 
        right_shoulder.visibility > visibility_threshold):

        shoulder_angle = calculate_angle(left_shoulder, right_shoulder)
        shoulder_tilt_degree = abs(shoulder_angle)

        if is_collecting_data:
            status_message = f'Shoulder Tilt: {shoulder_tilt_degree:.2f}° (Collecting)'
        else:
            status_message = f'Shoulder Tilt: {shoulder_tilt_degree:.2f}° (Ready)'

        if shoulder_tilt_degree > stability_threshold:
            status_color = (0, 0, 255)  # Red
        else:
            status_color = (0, 255, 0)  # Green
    else:
        status_message = "❌ Please show your shoulders fully"

    return shoulder_angle, status_message, status_color