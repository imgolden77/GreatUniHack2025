
import mediapipe as mp

mp_pose = mp.solutions.pose

def analyze_round_shoulder(landmarks, is_collecting_data, alignment_threshold, visibility_threshold):
    
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]

    forward_slouch = None
    status_message = "❌ Show your LEFT side clearly" 
    status_color = (0, 255, 255)  # Yellow

    if (left_shoulder.visibility > visibility_threshold and 
        left_hip.visibility > visibility_threshold):

        forward_slouch = left_hip.x - left_shoulder.x

        slouch_percentage = forward_slouch * 100

        if forward_slouch < 0: 
            status_message = f"Good Posture: {slouch_percentage:.1f}%"
            status_color = (0, 255, 0)  # Green
        else:  
            if forward_slouch > alignment_threshold:
                status_message = f"⚠️ Round Shoulder: {slouch_percentage:.1f}%"
                status_color = (0, 0, 255)  # Red
            else:
                status_message = f"Slight Slouch: {slouch_percentage:.1f}%"
                status_color = (0, 165, 255)  # Orange
        
        if is_collecting_data:
            status_message += " (Collecting)"

    return forward_slouch, status_message, status_color