# shoulder_side_analysis.py
import mediapipe as mp

mp_pose = mp.solutions.pose

def analyze_round_shoulder(landmarks, is_collecting_data, alignment_threshold, visibility_threshold):
    """
    라운드 숄더(Round Shoulder)를 측면에서 분석합니다.
    사용자가 '왼쪽' 어깨를 카메라에 보여주고 '오른쪽'을 바라보는 것을 가정합니다.

    Args:
        landmarks: MediaPipe 포즈 랜드마크
        is_collecting_data (bool): 현재 데이터 수집 중인지 여부
        alignment_threshold (float): 라운드 숄더로 판단하는 x좌표 차이 임계값 (예: 0.07)
        visibility_threshold (float): 랜드마크 신뢰도 임계값
    
    Returns:
        tuple: (측정된 기울기 값, 상태 메시지, 상태 색상)
    """
    
    # 1. 왼쪽 어깨와 힙 랜드마크 추출
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]

    forward_slouch = None
    status_message = "❌ Show your LEFT side clearly" # 왼쪽 측면을 보여달라는 메시지
    status_color = (0, 255, 255)  # Yellow

    # 2. 랜드마크 가시성 체크
    if (left_shoulder.visibility > visibility_threshold and 
        left_hip.visibility > visibility_threshold):

        # 3. 수평 거리(x) 계산
        # (hip.x - shoulder.x)
        # 사용자가 오른쪽을 볼 때, 어깨가 힙보다 "앞으로" 가면(x가 작아지면) 이 값은 양수가 됩니다.
        forward_slouch = left_hip.x - left_shoulder.x

        slouch_percentage = forward_slouch * 100

        if forward_slouch < 0:  # 어깨가 힙보다 뒤에 있음 (가슴을 편 자세)
            status_message = f"Good Posture: {slouch_percentage:.1f}%"
            status_color = (0, 255, 0)  # Green
        else:  # 어깨가 힙보다 앞에 있음
            if forward_slouch > alignment_threshold:
                status_message = f"⚠️ Round Shoulder: {slouch_percentage:.1f}%"
                status_color = (0, 0, 255)  # Red
            else:
                status_message = f"Slight Slouch: {slouch_percentage:.1f}%"
                status_color = (0, 165, 255)  # Orange
        
        if is_collecting_data:
            status_message += " (Collecting)"
            
    # 4. 결과 반환
    return forward_slouch, status_message, status_color