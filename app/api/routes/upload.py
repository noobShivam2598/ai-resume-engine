import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume_schema import (
    AnalyzeJobIn,
    AnalyzeJobOut,
    ResumeDetailOut,
    UrlAnalyzeIn,
    UrlAnalyzeOut,
)
from app.services.file_service import FileServiceError, save_upload
from app.services import parser_service
from app.services.resume_parsing_service import run_resume_parsing
from app.utils.url_text_extractor import extract_text_from_url

router = APIRouter(prefix="/api", tags=["upload"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=ResumeDetailOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: int = Form(default=1),
    db: Session = Depends(get_db),
) -> ResumeDetailOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info("Upload started user_id=%s filename=%s", user_id, file.filename)

    try:
        resume = await save_upload(db=db, user_id=user_id, upload=file)
    except FileServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    run_resume_parsing(db, resume.id)

    loaded = (
        db.query(Resume)
        .options(joinedload(Resume.parsed))
        .filter(Resume.id == resume.id)
        .first()
    )
    if loaded is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Resume missing after upload")
    return ResumeDetailOut.from_resume(loaded)


@router.post("/analyze-url", response_model=UrlAnalyzeOut)
def analyze_job_url(payload: UrlAnalyzeIn) -> UrlAnalyzeOut:
    analyzed = analyze_job(AnalyzeJobIn(job_url=payload.url))
    return UrlAnalyzeOut(
        url=payload.url,
        role=analyzed.role,
        skills=analyzed.skills_required,
        experience_years=analyzed.experience_required,
    )


@router.post("/analyze-job", response_model=AnalyzeJobOut)
def analyze_job(payload: AnalyzeJobIn) -> AnalyzeJobOut:
    logger.info("Analyze job started has_url=%s has_description=%s", bool(payload.job_url), bool(payload.job_description))

    text: str | None = None
    if payload.job_url and payload.job_url.strip():
        logger.info("Fetching job text from URL")
        text = extract_text_from_url(payload.job_url.strip())
        if not text:
            logger.warning("URL text extraction failed")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not fetch readable text from URL")
        logger.info("URL text extraction success chars=%s", len(text))
    else:
        logger.info("Using job_description from request body")
        text = (payload.job_description or "").strip()

    if not text:
        logger.warning("No job text available after source selection")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty job text provided")

    logger.info("Running Ollama structured extraction")
    llm_job = parser_service.extract_job_details_with_ollama(text)

    role = parser_service.infer_role_from_text(text)
    skills_from_text = parser_service.extract_skills(text)
    experience_years = parser_service.extract_experience_years(text)
    skills_from_llm: list[str] = []

    if isinstance(llm_job, dict):
        if isinstance(llm_job.get("role"), str) and str(llm_job.get("role")).strip():
            role = str(llm_job.get("role")).strip()
        llm_skills = llm_job.get("skills_required")
        if isinstance(llm_skills, list):
            skills_from_llm = [str(s).strip().lower() for s in llm_skills if str(s).strip()]
        llm_exp = llm_job.get("experience_required")
        if experience_years is None and isinstance(llm_exp, int) and llm_exp >= 0:
            experience_years = llm_exp
    else:
        logger.info("Ollama extraction unavailable, using deterministic fallback")

    skills_required = list(dict.fromkeys([*skills_from_text, *skills_from_llm]))
    logger.info(
        "Analyze job completed role=%s skills=%s experience=%s",
        role,
        len(skills_required),
        experience_years,
    )
    return AnalyzeJobOut(
        role=role,
        skills_required=skills_required,
        experience_required=experience_years,
    )
