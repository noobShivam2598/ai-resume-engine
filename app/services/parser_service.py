from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from app.core.config import settings

PARSER_VERSION = "phase1.2-mvp"
logger = logging.getLogger(__name__)

# Keyword-based skill catalog (lowercase canonical names; matching is case-insensitive).
SKILLS_DB: tuple[str, ...] = (
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "node.js",
    "vue.js",
    "react.js",
    "next.js",
    "express.js",
    "tensorflow",
    "pytorch",
    "kubernetes",
    "postgresql",
    "javascript",
    "typescript",
    "terraform",
    "ansible",
    "jenkins",
    "mongodb",
    "graphql",
    "fastapi",
    "django",
    "flask",
    "spring boot",
    "spring",
    "laravel",
    "rails",
    "ruby on rails",
    "angular",
    "bootstrap",
    "tailwind",
    "pandas",
    "numpy",
    "scikit-learn",
    "opencv",
    "tableau",
    "power bi",
    "html",
    "css",
    "sass",
    "redux",
    "webpack",
    "babel",
    "jest",
    "pytest",
    "cypress",
    "selenium",
    "rabbitmq",
    "kafka",
    "elasticsearch",
    "nginx",
    "apache",
    "linux",
    "unix",
    "bash",
    "shell",
    "git",
    "github",
    "gitlab",
    "bitbucket",
    "jira",
    "confluence",
    "agile",
    "scrum",
    "kanban",
    "mysql",
    "mariadb",
    "sqlite",
    "redis",
    "memcached",
    "oracle",
    "sql server",
    "dynamodb",
    "firebase",
    "supabase",
    "aws",
    "amazon web services",
    "ec2",
    "s3",
    "lambda",
    "cloudformation",
    "azure",
    "gcp",
    "google cloud",
    "docker",
    "podman",
    "helm",
    "ci/cd",
    "devops",
    "microservices",
    "backend",
    "backend development",
    "api development",
    "rest api",
    "grpc",
    "soap",
    "oauth",
    "jwt",
    "oauth2",
    "ssl",
    "tls",
    "https",
    "http",
    "tcp/ip",
    "udp",
    "vpn",
    "dns",
    "cdn",
    "load balancing",
    "blockchain",
    "solidity",
    "ethereum",
    "rust",
    "golang",
    "go language",
    "swift",
    "kotlin",
    "scala",
    "perl",
    "php",
    "ruby",
    "python",
    "java",
    "c#",
    "csharp",
    ".net",
    "dotnet",
    "asp.net",
    "c++",
    "cpp",
    "r language",
    "matlab",
    "excel",
    "vba",
    "sql",
    "nosql",
    "etl",
    "data warehousing",
    "snowflake",
    "bigquery",
    "hadoop",
    "spark",
    "airflow",
    "dbt",
    "figma",
    "sketch",
    "photoshop",
    "illustrator",
    "wordpress",
    "shopify",
    "salesforce",
    "sap",
    "oracle ebs",
)


def normalize_resume_text(raw_text: str) -> str:
    """Normalize OCR/PDF extracted text for downstream parsing."""
    if not raw_text:
        return ""

    normalized = raw_text.replace("\u00a0", " ")
    # Collapse words where each character was split by spaces, e.g. "P H P" -> "PHP".
    normalized = re.sub(
        r"\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b",
        lambda m: re.sub(r"\s+", "", m.group(0)),
        normalized,
    )
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized


def extract_text(file_path: Path) -> tuple[str | None, dict | None]:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return text, {"format": "plain_text", "chars": len(text)}

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        return text or None, {"format": "pdf", "pages": len(reader.pages)}

    if suffix == ".docx":
        import docx

        document = docx.Document(str(file_path))
        text = "\n".join(p.text for p in document.paragraphs).strip()
        return text or None, {"format": "docx"}

    return None, {"format": suffix or "unknown", "note": "Unsupported type for text extraction."}


def extract_skills(raw_text: str) -> list[str]:
    if not raw_text or not raw_text.strip():
        return []

    text_lower = normalize_resume_text(raw_text).lower()
    found: list[str] = []
    consumed = [False] * len(text_lower)

    def spans_overlap(start: int, end: int) -> bool:
        return any(consumed[i] for i in range(start, min(end, len(consumed))))

    def mark_consumed(start: int, end: int) -> None:
        for i in range(start, min(end, len(consumed))):
            consumed[i] = True

    for skill in sorted(SKILLS_DB, key=len, reverse=True):
        sl = skill.lower()
        if " " in skill:
            start = 0
            while True:
                idx = text_lower.find(sl, start)
                if idx == -1:
                    break
                end = idx + len(sl)
                if not spans_overlap(idx, end):
                    found.append(skill)
                    mark_consumed(idx, end)
                start = idx + 1
            continue

        pattern = re.escape(skill)
        if skill == "c++":
            pattern = r"c\+\+"
        elif skill == "c#":
            pattern = r"c\#"
        elif "." in skill:
            pattern = re.escape(skill)

        for m in re.finditer(rf"(?<![a-z0-9#+])(?:{pattern})(?![a-z0-9#+])", text_lower):
            idx, end = m.start(), m.end()
            if not spans_overlap(idx, end):
                found.append(skill)
                mark_consumed(idx, end)

    # De-duplicate while preserving first-seen order of longer matches
    seen: set[str] = set()
    ordered: list[str] = []
    for s in found:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def extract_skills_from_filename(filename: str) -> list[str]:
    if not filename or not filename.strip():
        return []

    # Drop extension and normalize separators often used in uploaded names.
    stem = Path(filename).stem
    normalized = re.sub(r"[_\-]+", " ", stem)
    return extract_skills(normalized)


def extract_experience_years(raw_text: str) -> int | None:
    if not raw_text or not raw_text.strip():
        return None

    normalized_text = normalize_resume_text(raw_text)
    candidates: list[int] = []

    for m in re.finditer(
        r"(?:over|more than|at least|approximately|around|~)\s*(\d+)\+?\s*(?:years?|yrs?)\b",
        normalized_text,
        re.IGNORECASE,
    ):
        candidates.append(int(m.group(1)))

    for m in re.finditer(
        r"\b(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:in|with|experience))?\b",
        normalized_text,
        re.IGNORECASE,
    ):
        candidates.append(int(m.group(1)))

    for m in re.finditer(
        r"\b(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)\b",
        normalized_text,
        re.IGNORECASE,
    ):
        candidates.append(max(int(m.group(1)), int(m.group(2))))

    if not candidates:
        # Fallback: infer from year ranges like "2018-2024".
        year_candidates: list[int] = []
        now_year = datetime.utcnow().year
        for m in re.finditer(
            r"\b(19\d{2}|20\d{2})\s*[-–]\s*(present|current|now|19\d{2}|20\d{2})\b",
            normalized_text,
            re.IGNORECASE,
        ):
            start = int(m.group(1))
            end_text = m.group(2).lower()
            end = now_year if end_text in {"present", "current", "now"} else int(end_text)
            if end >= start:
                year_candidates.append(end - start)
        if not year_candidates:
            return None
        inferred = max(year_candidates)
        return inferred if inferred > 0 else None
    return max(candidates)


def extract_with_ollama(raw_text: str) -> dict[str, object] | None:
    if not settings.ollama_enabled:
        return None
    if not raw_text or not raw_text.strip():
        return None

    prompt = (
        "Extract resume information and return ONLY valid JSON with keys "
        '`skills` (array of lowercase strings) and `experience_years` (integer or null). '
        "Do not add any markdown or explanation.\n\n"
        f"Resume text:\n{normalize_resume_text(raw_text)[:12000]}"
    )
    llm_json = call_ollama(prompt)
    if "error" in llm_json:
        logger.error("Ollama extraction failed: %s", llm_json.get("error"))
        return None
    return llm_json


def build_job_extraction_prompt(job_description: str) -> str:
    """Build a strict JSON-only prompt for Ollama job extraction."""
    safe_text = (job_description or "").strip()
    return (
        "You are an AI that extracts structured job data.\n\n"
        "Extract:\n"
        "* role (string)\n"
        "* skills_required (array of lowercase strings)\n"
        "* experience_required (integer, years)\n\n"
        "Strict rules:\n"
        "* Return ONLY valid JSON\n"
        "* No explanation\n"
        "* No markdown\n"
        "* No extra text\n"
        "* skills_required must be lowercase\n"
        "* skills_required must not contain duplicates\n\n"
        "Return ONLY valid JSON.\n\n"
        "Text:\n"
        '"""\n'
        f"{safe_text}\n"
        '"""'
    )


def infer_role_from_text(job_description: str) -> str | None:
    text = normalize_resume_text(job_description)
    if not text:
        return None
    patterns = (
        r"\b(senior|lead|principal|junior)?\s*(backend|frontend|full[-\s]?stack|software|data|devops|ml|ai)?\s*(engineer|developer)\b",
        r"\b(product manager|project manager|qa engineer|data analyst|business analyst)\b",
    )
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return " ".join(m.group(0).split()).strip()
    return None


def extract_job_details_with_ollama(job_description: str) -> dict[str, object] | None:
    if not settings.ollama_enabled:
        return None
    normalized = normalize_resume_text(job_description)
    if not normalized:
        return None

    llm_json = call_ollama(build_job_extraction_prompt(normalized[:12000]))
    if "error" in llm_json:
        logger.error("Ollama job extraction failed: %s", llm_json.get("error"))
        return None
    try:
        role = llm_json.get("role")
        skills_required = llm_json.get("skills_required")
        experience_required = llm_json.get("experience_required")
        normalized_skills: list[str] = []
        if isinstance(skills_required, list):
            normalized_skills = list(
                dict.fromkeys(str(s).strip().lower() for s in skills_required if str(s).strip())
            )
        result: dict[str, object] = {
            "role": str(role).strip() if isinstance(role, str) and role.strip() else None,
            "skills_required": normalized_skills,
            "experience_required": experience_required if isinstance(experience_required, int) else None,
        }
        return result
    except Exception:
        logger.exception("Failed to normalize Ollama job extraction payload")
        return None


def call_ollama(prompt: str) -> dict:
    payload = {
        "model": "qwen",
        "prompt": prompt,
        "stream": False,
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.ollama_timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        outer = json.loads(body)
        raw_response = outer.get("response", "")
        if not isinstance(raw_response, str):
            return {"error": "Missing or invalid response field from Ollama.", "raw": outer}
        try:
            parsed = json.loads(raw_response)
            if not isinstance(parsed, dict):
                return {"error": "Parsed JSON is not an object.", "raw": raw_response}
            return parsed
        except json.JSONDecodeError:
            return {"error": "Invalid JSON returned by Ollama.", "raw": raw_response}
    except urllib.error.URLError as exc:
        return {"error": f"Ollama request failed: {exc}"}
    except TimeoutError:
        return {"error": "Ollama request timed out."}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in Ollama API response body."}
