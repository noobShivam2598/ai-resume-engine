from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.resume import Resume
from app.schemas.resume_schema import ResumeDetailOut, ResumeSummaryOut
from app.services.file_service import delete_resume_file

router = APIRouter(prefix="/api", tags=["resumes"])


@router.get("/resumes", response_model=list[ResumeSummaryOut])
def list_resumes(
    user_id: int | None = Query(default=None),
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db),
) -> list[ResumeSummaryOut]:
    q = db.query(Resume).order_by(Resume.created_at.desc())
    if user_id is not None:
        q = q.filter(Resume.user_id == user_id)
    rows = list(q.offset(skip).limit(limit).all())
    return [ResumeSummaryOut.from_resume(r) for r in rows]


@router.get("/resumes/{resume_id}", response_model=ResumeDetailOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)) -> ResumeDetailOut:
    resume = (
        db.query(Resume)
        .options(joinedload(Resume.parsed))
        .filter(Resume.id == resume_id)
        .first()
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return ResumeDetailOut.from_resume(resume)


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: Session = Depends(get_db)) -> None:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    delete_resume_file(resume)
    db.delete(resume)
    db.commit()
