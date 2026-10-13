"""Read the QR code inside a photo.

Used to (a) reject photos that contain no readable QR and (b) build a
fingerprint so the same code can't be listed twice. Needs opencv-python-headless;
if it isn't installed, QR_SUPPORTED is False and the bot falls back to Telegram's
file_unique_id (weaker: a re-screenshot of the same QR would look different).
"""

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None
    np = None

QR_SUPPORTED = cv2 is not None


def decode_qr(data: bytes) -> str | None:
    """Return the text encoded in the first QR code found, or None. Blocking: run in a thread."""
    if cv2 is None or np is None:
        return None
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return None
    detector = cv2.QRCodeDetector()
    text, _, _ = detector.detectAndDecode(image)
    if text:
        return text
    # Second try: grayscale + upscale helps with small / compressed codes.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    text, _, _ = detector.detectAndDecode(gray)
    return text or None
