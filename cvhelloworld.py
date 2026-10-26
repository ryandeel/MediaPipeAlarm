import os
import cv2 as cv
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision

print("OpenCV:", cv.__version__)
# matrix of dimensions and then channels, channels is colors basically, rgb needs 3 channels
# and grayscale would need 1
# img = np.zeros((120, 400, 3), dtype=np.uint8)
# # image matrix, text, bottom left corner of text, font, fontscale, color, font thickness
# cv.putText(img, "OpenCV OK", (10, 80), cv.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)
# # If you installed a non-headless build, you can display a window:
# cv.imshow("hello", img); cv.waitKey(0)

cam = cv.VideoCapture(0)

while True:
    check, frame = cam.read()

    cv.imshow('video', frame)

    key = cv.waitKey(1)
    if key == 27:
        break

cam.release()
cv.destroyAllWindows()
