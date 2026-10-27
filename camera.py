import cv2

camera = cv2.VideoCapture(0)

while True:

    ret, frame = camera.read()

    cv2.imshow("Factory Inspection Camera", frame)

    if cv2.waitKey(1) == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()