from __future__ import annotations


def _normalize_skill(skill: object) -> str:
    return str(skill).strip().lower()


def analyze_skill_gap(jd_skills: list, resume_skills: list) -> dict:
    """Compare JD skills vs resume skills (case-insensitive, deduped by JD order)."""
    resume_set = {_normalize_skill(s) for s in resume_skills if _normalize_skill(s)}

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    seen_jd: set[str] = set()

    for skill in jd_skills:
        key = _normalize_skill(skill)
        if not key or key in seen_jd:
            continue
        seen_jd.add(key)
        if key in resume_set:
            matched_skills.append(key)
        else:
            missing_skills.append(key)

    return {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
