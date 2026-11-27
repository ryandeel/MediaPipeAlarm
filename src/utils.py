# small helpers shared by alarm_app, poses and actions

import math

import cv2 as cv


# we can calculate the angle of a line given three points (thanks nizdar laila)
def calcul_angle(x1, y1, x2, y2, x3, y3):
    angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))
    angle = abs(angle)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle

def put_text(img, text, y, scale=1.0, color=(0, 255, 0), x=30):
    cv.putText(img, text, (x, y), cv.FONT_HERSHEY_SIMPLEX, scale, color, 3)

def overlay_corner(display, img, alpha=0.5, margin=10):
    h, w = img.shape[:2]
    dh, dw = display.shape[:2]
    y0, x1 = margin, dw - margin
    x0, y1 = x1 - w, y0 + h
    roi = display[y0:y1, x0:x1]
    display[y0:y1, x0:x1] = cv.addWeighted(img, alpha, roi, 1 - alpha, 0)
