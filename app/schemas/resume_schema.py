from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from app.models.resume import Resume


class ParsedDataPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None


class UrlAnalyzeIn(BaseModel):
    url: str


class UrlAnalyzeOut(BaseModel):
    url: str
    role: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None


class AnalyzeJobIn(BaseModel):
    job_url: str | None = None
    job_description: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "AnalyzeJobIn":
        if not (self.job_url and self.job_url.strip()) and not (
            self.job_description and self.job_description.strip()
        ):
            raise ValueError("Provide either job_url or job_description.")
        return self


class AnalyzeJobOut(BaseModel):
    role: str | None = None
    skills_required: list[str] = Field(default_factory=list)
    experience_required: int | None = None


class ResumeDetailOut(BaseModel):
    id: int
    status: str
    file_name: str
    parsed_data: ParsedDataPublic | None = None

    @staticmethod
    def _display_status(status: str) -> str:
        return "Analyzed" if status == "parsed" else status

    @classmethod
    def from_resume(cls, resume: Any) -> ResumeDetailOut:
        pd = resume.parsed
        parsed_block: ParsedDataPublic | None = None
        if pd is not None:
            parsed_block = ParsedDataPublic(
                skills=list(pd.skills or []),
                experience_years=pd.experience_years,
            )
        return cls(
            id=resume.id,
            status=cls._display_status(resume.status),
            file_name=resume.original_filename,
            parsed_data=parsed_block,
        )


class ResumeSummaryOut(BaseModel):
    id: int
    status: str
    file_name: str
    created_at: datetime

    @staticmethod
    def _display_status(status: str) -> str:
        return "Analyzed" if status == "parsed" else status

    @classmethod
    def from_resume(cls, resume: Any) -> ResumeSummaryOut:
        return cls(
            id=resume.id,
            status=cls._display_status(resume.status),
            file_name=resume.original_filename,
            created_at=resume.created_at,
        )


class ResumeCreate(BaseModel):
    user_id: int = Field(..., description="Owner user id")
    original_filename: str


class ParsedDataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    raw_text: str | None
    skills: list[str] | None
    experience_years: int | None
    structured_json: dict | None
    parser_version: str | None
    created_at: datetime


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    original_filename: str
    stored_path: str
    mime_type: str | None
    created_at: datetime
    parsed: ParsedDataRead | None = None
