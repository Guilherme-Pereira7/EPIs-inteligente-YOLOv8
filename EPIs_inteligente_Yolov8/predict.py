from ultralytics import YOLO
import cv2
import argparse

parser = argparse.ArgumentParser(description="Detect EPIs in image/video/webcam")
parser.add_argument("--source", default="0", help="0 for webcam, or path to image/video")
parser.add_argument("--weights", default="runs/epis/weights/best.pt")
args = parser.parse_args()

model = YOLO(args.weights)
source = int(args.source) if args.source.isdigit() else args.source
model.predict(source=source, conf=0.35, show=True, save=True)
