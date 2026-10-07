from pathlib import Path
import mediapipe as mp
import cv2
import math

##get da image from the outputs/gen_images folder
image_path = (
    Path(__file__).resolve().parent
    / "outputs" / "gen_images" / "generated_face.png"
)

image = mp.Image.create_from_file(str(image_path))
print("Loaded image:", image.width, "×", image.height)

model_path = Path(__file__).resolve().parent / "models" / "face_landmarker.task"

##selects model and still -image mode, and sets the number of faces to detect to 1
options = mp.tasks.vision.FaceLandmarkerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
    running_mode=mp.tasks.vision.RunningMode.IMAGE,
    num_faces=1,
)
## detects the face in the image and prints the number of faces detected,,, finds facial landmarks
with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
    result = detector.detect(image)

print("Faces detected:", len(result.face_landmarks))

## if no face, error out 
if not result.face_landmarks:
    raise SystemExit("No face detected.")

##Copies the image’s pixel array so we can draw on it without changing the original,,, 
overlay = image.numpy_view().copy()

##loop to find first face 
for point in result.face_landmarks[0]:
    ##Converts normalized coordinates into pixel positions. For example, point.x = 0.5 on a 1024-pixel-wide image means x = 512.
    x = round(point.x * image.width)
    y = round(point.y * image.height)
    cv2.circle(overlay, (x, y), 2, (0, 255, 0), -1)

output_path = image_path.with_name("landmark_overlay.png")
##converts MediaPipe’s rgb pixel order to OpenCV’s bgr order (why is this even bro), then saves overlay
cv2.imwrite(str(output_path), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
print("Saved:", output_path)

###measures the mouth opening ratio by measuring the distance between the upper and lower lips (thats what 13 and 14 is) 
# and divides it by the width (61 and 291)
landmarks = result.face_landmarks[0]

def pixel_position(index):
    point = landmarks[index]
    return (point.x * image.width, point.y * image.height)

mouth_gap = math.dist(pixel_position(13), pixel_position(14))
mouth_width = math.dist(pixel_position(61), pixel_position(291))

mouth_open_ratio = mouth_gap / mouth_width
print("Mouth opening ratio:", round(mouth_open_ratio, 3))