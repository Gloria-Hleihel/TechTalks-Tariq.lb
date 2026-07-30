from ultralytics import YOLO

MODEL_PATH = "models/road_damage.pt"

model = YOLO(MODEL_PATH)

print("Model loaded successfully!")
print("Model classes:")
print(model.names)