"""
Quick local test for NLPService.
Run with: docker compose exec backend python test_nlp.py
"""
from app.services.nlp_service import nlp_service

TEST_SENTENCES = [
    "東京駅の出口",           # train station sign
    "本日のおすすめ定食",      # menu item
    "立入禁止",               # warning sign
    "営業時間：10時〜22時",    # business hours notice
]

def main():
    print("Initializing NLP service...")
    nlp_service.initialize()

    for sentence in TEST_SENTENCES:
        print(f"\n--- Input: {sentence} ---")
        tokens = nlp_service.tokenize(sentence)
        for t in tokens:
            print(f"  {t.surface:10} | {t.reading:10} | {t.romaji:15} | {t.pos:15} | base: {t.base_form}")

if __name__ == "__main__":
    main()