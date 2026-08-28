"""
app/utils/face_utils.py

Biometric utility library for face detection, image preprocessing, quality validation,
and feature encoding comparison for the Roll Call attendance system.
Uses OpenCV for face detection (no dlib required).
"""

import base64
import logging
import numpy as np
import cv2
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image
import io

# Setup module logger
logger = logging.getLogger(__name__)


# ✅ Try to import face_recognition, fallback to OpenCV if not available
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition not available - using OpenCV fallback")


def decode_base64_image(base64_str: str) -> Optional[np.ndarray]:
    """
    Decode a base64 encoded image string into an OpenCV BGR image array.
    """
    if not base64_str or not isinstance(base64_str, str):
        logger.warning("[FaceUtils] Input base64 string is empty or invalid.")
        return None

    try:
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]

        image_bytes = base64.b64decode(base64_str.strip())
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.error("[FaceUtils] Image decoding yielded None.")
            return None

        return img
    except Exception as e:
        logger.exception(f"[FaceUtils] Failed to decode base64 image string: {e}")
        return None


def decode_base64_image_pil(base64_str: str) -> Tuple[Optional[np.ndarray], Optional[Image.Image]]:
    """
    Decode a base64 encoded image string into both numpy array and PIL Image.
    """
    if not base64_str or not isinstance(base64_str, str):
        return None, None

    try:
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]

        image_bytes = base64.b64decode(base64_str.strip())
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        rgb_array = np.array(pil_image)
        return rgb_array, pil_image
    except Exception as e:
        logger.exception(f"[FaceUtils] Failed to decode base64 image: {e}")
        return None, None


def encode_image_to_base64(img: np.ndarray, format_ext: str = ".jpg") -> Optional[str]:
    """
    Convert an OpenCV image matrix back into a base64 data URL string.
    """
    try:
        success, buffer = cv2.imencode(format_ext, img)
        if not success:
            return None
        b64_data = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_data}"
    except Exception as e:
        logger.exception(f"[FaceUtils] Failed to encode image to base64: {e}")
        return None


def inspect_face_quality(
    img: np.ndarray, face_location: Tuple[int, int, int, int]
) -> Dict[str, Any]:
    """
    Perform structural quality verification on the detected face region.
    """
    if img is None or not isinstance(img, np.ndarray):
        return {"valid": False, "reason": "Invalid image matrix provided."}

    top, right, bottom, left = face_location
    h, w, _ = img.shape

    face_height = bottom - top
    face_width = right - left

    if face_height < 35 or face_width < 35:
        return {
            "valid": False,
            "reason": f"Face area is too small ({face_width}x{face_height}px). Move closer to the camera.",
        }

    top = max(0, top)
    left = max(0, left)
    bottom = min(h, bottom)
    right = min(w, right)

    crop = img[top:bottom, left:right]
    if crop.size == 0:
        return {"valid": False, "reason": "Extracted face bounding box is empty."}

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(gray))
    std_contrast = float(np.std(gray))
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    if mean_brightness < 20.0:
        return {"valid": False, "reason": "Environment is too dark. Move to a well-lit area."}
    if mean_brightness > 245.0:
        return {"valid": False, "reason": "Lighting is overexposed or washed out."}
    if std_contrast < 10.0:
        return {"valid": False, "reason": "Low image contrast detected. Adjust room lighting."}
    if laplacian_var < 15.0:
        return {"valid": False, "reason": "Image is blurry. Keep your device steady while scanning."}

    return {
        "valid": True,
        "reason": "Quality check passed.",
        "metrics": {
            "brightness": mean_brightness,
            "contrast": std_contrast,
            "blur_score": laplacian_var,
        },
    }


def detect_faces_opencv(rgb_array: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect faces using OpenCV's Haar Cascade classifier.
    Returns list of face locations as (top, right, bottom, left).
    """
    # Convert RGB to grayscale for OpenCV
    gray = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
    
    # Load the pre-trained face cascade
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )
    
    # Convert from (x, y, w, h) to (top, right, bottom, left)
    locations = []
    for (x, y, w, h) in faces:
        locations.append((y, x + w, y + h, x))
    
    return locations


def extract_face_encoding_from_array(
    rgb_array: np.ndarray, model: str = "hog"
) -> Tuple[Optional[np.ndarray], int, str]:
    """
    Extract face encoding from a numpy RGB array.
    Uses face_recognition if available, otherwise falls back to OpenCV.
    """
    if rgb_array is None:
        return None, 0, "Invalid image array provided."

    # Try face_recognition first if available
    if FACE_RECOGNITION_AVAILABLE:
        try:
            face_locations = face_recognition.face_locations(rgb_array, model=model)
            
            if not face_locations:
                return None, 0, "No face detected in the camera frame."
            
            if len(face_locations) > 1:
                return None, len(face_locations), "Multiple faces detected."
            
            encodings = face_recognition.face_encodings(rgb_array, known_face_locations=face_locations)
            if not encodings:
                return None, 1, "Could not compute biometric signature."
            
            if np.std(encodings[0]) < 0.1:
                return None, 1, "Low quality face encoding."
            
            return encodings[0], 1, "Success"
        except Exception as e:
            logger.error(f"[FaceUtils] face_recognition error: {e}")
            # Fall through to OpenCV fallback
    
    # Fallback: Use OpenCV for face detection and create a simple encoding
    try:
        face_locations = detect_faces_opencv(rgb_array)
        
        if not face_locations:
            return None, 0, "No face detected in the camera frame."
        
        if len(face_locations) > 1:
            return None, len(face_locations), "Multiple faces detected."
        
        # Create a simple encoding from the face region (placeholder)
        # This is a fallback - for production, you'd want a proper face embedding
        top, right, bottom, left = face_locations[0]
        face_region = rgb_array[top:bottom, left:right]
        
        # Resize to a fixed size and flatten to create a simple encoding
        resized = cv2.resize(face_region, (64, 64))
        encoding = resized.flatten().astype(np.float64)[:128]  # Take first 128 values
        
        return encoding, 1, "Success (OpenCV fallback)"
    except Exception as e:
        logger.exception(f"[FaceUtils] OpenCV face detection failed: {e}")
        return None, 0, f"Face detection error: {str(e)}"


def extract_face_encoding(
    base64_str: str, model: str = "hog"
) -> Tuple[Optional[np.ndarray], str]:
    """
    Locates faces within a base64 image string and computes a biometric vector.
    """
    rgb_array, pil_image = decode_base64_image_pil(base64_str)
    if rgb_array is None:
        return None, "Invalid or unreadable image payload."

    encoding, count, msg = extract_face_encoding_from_array(rgb_array, model)
    if encoding is None:
        return None, msg
    return encoding, "Success"


def extract_face_encoding_from_rgb(
    rgb_array: np.ndarray, model: str = "hog"
) -> Tuple[Optional[np.ndarray], str]:
    """
    Extract face encoding from a numpy RGB array.
    """
    encoding, count, msg = extract_face_encoding_from_array(rgb_array, model)
    if encoding is None:
        return None, msg
    return encoding, "Success"


def match_encoding(
    known_encoding: np.ndarray,
    candidate_encoding: np.ndarray,
    tolerance: float = 0.55,
) -> Tuple[bool, float]:
    """
    Calculates distance between stored facial encoding and incoming scan vector.
    """
    if known_encoding is None or candidate_encoding is None:
        return False, 1.0

    try:
        known = np.asarray(known_encoding, dtype=np.float64).flatten()
        candidate = np.asarray(candidate_encoding, dtype=np.float64).flatten()

        # Ensure both arrays have the same length
        min_len = min(len(known), len(candidate), 128)
        known = known[:min_len]
        candidate = candidate[:min_len]

        # Calculate Euclidean distance
        distance = np.linalg.norm(known - candidate)
        
        # For fallback encoding, scale differently
        if not FACE_RECOGNITION_AVAILABLE:
            # Adjust tolerance for fallback encoding (larger values)
            tolerance = 50.0
            distance = distance / 10.0  # Scale down for comparison

        is_match = distance <= tolerance
        return is_match, float(distance)
    except Exception as e:
        logger.exception(f"[FaceUtils] Error comparing facial vectors: {e}")
        return False, 1.0


def serialize_encoding(encoding: np.ndarray) -> bytes:
    """
    Convert numpy array biometric encoding vector into binary bytes format.
    """
    if encoding is None:
        return b""
    return np.asarray(encoding, dtype=np.float64).tobytes()


def deserialize_encoding(encoding_bytes: bytes) -> Optional[np.ndarray]:
    """
    Reconstruct numpy array encoding vector from database binary blob.
    """
    if not encoding_bytes:
        return None
    try:
        return np.frombuffer(encoding_bytes, dtype=np.float64)
    except Exception as e:
        logger.error(f"[FaceUtils] Deserialization failure: {e}")
        return None


def save_reference_photo(pil_image, upload_folder, user_id):
    """
    Save a reference photo for a user.
    """
    import os
    import uuid
    
    os.makedirs(upload_folder, exist_ok=True)
    filename = f"student_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
    path = os.path.join(upload_folder, filename)
    pil_image.save(path, "JPEG", quality=92, optimize=True)
    return filename


class FaceError(Exception):
    """Raised for face processing errors."""
    pass