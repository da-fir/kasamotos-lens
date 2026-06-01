import logging
import pykakasi
from app.models.schemas import Token

logger = logging.getLogger(__name__)


class NLPService:
    """
    Wraps SudachiPy to tokenize Japanese text into structured Token objects.

    SudachiPy is a morphological analyzer — it splits Japanese sentences
    into their smallest meaningful units (morphemes), and identifies each
    word's reading, part of speech, and dictionary form.

    Like OCRService, we use a singleton to avoid reloading the dictionary
    (200MB) on every request.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        if self._initialized:
            return

        logger.info("Initializing SudachiPy tokenizer...")

        import sudachipy.dictionary as sudachi_dict
        import sudachipy

        self._tokenizer = sudachi_dict.Dictionary(dict="full").create()
        self._mode = sudachipy.SplitMode.C  # C mode = natural word boundaries

        # pykakasi for katakana → hiragana and romaji conversion
        kks = pykakasi.kakasi()
        self._kakasi = kks

        self._initialized = True
        logger.info("SudachiPy initialized successfully.")

    def _katakana_to_hiragana(self, text: str) -> str:
        """Convert katakana reading to hiragana for furigana display."""
        result = []
        for char in text:
            code = ord(char)
            # Katakana range: 0x30A0–0x30FF → shift to hiragana 0x3040–0x309F
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)

    def _to_romaji(self, text: str) -> str:
        """Convert Japanese text to romaji using pykakasi."""
        result = self._kakasi.convert(text)
        return "".join([item["hepburn"] for item in result])

    def _map_pos(self, sudachi_pos: tuple) -> str:
        """
        Map SudachiPy's detailed POS tuple to a simple English label.
        SudachiPy returns a tuple like ('動詞', '一般', '*', '*', ...)
        We map the first element (main POS) to English.
        """
        pos_map = {
            "名詞": "noun",
            "動詞": "verb",
            "形容詞": "adjective",
            "形容動詞": "adjective",
            "副詞": "adverb",
            "助詞": "particle",
            "助動詞": "auxiliary verb",
            "接続詞": "conjunction",
            "感動詞": "interjection",
            "接頭辞": "prefix",
            "接尾辞": "suffix",
            "記号": "symbol",
            "空白": "whitespace",
            "補助記号": "symbol",
        }
        main_pos = sudachi_pos[0] if sudachi_pos else "unknown"
        return pos_map.get(main_pos, main_pos)

    def tokenize(self, text: str) -> list[Token]:
        """
        Tokenize Japanese text into a list of Token objects.

        Args:
            text: Raw Japanese text (output from OCRService)

        Returns:
            List of Token objects with surface, reading, romaji, pos,
            base_form, and meaning fields.
            Note: meaning is left empty here — filled in by AIService.
        """
        if not self._initialized:
            raise RuntimeError("NLPService not initialized. Call initialize() first.")

        morphemes = self._tokenizer.tokenize(text, self._mode)

        tokens = []
        for m in morphemes:
            surface = m.surface()

            # Skip pure whitespace tokens
            if surface.strip() == "":
                continue

            reading_kata = m.reading_form()
            reading_hira = self._katakana_to_hiragana(reading_kata)
            romaji = self._to_romaji(reading_hira or surface)
            pos = self._map_pos(m.part_of_speech())
            base_form = m.dictionary_form()

            tokens.append(Token(
                surface=surface,
                reading=reading_hira,
                romaji=romaji,
                pos=pos,
                base_form=base_form,
                meaning="",  # AIService fills this in later
                jlpt_level=None,  # Phase 2
            ))

        return tokens


# Module-level singleton
nlp_service = NLPService()