from ultralytics import YOLO
import cv2

model = YOLO("yolov8n.pt")

camera = cv2.VideoCapture(0)

while True:

    ret, frame = camera.read()

    results = model(frame)

    annotated_frame = results[0].plot()

    cv2.imshow("AI Inspection Camera", annotated_frame)

    if cv2.waitKey(1) == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()