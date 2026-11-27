# poses: positions the user has to hold for a few seconds to turn the alarm off

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from landmarks import *
from utils import calcul_angle, put_text


class Pose(Enum):
    DOUBLE_BI = 1
    HANDS_UP = 2


@dataclass
class PoseInfo:
    detect: Callable
    image: Optional[str] = None


def pose_double_bi(result, display):
    if not result.pose_landmarks:
            return False

    lm = result.pose_landmarks[0]

    # make sure they aren't facing sideways
    shoulder_w = abs(lm[LEFT_SHOULDER].x - lm[RIGHT_SHOULDER].x)
    if shoulder_w < 0.01:
        return False

    # get angle of left arm
    angle_left_arm = calcul_angle(lm[LEFT_SHOULDER].x, lm[LEFT_SHOULDER].y, lm[LEFT_ELBOW].x, lm[LEFT_ELBOW].y, lm[LEFT_WRIST].x, lm[LEFT_WRIST].y)
    # get angle of right arm
    angle_right_arm = calcul_angle(lm[RIGHT_SHOULDER].x, lm[RIGHT_SHOULDER].y, lm[RIGHT_ELBOW].x, lm[RIGHT_ELBOW].y, lm[RIGHT_WRIST].x, lm[RIGHT_WRIST].y)

    if "--debug" in sys.argv:
        put_text(display, f"angles: {angle_right_arm:.0f} {angle_left_arm:.0f}", 50, x=200)

    is_left_flex = (30 < angle_left_arm < 110) and (lm[LEFT_WRIST].y < lm[LEFT_SHOULDER].y)
    is_right_flex = (30 < angle_right_arm < 110) and (lm[RIGHT_WRIST].y < lm[RIGHT_SHOULDER].y)

    return is_left_flex and is_right_flex


# ported from avery's hands_above_head_pose on main
def pose_hands_up(result, display):
    if not result.pose_landmarks:
        return False

    lm = result.pose_landmarks[0]
    return lm[LEFT_WRIST].y < lm[NOSE].y and lm[RIGHT_WRIST].y < lm[NOSE].y


# registry: alarm_app looks up everything it needs about a pose here
#   detect -> function(result, display) that returns True while the user is in the pose
#   image  -> reference picture shown in the corner (file in the repo root), or None
POSES = {
    Pose.DOUBLE_BI: PoseInfo(detect=pose_double_bi, image="pose_double_bi.jpg"),
    Pose.HANDS_UP: PoseInfo(detect=pose_hands_up),
}
