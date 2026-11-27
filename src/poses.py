# poses: positions the user has to hold for a few seconds to turn the alarm off
#
# HOW TO ADD A POSE (alarm_app.py doesn't need to change):
#   1. add a value to the Pose enum, e.g. T_POSE = 3
#   2. write a function pose_<name>(result, display) that returns True while
#      the user is in the pose (result.pose_landmarks[0] has the landmarks,
#      use the constants from landmarks.py to index it)
#   3. add one line to POSES at the bottom: Pose.T_POSE: PoseInfo(detect=pose_t_pose)
#      optionally pass image="images/some_picture.jpg" (path from the repo root) to show a
#      reference picture in the corner
# the hold timer, on-screen text and turning the alarm off are handled for you

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from landmarks import *
from utils import calcul_angle, put_text


class Pose(Enum):
    DOUBLE_BI = 1
    HANDS_UP = 2
    TOE_TOUCH = 3


@dataclass
class PoseInfo:
    detect: Callable
    image: Optional[str] = None

TOE_TOUCH_MIN_KNEE_ANGLE = 140  # legs have to stay mostly straight
MIN_LEG_VISIBILITY = 0.5    # 0-1 score from mediapipe for how sure it is the point is on camera

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


def pose_toe_touch(result, display):
    if not result.pose_landmarks:
        return False

    lm = result.pose_landmarks[0]

    # same reason as the squat: don't trust guessed positions for points
    # that are off camera. wrists are included since they end up down by the feet
    points = (LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE, LEFT_WRIST, RIGHT_WRIST)
    if min(lm[i].visibility for i in points) < MIN_LEG_VISIBILITY:
        put_text(display, "Step back so your whole body is visible", 150, 0.8, (0, 0, 255))
        return False

    angle_left_leg = calcul_angle(lm[LEFT_HIP].x, lm[LEFT_HIP].y, lm[LEFT_KNEE].x, lm[LEFT_KNEE].y, lm[LEFT_ANKLE].x, lm[LEFT_ANKLE].y)
    angle_right_leg = calcul_angle(lm[RIGHT_HIP].x, lm[RIGHT_HIP].y, lm[RIGHT_KNEE].x, lm[RIGHT_KNEE].y, lm[RIGHT_ANKLE].x, lm[RIGHT_ANKLE].y)

    if "--debug" in sys.argv:
        put_text(display, f"knee angles: {angle_right_leg:.0f} {angle_left_leg:.0f}", 50, x=200)

    # bigger y = lower on screen, so this means both hands reached down past the knees
    hands_down = lm[LEFT_WRIST].y > lm[LEFT_KNEE].y and lm[RIGHT_WRIST].y > lm[RIGHT_KNEE].y
    # straight legs, so squatting down and grabbing your ankles doesn't count
    legs_straight = angle_left_leg > TOE_TOUCH_MIN_KNEE_ANGLE and angle_right_leg > TOE_TOUCH_MIN_KNEE_ANGLE

    return hands_down and legs_straight


# registry: alarm_app looks up everything it needs about a pose here
#   detect -> function(result, display) that returns True while the user is in the pose
#   image  -> reference picture shown in the corner (path from the repo root), or None
POSES = {
    Pose.DOUBLE_BI: PoseInfo(detect=pose_double_bi, image="images/double_bi.png"),
    Pose.HANDS_UP: PoseInfo(detect=pose_hands_up, image="images/hands_up.webp"),
    Pose.TOE_TOUCH: PoseInfo(detect=pose_toe_touch, image="images/touching_toes.jpg"),
}
