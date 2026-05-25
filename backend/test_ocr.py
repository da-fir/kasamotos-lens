"""
Quick local test for OCRService.
Run with: python test_ocr.py <path_to_image>

Usage:
    python test_ocr.py sample.jpg
"""
import sys
from app.services.ocr_service import ocr_service

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Initializing OCR service...")
    ocr_service.initialize()

    print(f"Processing: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result = ocr_service.extract_text(image_bytes)

    print("\n--- Extracted Text ---")
    print(result if result else "(no text detected)")
    print("----------------------")

if __name__ == "__main__":
    main()