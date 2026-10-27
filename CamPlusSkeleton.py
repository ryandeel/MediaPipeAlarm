#I literally just copy pasted this from avery and ryans code lol.

import os
import cv2 as cv
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, drawing_styles

#copy pasted from ryans code 
def draw_landmarks_on_image(rgb_image, detection_result):
    annotated_image = np.copy(rgb_image)
    pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
    pose_connection_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)

    for pose_landmarks in detection_result.pose_landmarks:
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=pose_landmarks,
            connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=pose_landmark_style,
            connection_drawing_spec=pose_connection_style)
    return annotated_image

model_path = os.path.abspath("models/pose_landmarker_heavy.task")

options = vision.PoseLandmarkerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
    running_mode=vision.RunningMode.IMAGE)
detector = vision.PoseLandmarker.create_from_options(options)

#cam setup from avery 

cam = cv.VideoCapture(0)

while True:
    check, frame = cam.read()

    #replacement: instead of loading a file, wrap the camera frame
    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB) #OpenCV is BGR, MediaPipe wants RGB,  they store color differently sso this'll fix it prolly
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    #detect posess
    detection_result = detector.detect(image) #pose model does its magic and finds the person/landmarkss on them

    #draw, then convert back to BGR for OpenCV to display
    annotated_image = draw_landmarks_on_image(rgb, detection_result)
    cv.imshow('video', cv.cvtColor(annotated_image, cv.COLOR_RGB2BGR)) #dissplays skeleton onto the current frame :)

    
    key = cv.waitKey(1)
    if key == 27:                         
        break

cam.release()
cv.destroyAllWindows()