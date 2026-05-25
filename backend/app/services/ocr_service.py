import logging
from pathlib import Path
from PIL import Image
import numpy as np
import io

logger = logging.getLogger(__name__)

class OCRService:
    """
    Wraps PaddleOCR to extract Japanese text from images.
    
    Uses a singleton pattern — the model is heavy (~200MB) and slow
    to initialize. We load it once at startup and reuse it for every
    request. This is standard practice for ML model serving.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        """
        Load the PaddleOCR model. Called once at application startup.
        Separated from __init__ so we can control when the heavy load happens.
        """
        if self._initialized:
            return

        logger.info("Initializing PaddleOCR model — this takes ~10s on first run...")

        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(
            use_angle_cls=True,   # handles rotated text (e.g. vertical signs)
            lang="japan",         # Japanese language model
            show_log=False,       # suppress verbose paddle logs
        )

        self._initialized = True
        logger.info("PaddleOCR initialized successfully.")

    def extract_text(self, image_bytes: bytes) -> str:
        """
        Extract Japanese text from raw image bytes.
        Returns all detected text joined as a single string.
        
        Args:
            image_bytes: Raw bytes of a JPEG, PNG, or WebP image
            
        Returns:
            Extracted Japanese text as a single string.
            Empty string if no text is detected.
        """
        if not self._initialized:
            raise RuntimeError("OCRService not initialized. Call initialize() first.")

        # Convert bytes → PIL Image → numpy array
        # PaddleOCR expects a numpy array (H, W, C) in BGR format
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)

        result = self._ocr.ocr(image_np, cls=True)

        if not result or not result[0]:
            logger.warning("PaddleOCR returned no results for this image.")
            return ""

        # result structure: [[[box, (text, confidence)], ...]]
        # We extract just the text strings, filter low-confidence results
        lines = []
        for line in result[0]:
            text, confidence = line[1]
            if confidence >= 0.7:   # discard likely noise
                lines.append(text)

        extracted = "\n".join(lines)
        logger.info(f"Extracted {len(lines)} text regions, confidence >= 0.7")

        return extracted


# Module-level singleton instance
ocr_service = OCRService()