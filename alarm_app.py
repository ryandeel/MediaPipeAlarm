"""
Resisting Alarm Clock
State machine: IDLE -> RINGING -> EXERCISING -> DONE

Run normally:   python AlarmApp.py          (uses ALARM_TIME below)
Quick test:     python AlarmApp.py --test   (alarm goes off in 5 seconds)
"""

import os
import sys
import time
import wave
import datetime
import winsound  # built into Windows

import cv2 as cv
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, drawing_styles

# ---------------- Settings you can change ----------------
ALARM_TIME = "20:24"      # 24-hour HH:MM
TARGET_REPS = 15          # jumping jacks needed to turn the alarm off
ALLOW_ESC_QUIT = True     # set False for the "real" alarm so ESC can't cheat
ARMS_UP_FEET_APART = 1.5  # ankle gap must be this many shoulder-widths to count as "apart"
FEET_TOGETHER = 1.2       # ankle gap must be under this many shoulder-widths to count as "together"
MIN_VISIBILITY = 0.5      # ankles must be at least this visible to trust the reading
# ---------------------------------------------------------

# Landmark indices (MediaPipe 33-point pose model)
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW, RIGHT_ELBOW = 13, 14
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
REQUIRE_FEET = False 

# States
IDLE, RINGING, EXERCISING, DONE = "IDLE", "RINGING", "EXERCISING", "DONE"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "pose_landmarker_heavy.task")
SOUND_PATH = os.path.join(BASE_DIR, "alarm.wav")


# ---------------- Sound ----------------
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


def update_jumping_jacks(result, phase):
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

    if REQUIRE_FEET:
        if lm[LEFT_ANKLE].visibility < MIN_VISIBILITY or lm[RIGHT_ANKLE].visibility < MIN_VISIBILITY:
            return phase, False
        ankle_w = abs(lm[LEFT_ANKLE].x - lm[RIGHT_ANKLE].x)
        feet_apart = ankle_w > ARMS_UP_FEET_APART * shoulder_w
        feet_together = ankle_w < FEET_TOGETHER * shoulder_w
    else:
        feet_apart = True
        feet_together = True

    if phase == "down" and arms_up and feet_apart:
        return "up", False
    if phase == "up" and arms_down and feet_together:
        return "down", True
    return phase, False

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


def put_text(img, text, y, scale=1.0, color=(0, 255, 0)):
    cv.putText(img, text, (30, y), cv.FONT_HERSHEY_SIMPLEX, scale, color, 3)


# ---------------- Alarm time ----------------
def next_alarm_datetime():
    if "--test" in sys.argv:
        return datetime.datetime.now() + datetime.timedelta(seconds=5)
    hour, minute = map(int, ALARM_TIME.split(":"))
    now = datetime.datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)  # already passed today -> tomorrow
    return target


# ---------------- Main ----------------
def main():
    options = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO)
    detector = vision.PoseLandmarker.create_from_options(options)

    alarm_dt = next_alarm_datetime()
    print(f"Alarm set for {alarm_dt.strftime('%Y-%m-%d %H:%M:%S')}. Press Ctrl+C to cancel.")

    state = IDLE
    cam = None
    reps = 0
    phase = "down"
    start = time.monotonic()
    last_ts = -1
    done_at = None

    try:
        while True:
            # ---- IDLE: wait for the alarm time (no camera needed) ----
            if state == IDLE:
                if datetime.datetime.now() >= alarm_dt:
                    state = RINGING
                else:
                    time.sleep(0.5)
                continue

            # ---- RINGING: start sound, open camera ----
            if state == RINGING:
                print("WAKE UP! Do jumping jacks to turn it off.")
                start_sound()
                cam = cv.VideoCapture(0)
                reps, phase = 0, "down"
                state = EXERCISING
                continue

            # ---- EXERCISING / DONE both need a camera frame ----
            ok, frame = cam.read()
            if not ok:
                print("Camera failed to read a frame.")
                break

            rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            ts = int((time.monotonic() - start) * 1000)
            if ts <= last_ts:
                ts = last_ts + 1
            last_ts = ts
            result = detector.detect_for_video(image, ts)

            display = cv.cvtColor(draw_landmarks_on_image(rgb, result), cv.COLOR_RGB2BGR)

            if state == EXERCISING:
                phase, rep_done = update_jumping_jacks(result, phase)
                if rep_done:
                    reps += 1
                    print(f"Rep {reps}/{TARGET_REPS}")
                if reps >= TARGET_REPS:
                    stop_sound()
                    state = DONE
                    done_at = time.monotonic()
                put_text(display, f"Jumping jacks: {reps}/{TARGET_REPS}", 50)
                if not result.pose_landmarks:
                    put_text(display, "Step back so I can see you", 100, 0.8, (0, 0, 255))

            elif state == DONE:
                put_text(display, "Alarm off. Good morning!", 50)
                if time.monotonic() - done_at > 3:
                    break

            cv.imshow("Resisting Alarm Clock", display)
            if cv.waitKey(1) == 27 and ALLOW_ESC_QUIT:
                break

    except KeyboardInterrupt:
        print("Cancelled.")
    finally:
        stop_sound()
        if cam is not None:
            cam.release()
        cv.destroyAllWindows()


if __name__ == "__main__":
    main()