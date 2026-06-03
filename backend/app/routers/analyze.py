import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.services.ocr_service import ocr_service
from app.services.nlp_service import nlp_service
from app.services.ai_service import ai_service
from app.models.schemas import AnalysisResult, Sentence, Token
from app.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed image types — reject everything else at the door
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _assemble_result(
    analysis_id: str,
    raw_text: str,
    ai_result: dict,
) -> AnalysisResult:
    """
    Merge AI output into our AnalysisResult schema.

    The AI returns its own token list with meanings filled in.
    We use the AI's token data since it adds the meaning field
    that NLPService leaves empty.
    """
    sentences = []

    for s in ai_result.get("sentences", []):
        tokens = [
            Token(
                surface=t.get("surface", ""),
                reading=t.get("reading", ""),
                romaji=t.get("romaji", ""),
                pos=t.get("pos", ""),
                base_form=t.get("base_form", ""),
                meaning=t.get("meaning", ""),
                jlpt_level=t.get("jlpt_level"),
            )
            for t in s.get("tokens", [])
        ]

        sentences.append(Sentence(
            original=s.get("original", ""),
            romaji=s.get("romaji", ""),
            meaning=s.get("meaning", ""),
            nuance=s.get("nuance", ""),
            grammar_pattern=s.get("grammar_pattern"),
            grammar_explanation=s.get("grammar_explanation"),
            tokens=tokens,
        ))

    return AnalysisResult(
        id=analysis_id,
        raw_text=raw_text,
        context_type=ai_result.get("context_type", "other"),
        context_explanation=ai_result.get("context_explanation", ""),
        sentences=sentences,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...)):
    """
    Main pipeline endpoint. Takes an image, returns a full AnalysisResult.

    Pipeline:
        1. Validate file
        2. OCR → raw Japanese text
        3. NLP → token list
        4. AI → meanings, nuance, grammar explanations
        5. Assemble result
        6. Persist to Supabase
        7. Return to client
    """

    # ── 1. Validate ──────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: jpeg, png, webp"
        )

    image_bytes = await file.read()

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    logger.info(f"Received image: {file.filename}, size: {len(image_bytes)} bytes")

    # ── 2. OCR ───────────────────────────────────────────────────────────
    try:
        raw_text = ocr_service.extract_text(image_bytes)
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail="OCR processing failed.")

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No Japanese text detected in this image. Try a clearer photo."
        )

    logger.info(f"OCR extracted: {raw_text[:100]}")

    # ── 3. NLP ───────────────────────────────────────────────────────────
    try:
        tokens = nlp_service.tokenize(raw_text)
    except Exception as e:
        logger.error(f"NLP tokenization failed: {e}")
        raise HTTPException(status_code=500, detail="Text analysis failed.")

    logger.info(f"NLP produced {len(tokens)} tokens")

    # ── 4. AI ────────────────────────────────────────────────────────────
    try:
        ai_result = ai_service.explain(
            raw_text=raw_text,
            context_type="other",   # Phase 2: auto-classify from image
            tokens=tokens,
        )
    except ValueError as e:
        logger.error(f"AI returned invalid response: {e}")
        raise HTTPException(status_code=500, detail="AI explanation failed.")
    except Exception as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(status_code=500, detail="AI service unavailable.")

    # ── 5. Assemble ──────────────────────────────────────────────────────
    analysis_id = str(uuid.uuid4())

    try:
        result = _assemble_result(analysis_id, raw_text, ai_result)
    except Exception as e:
        logger.error(f"Failed to assemble result: {e}")
        raise HTTPException(status_code=500, detail="Failed to assemble analysis result.")

    # ── 6. Persist ───────────────────────────────────────────────────────
    try:
        db = get_supabase()
        db.table("analyses").insert({
            "id": analysis_id,
            "raw_text": raw_text,
            "context_type": result.context_type,
            "result": result.model_dump(mode="json"),
        }).execute()
        logger.info(f"Saved analysis {analysis_id} to Supabase")
    except Exception as e:
        # Non-fatal — we still return the result even if saving fails
        # The user gets their analysis; we log the DB issue
        logger.error(f"Failed to save to Supabase: {e}")

    # ── 7. Return ────────────────────────────────────────────────────────
    return result