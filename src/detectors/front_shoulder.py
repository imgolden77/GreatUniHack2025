import mediapipe as mp
from src.utils import calculate_angle  # 공통 유틸리티 임포트

mp_pose = mp.solutions.pose

def analyze_shoulder_tilt(landmarks, is_collecting_data, stability_threshold, visibility_threshold):
    """어깨 랜드마크를 분석하여 기울기 각도와 상태 메시지를 반환합니다."""
    
    # 1. 랜드마크 추출
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    
    shoulder_angle = None
    status_message = "No Shoulders Detected"
    status_color = (0, 255, 255)  # Yellow

    # 2. 랜드마크 가시성 체크
    if (left_shoulder.visibility > visibility_threshold and 
        right_shoulder.visibility > visibility_threshold):

        # 3. 각도 계산
        shoulder_angle = calculate_angle(left_shoulder, right_shoulder)
        shoulder_tilt_degree = abs(shoulder_angle)

        # 4. 현재 상태 메시지 및 색상 결정
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