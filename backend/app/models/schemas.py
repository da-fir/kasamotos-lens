from pydantic import BaseModel
from typing import Literal
from datetime import datetime

ContextType = Literal["sign", "menu", "notice", "letter", "other"]

class Token(BaseModel):
    surface: str
    reading: str
    romaji: str
    pos: str
    base_form: str
    meaning: str
    jlpt_level: str | None = None

class Sentence(BaseModel):
    original: str
    romaji: str
    meaning: str
    nuance: str
    grammar_pattern: str | None = None
    tokens: list[Token]

class AnalysisResult(BaseModel):
    id: str
    raw_text: str
    context_type: ContextType
    sentences: list[Sentence]
    created_at: datetime