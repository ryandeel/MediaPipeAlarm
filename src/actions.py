# actions: movements the user has to do a number of reps of to turn the alarm off
#
# HOW TO ADD AN ACTION (alarm_app.py doesn't need to change):
#   1. add a value to the Action enum, e.g. SQUATS = 3
#   2. write a function action_<name>(result, phase) that returns (new_phase, rep_done)
#      - phase is whatever you need to remember between frames ("up"/"down" etc.)
#      - rep_done is True on the one frame a rep finishes
#   3. add one line to ACTIONS at the bottom:
#      Action.SQUATS: ActionInfo(detect=action_squats, label="Squats", start_phase="up")
# the rep counter, on-screen text and turning the alarm off are handled for you

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
import math
from landmarks import *


class Action(Enum):
    JUMPING_JACKS = 1
    # CLAP = 2
    # SQUATS = 3
    PUSHUPS = 4


@dataclass
class ActionInfo:
    detect: Callable
    label: str
    start_phase: Any = None


def action_jumping_jacks(result, phase):
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

def _angle_between_points(p1, p2, p3):
    #The goal of this function is to calculate the angle between three points p1, p2, and p3. We use this for actions that have a general requirement to "count", such as pushups.
    ang = abs(math.degrees(math.atan2(p3.y - p2.y, p3.x - p2.x) - math.atan2(p1.y - p2.y, p1.x - p2.x)))
    return 360 - ang if ang > 180 else ang

def action_pushups(result, phase):
    PUSHUP_BOTTOM = 100
    PUSHUP_TOP = 150

    if not result.pose_landmarks:
        return phase, False

    lm = result.pose_landmarks[0]

    #Since we do not know which side the user will face when doing pushups, we will pick the side closest to the camera.
    if lm[LEFT_SHOULDER].z < lm[RIGHT_SHOULDER].z:
        shoulder = lm[LEFT_SHOULDER]
        elbow = lm[LEFT_ELBOW]
        wrist = lm[LEFT_WRIST]
        ankle = lm[LEFT_ANKLE]
    else:
        shoulder = lm[RIGHT_SHOULDER]
        elbow = lm[RIGHT_ELBOW]
        wrist = lm[RIGHT_WRIST]
        ankle = lm[RIGHT_ANKLE]

    #The next check we do is to see if the user is in a position that is close to a pushup.
    #We will check the line from the users shoulder to their ankle.
    dx = abs(ankle.x - shoulder.x)
    dy = abs(ankle.y - shoulder.y)
    if dx < 0.01 or dy > 0.5 * dx:
        return phase, False

    elbow_angle = _angle_between_points(shoulder, elbow, wrist)

    if phase == "up" and elbow_angle < PUSHUP_BOTTOM:
        return "down", False
    if phase == "down" and elbow_angle > PUSHUP_TOP:
        return "up", True
    return phase, False


# registry: alarm_app looks up everything it needs about an action here
#   detect      -> function(result, phase) that returns (new_phase, rep_done)
#   label       -> name shown on screen next to the rep counter
#   start_phase -> phase passed in on the first frame
ACTIONS = {
    Action.JUMPING_JACKS: ActionInfo(detect=action_jumping_jacks, label="Jumping jacks", start_phase="down"),
    Action.PUSHUPS: ActionInfo(detect=action_pushups, label="Pushups", start_phase="up"),
}
