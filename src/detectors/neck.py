
import mediapipe as mp

mp_pose = mp.solutions.pose

def analyze_forward_neck(landmarks, is_collecting_data, alignment_threshold, visibility_threshold):
    
    left_ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR.value]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    
    forward_lean = None
    status_message = "❌ Show your LEFT side clearly" 
    status_color = (0, 255, 255)  # Yellow

    if (left_ear.visibility > visibility_threshold and 
        left_shoulder.visibility > visibility_threshold):
        
        forward_lean = left_shoulder.x - left_ear.x

        lean_percentage = forward_lean * 100 
        
        if forward_lean < 0:  
            status_message = f"Good Posture: {lean_percentage:.1f}%"
            status_color = (0, 255, 0)  # Green
        else:  
            if forward_lean > alignment_threshold:
                status_message = f"⚠️ Forward Head: {lean_percentage:.1f}%"
                status_color = (0, 0, 255)  # Red
            else:
                status_message = f"Slight Lean: {lean_percentage:.1f}%"
                status_color = (0, 165, 255)  # Orange

        if is_collecting_data:
            status_message += " (Collecting)"

    return forward_lean, status_message, status_color