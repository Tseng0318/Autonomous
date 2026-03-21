# file:
#
# this is the ai model part, dont edit this file

import subprocess
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models
from torchvision.models.feature_extraction import create_feature_extractor


# CONFIG
MODEL_PATH = Path("resnet_bundle.pt")   # or "resnet_prototype_bundle.pt"
IMAGE_PATH = Path("capture.jpg")
WIDTH, HEIGHT = 640, 480
INPUT_SIZE = 224


# 1) CAPTURE ONE IMAGE
def capture_image():
    # Warm-up time helps exposure/AF settle
 #   cmd = [
  #       "rpicam-still",
   #      "-t", "2000",  # ms warm-up
    #     "--width", str(WIDTH),
    #     "--height", str(HEIGHT),

        # # Autofocus tuning
        # "--autofocus-mode", "continuous",
        # "--autofocus-range", "normal",
        # "--autofocus-speed", "fast",
        # "-n",  # no preview
        # "-o", str(IMAGE_PATH),
    # ]
    cmd = [
        "rpicam-still",
        "-o", str(IMAGE_PATH),  # Save image to file
    ]
    
    subprocess.run(cmd, check=True)


# 2) LOAD MODEL BUNDLE
def load_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model bundle not found: {MODEL_PATH.resolve()}")

    device = torch.device("cpu")
    bundle = torch.load(str(MODEL_PATH), map_location=device)

    required_keys = ["model_state_dict", "prototypes", "threshold", "class_names"]
    for key in required_keys:
        if key not in bundle:
            raise KeyError(f"Missing key '{key}' in bundle.")

    # Rebuild ResNet18 classifier exactly enough to load the saved weights.
    num_classes = len(bundle["class_names"])
    model = models.resnet18(weights=None)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)

    model.load_state_dict(bundle["model_state_dict"], strict=True)
    model.eval()

    # Feature extractor from avgpool, matching notebook logic
    feat_extractor = create_feature_extractor(
        model,
        return_nodes={"avgpool": "emb"}
    ).to(device)
    feat_extractor.eval()

    prototypes = bundle["prototypes"]
    if not isinstance(prototypes, torch.Tensor):
        prototypes = torch.tensor(prototypes, dtype=torch.float32)
    prototypes = prototypes.to(device).float()

    threshold = float(bundle["threshold"])
    class_names = list(bundle["class_names"])

    return feat_extractor, prototypes, threshold, class_names, device


# 3) PREPROCESS + PREDICT
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_bgr(img_bgr, device):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_rgb = cv2.resize(img_rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
    img = img_rgb.astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
    x = torch.from_numpy(img).unsqueeze(0).to(device)  # [1, 3, 224, 224]
    return x


def l2_normalize_torch(x, eps=1e-12):
    return x / x.norm(dim=1, keepdim=True).clamp_min(eps)


def predict(model, prototypes, threshold, class_names, device):
    if not IMAGE_PATH.is_file():
        raise FileNotFoundError(f"Image not found: {IMAGE_PATH.resolve()}")

    frame = cv2.imread(str(IMAGE_PATH))
    if frame is None:
        raise RuntimeError("Failed to read captured image (capture.jpg).")

    x = preprocess_bgr(frame, device)

    with torch.no_grad():
        outputs = model(x)
        emb = outputs["emb"]                  # [1, 512, 1, 1]
        emb = torch.flatten(emb, start_dim=1) # [1, 512]
        emb = l2_normalize_torch(emb)         # notebook matched

        sims = emb @ prototypes.T             # cosine similarity because both are normalized
        score, idx = sims.max(dim=1)

    idx = int(idx.item())
    score = float(score.item())

    if score >= threshold:
        label = class_names[idx]
        accepted = True
    else:
        label = "REJECT"
        accepted = False

    return {
        "label": label,
        "accepted": accepted,
        "predicted_class_index": idx,
        "predicted_class_name": class_names[idx],
        "score": score,
        "threshold": threshold,
        "similarities": sims.squeeze(0).cpu().numpy(),
    }


# MAIN
def detect_rust():
    print("Capturing image...")
    capture_image()
    print(f"Saved: {IMAGE_PATH.resolve()}")

    print("Loading model...")
    model, prototypes, threshold, class_names, device = load_model()

    print("Running inference...")
    result = predict(model, prototypes, threshold, class_names, device)

    print("\n=== Prediction ===")
    print(f"Accepted:         {result['accepted']}")
    print(f"Predicted class:  {result['label']}")
    print(f"Nearest class:    {result['predicted_class_name']}")
    print(f"Score:            {result['score']:.4f}")
    print(f"Threshold:        {result['threshold']:.4f}")
    print(f"Similarities:     {result['similarities']}")

    return result["label"], result["score"], result["similarities"]


if __name__ == "__main__":
    detect_rust()# file:
#
# this is the ai model part, dont edit this file
