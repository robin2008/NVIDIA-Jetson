import cv2
import time
import numpy as np
from random import randint
import argparse
import sys
import time
from openpose import pyopenpose as op

parser = argparse.ArgumentParser(description='Run keypoint detection')
parser.add_argument("--device", default="gpu", help="Device to inference on")
parser.add_argument(
    "--video", default="/usr/local/src/image/chaplin.mp4", help="Input video")
parser.add_argument("--model", default="body25", help="model : body25 or coco")
args = parser.parse_args()


threshold = 0.2

if args.model == 'body25':
    # Body_25 model use 25 points
    key_points = {
        0:  "Nose", 1:  "Neck", 2:  "RShoulder", 3:  "RElbow", 4:  "RWrist", 5:  "LShoulder", 6:  "LElbow",
        7:  "LWrist", 8:  "MidHip", 9:  "RHip", 10: "RKnee", 11: "RAnkle", 12: "LHip", 13: "LKnee",
        14: "LAnkle", 15: "REye", 16: "LEye", 17: "REar", 18: "LEar", 19: "LBigToe", 20: "LSmallToe",
        21: "LHeel", 22: "RBigToe", 23: "RSmallToe", 24: "RHeel", 25: "Background"
    }

    # Body_25 keypoint pairs
    POSE_PAIRS = [[1, 2], [1, 5], [2, 3], [3, 4], [5, 6], [6, 7],  # arm, shoulder line
                  [1, 8], [8, 9], [9, 10], [10, 11], [
                      8, 12], [12, 13], [13, 14],  # 2 leg
                  [11, 24], [11, 22], [22, 23], [14, 21], [
                      14, 19], [19, 20],  # 2 foot
                  [1, 0], [0, 15], [15, 17], [0, 16], [16, 18],  # face
                  [2, 17], [5, 18]
                  ]

    # Body_25 PAF information 46,47? 54,55?
    mapIdx = [[40, 41], [48, 49], [42, 43], [44, 45], [50, 51], [52, 53],
              [26, 27], [32, 33], [28, 29], [30, 31], [
                  34, 35], [36, 37], [38, 39],  # 2 leg
              [76, 77], [72, 73], [74, 75], [70, 71], [
                  66, 67], [68, 69],  # 2 foot
              [56, 57], [58, 59], [62, 63], [60, 61], [64, 65],  # face
              [46, 47], [54, 55]  # Rshoulder<->REar, Lshoulder<->LEar
              ]
    nPoints = 25

else:
    key_points = {
        0:  "Nose", 1:  "Neck", 2:  "RShoulder", 3:  "RElbow", 4:  "RWrist", 5:  "LShoulder", 6:  "LElbow",
        7:  "LWrist", 8:  "RHip", 9:  "RKnee", 10: "R-Ank", 11: "LHip", 12: "LKnee", 13: "LKnee", 14: "LAnkle",
        15: "REye", 16: "LEye", 17: "REar", 18: "LEar"
    }
    POSE_PAIRS = [[1, 2], [1, 5], [2, 3], [3, 4], [5, 6], [6, 7],
                  [1, 8], [8, 9], [9, 10], [1, 11], [11, 12], [12, 13],
                  [1, 0], [0, 14], [14, 16], [0, 15], [15, 17],
                  [2, 17], [5, 16]]
    # index of pafs correspoding to the POSE_PAIRS
    # e.g for POSE_PAIR(1,2), the PAFs are located at indices (31,32) of output, Similarly, (1,5) -> (39,40) and so on.
    mapIdx = [[31, 32], [39, 40], [33, 34], [35, 36], [41, 42], [43, 44],
              [19, 20], [21, 22], [23, 24], [25, 26], [27, 28], [29, 30],
              [47, 48], [49, 50], [53, 54], [51, 52], [55, 56],
              [37, 38], [45, 46]]
    nPoints = 18


colors = [[0, 100, 255], [0, 100, 255], [0, 255, 255], [0, 100, 255], [0, 255, 255], [0, 100, 255],
          [0, 255, 0], [255, 200, 100], [255, 0, 255], [
              0, 255, 0], [255, 200, 100], [255, 0, 255],
          [0, 0, 255], [255, 0, 0], [200, 200, 0], [255, 0, 0], [200, 200, 0], [0, 0, 0]]


if args.model == 'body25':
    protoFile = "/usr/local/src/openpose-1.7.0/models/pose/body_25/pose_deploy.prototxt"
    weightsFile = "/usr/local/src/openpose-1.7.0/models/pose/body_25/pose_iter_584000.caffemodel"
else:
    protoFile = "/usr/local/src/openpose-1.7.0/models/pose/coco/pose_deploy_linevec.prototxt"
    weightsFile = "/usr/local/src/openpose-1.7.0/models/pose/coco/pose_iter_440000.caffemodel"

cap = cv2.VideoCapture(args.video)
ret, img = cap.read()
if ret == False:
    print('Video File Read Error')
    sys.exit(0)
frameHeight, frameWidth, c = img.shape

fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
out_video = cv2.VideoWriter('/tmp/%s-%s-output.mp4' % (args.model, args.device),
                            fourcc, cap.get(cv2.CAP_PROP_FPS), (frameWidth, frameHeight))
frame = 0
inHeight = 368
params = dict()
params["model_folder"] = "/usr/local/src/openpose-1.7.0/models/"
params["net_resolution"] = "368x-1"
params["display"] = "0"
opWrapper = op.WrapperPython()
opWrapper.configure(params)
opWrapper.start()
t_elapsed = 0.0

while cap.isOpened():
    f_st = time.time()
    ret, img = cap.read()
    if ret == False:
        break
    frame += 1
    datum = op.Datum()
    datum.cvInputData = img
    opWrapper.emplaceAndPop(op.VectorDatum([datum]))
    human_count = len(datum.poseKeypoints)

    frameClone = img.copy()
    for human in range(human_count):
        for j in range(nPoints):
            if datum.poseKeypoints[human][j][2] > threshold:
                # center = (int(datum.poseKeypoints[human][j][0]) ,  int(datum.poseKeypoints[human][j][1]))
                # cv2.circle(img, center, 3, color, thickness)
                cv2.circle(
                    frameClone, datum.poseKeypoints[human][j][0:2], 5, colors[j % 17], -1, cv2.LINE_AA)

    for human in range(human_count):
        for pair in POSE_PAIRS:
            if datum.poseKeypoints[human][pair[0]][2] <= threshold or datum.poseKeypoints[human][pair[1]][2] <= threshold:
                continue
            i = datum.poseKeypoints[human][pair[0]]
            S = (datum.poseKeypoints[human][pair[0]][0],
                 datum.poseKeypoints[human][pair[0]][1])
            E = (datum.poseKeypoints[human][pair[1]][0],
                 datum.poseKeypoints[human][pair[1]][1])
            cv2.line(frameClone, S, E, colors[i % 17], 3, cv2.LINE_AA)

    out_video.write(frameClone)
    f_elapsed = time.time() - f_st
    t_elapsed += f_elapsed
    print('Frame[%d] processed time[%4.2f]' % (frame, f_elapsed))


print('Total processed time[%4.2f]' % (t_elapsed))
print('avg frame processing rate :%4.2f' % (t_elapsed / frame))
cap.release()
out_video.release()
