import math

def calculate_angle(p1, p2):
    delta_y = -(p2.y - p1.y)
    delta_x = p2.x - p1.x
    angle_rad = math.atan2(delta_y, delta_x)
    angle_deg = math.degrees(angle_rad)
    
    if angle_deg > 90:
        angle_deg = -(180 - angle_deg)
    elif angle_deg < -90:
        angle_deg = 180 + angle_deg
    return angle_deg