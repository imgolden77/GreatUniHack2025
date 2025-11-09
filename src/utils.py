import math

def calculate_angle(p1, p2):
    """두 MediaPipe 랜드마크 포인트 사이의 수평 각도를 계산합니다."""
    delta_y = -(p2.y - p1.y)  # y축은 위로 갈수록 값이 작아지므로 반전
    delta_x = p2.x - p1.x
    angle_rad = math.atan2(delta_y, delta_x)
    angle_deg = math.degrees(angle_rad)
    
    # 각도를 -90 ~ +90 범위로 정규화
    if angle_deg > 90:
        angle_deg = -(180 - angle_deg)
    elif angle_deg < -90:
        angle_deg = 180 + angle_deg
    return angle_deg