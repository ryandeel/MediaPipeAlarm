import os
import sys
import time
import wave
import datetime
import winsound  # built into Windows
from enum import Enum

import cv2 as cv
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, drawing_styles

# constants
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(FILE_DIR)
MODEL_PATH = os.path.join(BASE_DIR, "models", "pose_landmarker_heavy.task")
SOUND_PATH = os.path.join(BASE_DIR, "alarm.wav")

NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW, RIGHT_ELBOW = 13, 14
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_ANKLE, RIGHT_ANKLE = 27, 28

class Action(Enum):
    JUMPING_JACKS = 1
    CLAP = 2
    
class Pose(Enum):
    DOUBLE_BI = 1
    SALUTE = 2 # army salute, one arm behind back, one to head

def main():
    options = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5)

    pose_landmarker = vision.PoseLandmarker.create_from_options(options)
    
    cap = cv.VideoCapture(0)
    
    if not cap.isOpened:
        raise RuntimeError("can't open webcam")
    
    frame_timestamp_ms = 0
    
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            frame = cv.flip(frame, 1)
            rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            # 30 fps
            frame_timestamp_ms += 33
            result = pose_landmarker.detect_for_video(mp_image, frame_timestamp_ms)
            
            display = cv.cvtColor(draw_landmarks_on_image(rgb, result), cv.COLOR_RGB2BGR)
            
            cv.imshow("alarm", display)
            if cv.waitKey(1) & 0xFF == 27:
                break
            
    finally:
        if cap is not None:
            cap.release()
        cv.destroyAllWindows()

def draw_landmarks_on_image(rgb_image, result):
    annotated = np.copy(rgb_image)
    style = drawing_styles.get_default_pose_landmarks_style()
    conn_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)
    for pose_landmarks in result.pose_landmarks:
        drawing_utils.draw_landmarks(
            image=annotated,
            landmark_list=pose_landmarks,
            connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=style,
            connection_drawing_spec=conn_style)
    return annotated

def jumping_jacks(result, phase):
    if not result.pose_landmarks:
        return phase, False

    lm = result.pose_landmarks[0]

    shoulder_w = abs(lm[LEFT_SHOULDER].x - lm[RIGHT_SHOULDER].x)
    if shoulder_w < 0.01:
        return phase, False

    shoulder_y = (lm[LEFT_SHOULDER].y + lm[RIGHT_SHOULDER].y) / 2

    # Arms up = wrists above the nose AND elbows above the shoulders
    # (so you actually have to extend your arms overhead)
    arms_up = (lm[LEFT_WRIST].y < lm[NOSE].y and lm[RIGHT_WRIST].y < lm[NOSE].y and
               lm[LEFT_ELBOW].y < shoulder_y and lm[RIGHT_ELBOW].y < shoulder_y)
    arms_down = lm[LEFT_WRIST].y > shoulder_y and lm[RIGHT_WRIST].y > shoulder_y


    if phase == "down" and arms_up:
        return "up", False
    if phase == "up" and arms_down:
        return "down", True
    return phase, False

# functions for alarm sound
def make_alarm_wav(path):
    """Generate a simple beep-beep alarm sound so no audio file is needed."""
    rate = 44100
    t = np.linspace(0, 0.25, int(rate * 0.25), endpoint=False)
    beep = 0.5 * np.sin(2 * np.pi * 880 * t)
    silence = np.zeros(int(rate * 0.15))
    pattern = np.concatenate([beep, silence, beep, silence, silence, silence])
    data = (pattern * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(data.tobytes())


def start_sound():
    if not os.path.exists(SOUND_PATH):
        make_alarm_wav(SOUND_PATH)
    # ASYNC = don't block the program, LOOP = repeat until stopped
    winsound.PlaySound(SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)


def stop_sound():
    winsound.PlaySound(None, winsound.SND_PURGE)

if __name__ == "__main__":
    main()
    