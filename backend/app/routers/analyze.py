from fastapi import APIRouter

router = APIRouter()

@router.post("/analyze")
def analyze():
    return {"message": "analyze endpoint ready"}