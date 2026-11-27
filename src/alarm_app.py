"""
IMPORTANT STUFF TO KNOW DEVELOPERS:

i made it so that running with the debug flag (i.e. python ./alarm_app.py --debug)
will show text (angles in the pose_double_bi function), i implore you
to use the if statement: {if "--debug" in sys.argv:} whenever you want to show certain
variables during debugging or testing
the debug stuff will stay here in development but will never reach main branch, basically
when we are done with coding this and we push to main, please do not push this comment block
and the debug flags, leave it in the dev branch though because its important dev tools

enums for poses and actions are below constants, feel free to move around or change
non-implemented poses and actions as you see fit, but please don't mess with the enums
for already implemented poses and actions
"""

"""
HOW SETTING THE ALARM WORKS:

so, you want to set your alarm, don't you?
alright well listen up, setting your alarm is a flag, yep thats right
whenever you call "python alarm_app.py" you can specify the time right after!

here are your options:
just a number, i.e. python alarm_app.py 3, this sets your alarm for 3 seconds after now

a duration, i.e. python alarm_app.py 1h30m or 10m or 45s, this sets your alarm 
                                                         for however long from now

a clock time, i.e. python alarm_app.py 7:30 or 07:30 or 7:30pm or 6pm, this sets your alarm
                                                                       for a specified clock time
"""


import os
import sys
import time
import wave
import datetime
import winsound  # built into Windows
import random
import argparse
import re

import cv2 as cv
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, drawing_styles

from landmarks import *
from utils import calcul_angle, put_text, overlay_corner
from poses import Pose, POSES
from actions import Action, ACTIONS

# seed randomizer
random.seed()

# constants
BASE_REPS = 5 # average reps needed for whatever action you use
BASE_TIME = 5 # average time in seconds for holding a pose

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(FILE_DIR)
MODEL_PATH = os.path.join(BASE_DIR, "models", "pose_landmarker_heavy.task")
SOUND_PATH = os.path.join(BASE_DIR, "alarm.wav")

def load_pose_image(filename, size=(200, 200)):
    """load a reference picture for a pose, or None if it has no picture / file is missing"""
    if filename is None:
        return None
    img = cv.imread(os.path.join(BASE_DIR, filename))
    if img is None:
        print(f"Warning: couldn't load pose image {filename!r}")
        return None
    return cv.resize(img, size)

# states
IDLE, RINGING, POSE, ACTION, DONE = "IDLE", "RINGING", "POSE", "ACTION", "DONE"

def main():
    options = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5)
    pose_landmarker = vision.PoseLandmarker.create_from_options(options)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("time", nargs="?", default="5s",
                        help="e.g. 3, 10m, 1h30m, 7:30, 6:45pm (default: 5s)")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        alarm_dt = parse_alarm(args.time)
    except ValueError as e:
        parser.error(str(e))
        
    print(f"Alarm set for {alarm_dt.strftime('%Y-%m-%d %H:%M:%S')}. Press Ctrl+C to cancel.")
    
    state = IDLE
    cap = None
    done_at = None
    action = random.choice(list(Action))
    pose = random.choice(list(Pose))
        
    frame_timestamp_ms = 0
    # psuedorandomly select between an action or pose
    action_or_pose = random.randint(0,1)
    
    try:
        while True:
            # idle state: wait for the alarm time
            if state == IDLE:
                if datetime.datetime.now() >= alarm_dt:
                    state = RINGING
                else:
                    time.sleep(0.5)
                continue
            
            # ringing state: start alarm and open camera
            if state == RINGING:
                if action_or_pose == 0:
                    print("WAKE UP! Strike a pose to turn it off.")
                    start_sound()
                    cap = cv.VideoCapture(0)
                    pose_started_at = None
                    pose_img = load_pose_image(POSES[pose].image)
                    state = POSE
                else:
                    print("WAKE UP! Do an action to turn it off.")
                    start_sound()
                    cap = cv.VideoCapture(0)
                    reps = 0
                    phase = ACTIONS[action].start_phase
                    state = ACTION
                continue
            
            # doing stuff / done state
            success, frame = cap.read()
            if not success:
                print("Camera failed to read a frame.")
                break
            
            frame = cv.flip(frame, 1)
            rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            # 30 fps
            frame_timestamp_ms += 33
            result = pose_landmarker.detect_for_video(mp_image, frame_timestamp_ms)
            
            display = cv.cvtColor(draw_landmarks_on_image(rgb, result), cv.COLOR_RGB2BGR)
            
            if state == ACTION:
                # works for every action in the ACTIONS registry
                info = ACTIONS[action]
                phase, rep_done = info.detect(result, phase)
                if rep_done:
                    reps += 1
                    print(f"Rep {reps}/{BASE_REPS}")
                if reps >= BASE_REPS:
                    stop_sound()
                    state = DONE
                    done_at = time.monotonic()
                put_text(display, f"{info.label}: {reps}/{BASE_REPS}", 50)
                if not result.pose_landmarks:
                    put_text(display, "Step back or find a more well-lit room", 100, 0.8, (0, 0, 255))

            if state == POSE:
                # works for every pose in the POSES registry
                put_text(display, "Strike a pose!", 50)
                if pose_img is not None:
                    overlay_corner(display, pose_img, alpha=0.75)

                is_in_pose = POSES[pose].detect(result, display)
                if is_in_pose:
                    if pose_started_at is None:
                        pose_started_at = time.monotonic()
                    held = time.monotonic() - pose_started_at
                    put_text(display, f"Hold it! {held:.1f}/{BASE_TIME}s", 100)

                    if held >= BASE_TIME:
                        stop_sound()
                        state = DONE
                        done_at = time.monotonic()
                        pose_started_at = None
                else:
                    pose_started_at = None   # broke the pose, restart the timer

                if not result.pose_landmarks:
                    put_text(display, "Step back or find a more well-lit room", 150, 0.8, (0, 0, 255))

            elif state == DONE:
                put_text(display, "Alarm off. Good morning!", 50)
                if time.monotonic() - done_at > 3:
                    break
            
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

# thanks claude for some alarm stuff
def parse_alarm(text):
    now = datetime.datetime.now()
    text = text.strip().lower().replace(" ", "")

    # plain number -> seconds
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return now + datetime.timedelta(seconds=float(text))

    # duration: 1h30m, 10m, 45s
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
    if m and any(m.groups()):
        h, mins, s = (int(g or 0) for g in m.groups())
        return now + datetime.timedelta(hours=h, minutes=mins, seconds=s)

    # clock time: 7:30, 07:30, 7:30pm, 6pm
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", text)
    if m and (":" in text or m.group(3)):
        hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        if hour < 24 and minute < 60:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
            return target

    raise ValueError(f"Couldn't understand alarm time: {text!r}")

if __name__ == "__main__":
    main()
    