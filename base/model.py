# file: 
#
# this is the ai model part, dont edit this file

import os
import subprocess
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

# CONFIG
MODEL_PATH = Path("resnet18_deploy.pt")          # model file
IMAGE_PATH = Path("capture.jpg")       # captured image file
WIDTH, HEIGHT = 640, 480
INPUT_SIZE = 224

CLASS_NAMES = ["CORROSION", "NOCORROSION"]

# 1) CAPTURE ONE IMAGE
def capture_image():
    # Warm-up time helps exposure/AF settle
    cmd = [
        "rpicam-still",
        "-t", "2000",  # ms warm-up
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        
     # Autofocus tuning 
        "--autofocus-mode", "continuous",  # let AF settle over the warm-up period
        "--autofocus-range", "normal",     # normal / macro (use macro if you're very close)
        "--autofocus-speed", "fast",       # fast / normal
        "-n",  # no preview
        "-o", str(IMAGE_PATH),
    ]
    subprocess.run(cmd, check=True)

# 2) LOAD MODEL
def load_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH.resolve()}")

    device = torch.device("cpu")

    # TorchScript first, then fallback to torch.load(full-model)
    try:
        model = torch.jit.load(str(MODEL_PATH), map_location=device)
    except Exception:
        model = torch.load(str(MODEL_PATH), map_location=device)

    model.eval()
    return model, device

# 3) PREPROCESS + PREDICT
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def preprocess_bgr(img_bgr, device):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_rgb = cv2.resize(img_rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
    img = img_rgb.astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
    x = torch.from_numpy(img).unsqueeze(0).to(device)  # [1,3,224,224]
    return x

def predict(model, device):
    if not IMAGE_PATH.is_file():
        raise FileNotFoundError(f"Image not found: {IMAGE_PATH.resolve()}")

    frame = cv2.imread(str(IMAGE_PATH))
    if frame is None:
        raise RuntimeError("Failed to read captured image (capture.jpg).")

    x = preprocess_bgr(frame, device)

    with torch.no_grad():
        logits = model(x)
        probs = F.softmax(logits, dim=1)

    conf, idx = torch.max(probs, dim=1)
    idx = int(idx.item())
    conf = float(conf.item())

    label = CLASS_NAMES[idx] if 0 <= idx < len(CLASS_NAMES) else f"class_{idx}"
    return label, conf, probs.squeeze().cpu().numpy()


# MAIN
def detect_rust():
    print("Capturing image...")
    capture_image()
    print(f"Saved: {IMAGE_PATH.resolve()}")

    print("Loading model...")
    model, device = load_model()

    print("Running inference...")
    label, conf, probs = predict(model, device)

    print("\n=== Prediction ===")
    print(f"Predicted class: {label}")
    print(f"Confidence:      {conf:.4f}")
    print(f"Probabilities:   {probs}")
    return label, conf, probs

if __name__ == "__main__":
    detect_rust()
