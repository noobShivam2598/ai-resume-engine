from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.parsed_data import ParsedData
from app.models.resume import Resume
from app.services import parser_service

logger = logging.getLogger(__name__)


def _apply_parsed_fields(
    row: ParsedData,
    *,
    raw_text: str | None,
    skills: list[str],
    experience_years: int | None,
    structured_json: dict | None,
    parser_version: str,
) -> None:
    row.raw_text = raw_text
    row.skills = skills
    row.experience_years = experience_years
    row.structured_json = structured_json
    row.parser_version = parser_version


def _upsert_parsed_data_with_integrity_retry(
    db: Session,
    resume_id: int,
    *,
    raw_text: str | None,
    skills: list[str],
    experience_years: int | None,
    structured_json: dict | None,
    parser_version: str,
) -> None:
    existing = db.scalars(select(ParsedData).where(ParsedData.resume_id == resume_id)).first()
    if existing is not None:
        _apply_parsed_fields(
            existing,
            raw_text=raw_text,
            skills=skills,
            experience_years=experience_years,
            structured_json=structured_json,
            parser_version=parser_version,
        )
        return

    row = ParsedData(
        resume_id=resume_id,
        raw_text=raw_text,
        skills=skills,
        experience_years=experience_years,
        structured_json=structured_json,
        parser_version=parser_version,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        logger.warning(
            "Duplicate parsed_data insert for resume_id=%s; applying update instead",
            resume_id,
        )
        db.rollback()
        existing = db.scalars(select(ParsedData).where(ParsedData.resume_id == resume_id)).first()
        if existing is None:
            raise
        _apply_parsed_fields(
            existing,
            raw_text=raw_text,
            skills=skills,
            experience_years=experience_years,
            structured_json=structured_json,
            parser_version=parser_version,
        )


def run_resume_parsing(db: Session, resume_id: int) -> None:
    resume = db.get(Resume, resume_id)
    if resume is None:
        logger.warning("Parsing skipped: resume_id=%s not found", resume_id)
        return

    resume.status = "parsing"
    db.commit()
    logger.info("Parsing started resume_id=%s", resume_id)

    try:
        path = Path(resume.stored_path)
        raw_text, structured = parser_service.extract_text(path)
        text_for_features = raw_text or ""
        skills_from_text = parser_service.extract_skills(text_for_features)
        skills_from_filename = parser_service.extract_skills_from_filename(resume.original_filename)
        llm_result = parser_service.extract_with_ollama(text_for_features)
        skills_from_llm: list[str] = []
        if isinstance(llm_result, dict):
            llm_skills = llm_result.get("skills")
            if isinstance(llm_skills, list):
                skills_from_llm = [str(s).strip().lower() for s in llm_skills if str(s).strip()]
        # Keep order stable: text-derived skills first, filename fallback after that.
        skills = list(dict.fromkeys([*skills_from_text, *skills_from_llm, *skills_from_filename]))
        experience_years = parser_service.extract_experience_years(text_for_features)
        if experience_years is None and isinstance(llm_result, dict):
            llm_exp = llm_result.get("experience_years")
            if isinstance(llm_exp, int) and llm_exp >= 0:
                experience_years = llm_exp

        _upsert_parsed_data_with_integrity_retry(
            db,
            resume_id,
            raw_text=raw_text,
            skills=skills,
            experience_years=experience_years,
            structured_json=structured,
            parser_version=parser_service.PARSER_VERSION,
        )

        resume = db.get(Resume, resume_id)
        if resume is not None:
            resume.status = "parsed"
        db.commit()
        logger.info("Parsing success resume_id=%s skills=%s experience_years=%s", resume_id, len(skills), experience_years)
    except Exception:
        logger.exception("Parsing failure resume_id=%s", resume_id)
        db.rollback()
        resume = db.get(Resume, resume_id)
        if resume is not None:
            resume.status = "failed"
            db.commit()
