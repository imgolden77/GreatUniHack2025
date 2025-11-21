# hip.py
import mediapipe as mp
from src.utils import calculate_angle

mp_pose = mp.solutions.pose

def analyze_hip_tilt(landmarks, is_collecting_data, stability_threshold, visibility_threshold):
    
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    
    hip_angle = None
    status_message = "No Hips Detected"
    status_color = (0, 255, 255)  # Yellow

    if (left_hip.visibility > visibility_threshold and 
        right_hip.visibility > visibility_threshold):

        hip_angle = calculate_angle(left_hip, right_hip)
        hip_tilt_degree = abs(hip_angle)

        if is_collecting_data:
            status_message = f'Hip Tilt: {hip_tilt_degree:.2f}° (Collecting)'
        else:
            status_message = f'Hip Tilt: {hip_tilt_degree:.2f}° (Ready)'

        if hip_tilt_degree > stability_threshold:
            status_color = (0, 0, 255)  # Red
        else:
            status_color = (0, 255, 0)  # Green
    else:
        status_message = "❌ Please show your hips fully"

    return hip_angle, status_message, status_color