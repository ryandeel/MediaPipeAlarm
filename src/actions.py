# actions: movements the user has to do a number of reps of to turn the alarm off

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from landmarks import *


class Action(Enum):
    JUMPING_JACKS = 1
    # CLAP = 2
    # SQUATS = 3


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


# registry: alarm_app looks up everything it needs about an action here
#   detect      -> function(result, phase) that returns (new_phase, rep_done)
#   label       -> name shown on screen next to the rep counter
#   start_phase -> phase passed in on the first frame
ACTIONS = {
    Action.JUMPING_JACKS: ActionInfo(detect=action_jumping_jacks, label="Jumping jacks", start_phase="down"),
}
