"""
End-to-end pipeline test without the HTTP layer.
Tests the full M-02 → M-03 → M-04 → M-05 chain.

Run with: docker compose exec backend python test_pipeline.py <image_path>
"""
import sys
import json
from app.services.ocr_service import ocr_service
from app.services.nlp_service import nlp_service
from app.services.ai_service import ai_service

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Initializing all services...")
    ocr_service.initialize()
    nlp_service.initialize()
    ai_service.initialize()

    print(f"\n── Step 1: OCR ──")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    raw_text = ocr_service.extract_text(image_bytes)
    print(f"Extracted: {raw_text}")

    print(f"\n── Step 2: NLP ──")
    tokens = nlp_service.tokenize(raw_text)
    for t in tokens:
        print(f"  {t.surface} | {t.reading} | {t.pos}")

    print(f"\n── Step 3: AI ──")
    result = ai_service.explain(raw_text, "other", tokens)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n── Pipeline complete ──")

if __name__ == "__main__":
    main()