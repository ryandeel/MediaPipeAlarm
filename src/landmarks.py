# landmark indices from the mediapipe 33-point pose model
# https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
#
# left and right are swapped compared to the mediapipe docs on purpose:
# alarm_app flips the camera frame like a mirror, so mediapipe's "left"
# ends up being the user's right side on screen

NOSE = 0
RIGHT_SHOULDER, LEFT_SHOULDER = 11, 12
RIGHT_ELBOW, LEFT_ELBOW = 13, 14
RIGHT_WRIST, LEFT_WRIST = 15, 16
RIGHT_HIP, LEFT_HIP = 23, 24
RIGHT_KNEE, LEFT_KNEE = 25, 26
RIGHT_ANKLE, LEFT_ANKLE = 27, 28

