# neck_side_analysis.py
import mediapipe as mp

mp_pose = mp.solutions.pose

def analyze_forward_neck(landmarks, is_collecting_data, alignment_threshold, visibility_threshold):
    """
    거북목(Forward Head Posture)을 측면에서 분석합니다.
    사용자가 '왼쪽' 어깨를 카메라에 보여주고 '오른쪽'을 바라보는 것을 가정합니다.
    
    Args:
        landmarks: MediaPipe 포즈 랜드마크
        is_collecting_data (bool): 현재 데이터 수집 중인지 여부
        alignment_threshold (float): 거북목으로 판단하는 x좌표 차이 임계값 (예: 0.05)
        visibility_threshold (float): 랜드마크 신뢰도 임계값
    
    Returns:
        tuple: (측정된 기울기 값, 상태 메시지, 상태 색상)
    """
    
    # 1. 왼쪽 귀와 어깨 랜드마크 추출
    left_ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR.value]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    
    forward_lean = None
    status_message = "❌ Show your LEFT side clearly" # 왼쪽 측면을 보여달라는 메시지
    status_color = (0, 255, 255)  # Yellow

    # 2. 랜드마크 가시성 체크
    if (left_ear.visibility > visibility_threshold and 
        left_shoulder.visibility > visibility_threshold):
        
        # 3. 수평 거리(x) 계산
        # (shoulder.x - ear.x)
        # 사용자가 오른쪽을 볼 때, 귀가 어깨보다 "앞으로" 가면(x가 작아지면) 이 값은 양수가 됩니다.
        forward_lean = left_shoulder.x - left_ear.x
        
        # 표시를 위해 백분율로 변환 (화면 너비 대비 %
        lean_percentage = forward_lean * 100 
        
        if forward_lean < 0:  # 귀가 어깨보다 뒤에 있음 (매우 좋은 자세)
            status_message = f"Good Posture: {lean_percentage:.1f}%"
            status_color = (0, 255, 0)  # Green
        else:  # 귀가 어깨보다 앞에 있음
            if forward_lean > alignment_threshold:
                status_message = f"⚠️ Forward Head: {lean_percentage:.1f}%"
                status_color = (0, 0, 255)  # Red
            else:
                status_message = f"Slight Lean: {lean_percentage:.1f}%"
                status_color = (0, 165, 255)  # Orange

        if is_collecting_data:
            status_message += " (Collecting)"
    
    # 4. 결과 반환
    return forward_lean, status_message, status_color