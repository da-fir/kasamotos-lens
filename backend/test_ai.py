"""
Test AIService in isolation with hardcoded Japanese text.
No image needed — we simulate what OCR + NLP would produce.

Run with: docker compose exec backend python test_ai.py
"""
import json
from app.services.nlp_service import nlp_service
from app.services.ai_service import ai_service

# Simulate what OCR would extract from a real sign
TEST_CASES = [
    ("東京駅の出口はこちらです", "sign"),
    ("本日のおすすめ：サーモン定食 1200円", "menu"),
    ("立入禁止　関係者以外お断り", "sign"),
    ("ご注文はお決まりですか？", "menu"),
]

def main():
    print("Initializing services...")
    nlp_service.initialize()
    ai_service.initialize()

    for text, context in TEST_CASES:
        print(f"\n{'='*60}")
        print(f"Input:   {text}")
        print(f"Context: {context}")
        print(f"{'='*60}")

        # Get tokens from NLP (exactly what the pipeline will do)
        tokens = nlp_service.tokenize(text)

        # Get AI explanation
        result = ai_service.explain(text, context, tokens)

        # Pretty print the result
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()