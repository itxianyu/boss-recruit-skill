from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover
    Workbook = None

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:  # pragma: no cover
    SentenceTransformer = None
    util = None


DEFAULT_RESUMES: List[Dict[str, Any]] = [
    {
        "name": "张三",
        "skills": ["Python", "Django", "REST API", "MySQL"],
        "experience": 4,
        "city": "上海",
        "education": "本科",
        "projects": ["电商订单系统", "供应链管理平台"],
        "summary": "偏后端服务开发，熟悉接口设计和性能优化。",
    },
    {
        "name": "李四",
        "skills": ["Python", "Flask", "Redis", "Docker"],
        "experience": 3,
        "city": "上海",
        "education": "本科",
        "projects": ["营销活动平台", "数据采集服务"],
        "summary": "偏业务系统交付，能独立负责中小型服务。",
    },
    {
        "name": "王五",
        "skills": ["Java", "Spring Boot", "MySQL", "Kafka"],
        "experience": 5,
        "city": "杭州",
        "education": "本科",
        "projects": ["支付清结算系统"],
        "summary": "主栈 Java，转 Python 成本较高。",
    },
]


@dataclass
class JobRequest:
    title: str
    skills: List[str] = field(default_factory=list)
    experience: int = 0
    city: str = ""
    education: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRequest":
        return cls(
            title=str(data.get("title", "")).strip(),
            skills=[str(item).strip() for item in data.get("skills", []) if str(item).strip()],
            experience=_safe_int(data.get("experience", 0)),
            city=str(data.get("city", "")).strip(),
            education=str(data.get("education", "")).strip(),
        )


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class BossRecruitSkill:
    """
    Agent-callable recruiting workflow.

    The live resume source is intentionally pluggable:
    - use `resume_data_path` for local JSON data
    - override `_fetch_resumes` for MCP or browser-backed collection
    """

    def __init__(
        self,
        output_dir: str = "artifacts",
        resume_data_path: Optional[str] = None,
        embedding_model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.resume_data_path = Path(resume_data_path) if resume_data_path else None
        self.embedding_model_name = embedding_model_name
        self._embedding_model = None

    def search_and_generate(self, job_req: Dict[str, Any]) -> Dict[str, Any]:
        parsed_request = JobRequest.from_dict(job_req)
        self._validate_job_request(parsed_request)

        resumes = self._fetch_resumes(parsed_request)
        matched = self._match_resumes(parsed_request, resumes)
        pdf_files = [self._generate_pdf(parsed_request, resume) for resume in matched]
        excel_file = self._generate_excel(matched)

        return {
            "job_request": parsed_request.__dict__,
            "resumes": matched,
            "pdf_files": [str(path) for path in pdf_files],
            "excel_file": str(excel_file),
            "data_source": self._data_source_label(),
        }

    def search_and_generate_from_text(self, request_text: str) -> Dict[str, Any]:
        job_req = self.parse_job_request(request_text)
        result = self.search_and_generate(job_req)
        result["request_text"] = request_text
        return result

    def parse_job_request(self, request_text: str) -> Dict[str, Any]:
        text = request_text.strip()
        city = self._extract_first(text, ["上海", "北京", "深圳", "广州", "杭州", "苏州", "成都", "武汉", "南京"])
        education = self._extract_first(text, ["大专", "本科", "硕士", "博士"])
        experience_match = re.search(r"(\d+)\s*年", text)
        experience = int(experience_match.group(1)) if experience_match else 0

        title = self._guess_title(text)
        skills = self._extract_skills(text)

        return {
            "title": title or "未指定岗位",
            "skills": skills,
            "experience": experience,
            "city": city or "",
            "education": education or "",
        }

    def _validate_job_request(self, job_req: JobRequest) -> None:
        if not job_req.title:
            raise ValueError("job_req.title is required")

    def _fetch_resumes(self, job_req: JobRequest) -> List[Dict[str, Any]]:
        if self.resume_data_path and self.resume_data_path.exists():
            with self.resume_data_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, list):
                raise ValueError("resume_data_path must contain a JSON array")
            return [self._normalize_resume(item) for item in data]

        return [self._normalize_resume(item) for item in DEFAULT_RESUMES]

    def _normalize_resume(self, item: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(item)
        normalized["skills"] = [str(skill).strip() for skill in item.get("skills", []) if str(skill).strip()]
        normalized["projects"] = [str(project).strip() for project in item.get("projects", []) if str(project).strip()]
        normalized["experience"] = _safe_int(item.get("experience", 0))
        normalized["city"] = str(item.get("city", "")).strip()
        normalized["education"] = str(item.get("education", "")).strip()
        normalized["name"] = str(item.get("name", "")).strip()
        normalized["summary"] = str(item.get("summary", "")).strip()
        return normalized

    def _match_resumes(self, job_req: JobRequest, resumes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored_resumes = []
        for resume in resumes:
            score_details = self._score_resume(job_req, resume)
            enriched = dict(resume)
            enriched.update(score_details)
            scored_resumes.append(enriched)

        return sorted(scored_resumes, key=lambda item: item["match_score"], reverse=True)

    def _score_resume(self, job_req: JobRequest, resume: Dict[str, Any]) -> Dict[str, Any]:
        skill_overlap = self._skill_overlap_score(job_req.skills, resume.get("skills", []))
        experience_score = self._experience_score(job_req.experience, resume.get("experience", 0))
        city_score = 1.0 if not job_req.city or job_req.city == resume.get("city", "") else 0.0
        education_score = self._education_score(job_req.education, resume.get("education", ""))
        semantic_score = self._semantic_score(job_req, resume)

        weighted = (
            skill_overlap * 0.45
            + experience_score * 0.2
            + city_score * 0.15
            + education_score * 0.1
            + semantic_score * 0.1
        )

        reasons = []
        if skill_overlap > 0:
            reasons.append(f"技能匹配 {skill_overlap:.2f}")
        if experience_score > 0:
            reasons.append(f"经验匹配 {experience_score:.2f}")
        if city_score == 1.0 and job_req.city:
            reasons.append("城市匹配")
        if education_score > 0 and job_req.education:
            reasons.append("学历满足")
        if semantic_score > 0:
            reasons.append(f"语义相似 {semantic_score:.2f}")

        return {
            "match_score": round(weighted, 3),
            "match_reasons": reasons,
        }

    def _skill_overlap_score(self, required_skills: List[str], resume_skills: List[str]) -> float:
        if not required_skills:
            return 0.5
        required = {skill.lower() for skill in required_skills}
        actual = {skill.lower() for skill in resume_skills}
        return len(required & actual) / len(required)

    def _experience_score(self, required_years: int, actual_years: int) -> float:
        if required_years <= 0:
            return 0.5
        if actual_years >= required_years:
            return 1.0
        return max(0.0, actual_years / required_years)

    def _education_score(self, required: str, actual: str) -> float:
        if not required:
            return 0.5
        rank = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}
        return 1.0 if rank.get(actual, 0) >= rank.get(required, 0) else 0.0

    def _semantic_score(self, job_req: JobRequest, resume: Dict[str, Any]) -> float:
        if SentenceTransformer is None or util is None:
            return 0.0

        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.embedding_model_name)

        job_text = self._job_text(job_req)
        resume_text = self._resume_text(resume)
        job_vector = self._embedding_model.encode(job_text)
        resume_vector = self._embedding_model.encode(resume_text)
        return max(0.0, float(util.cos_sim(job_vector, resume_vector).item()))

    def _job_text(self, job_req: JobRequest) -> str:
        return (
            f"岗位:{job_req.title} "
            f"技能:{','.join(job_req.skills)} "
            f"经验:{job_req.experience}年 "
            f"城市:{job_req.city} "
            f"学历:{job_req.education}"
        )

    def _resume_text(self, resume: Dict[str, Any]) -> str:
        return (
            f"技能:{','.join(resume.get('skills', []))} "
            f"经验:{resume.get('experience', 0)}年 "
            f"城市:{resume.get('city', '')} "
            f"学历:{resume.get('education', '')} "
            f"项目:{','.join(resume.get('projects', []))} "
            f"总结:{resume.get('summary', '')}"
        )

    def _generate_pdf(self, job_req: JobRequest, resume: Dict[str, Any]) -> Path:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

        file_path = self.output_dir / f"{resume['name']}.pdf"
        pdf = canvas.Canvas(str(file_path), pagesize=A4)
        pdf.setTitle(f"{resume['name']}_match_summary")
        pdf.setFont("STSong-Light", 14)

        lines = [
            f"岗位: {job_req.title}",
            f"候选人: {resume['name']}",
            f"匹配分: {resume['match_score']}",
            f"技能: {', '.join(resume.get('skills', []))}",
            f"经验: {resume.get('experience', 0)} 年",
            f"城市: {resume.get('city', '')}",
            f"学历: {resume.get('education', '')}",
            f"项目: {', '.join(resume.get('projects', []))}",
            f"说明: {'; '.join(resume.get('match_reasons', []))}",
            f"摘要: {resume.get('summary', '')}",
        ]

        y = 800
        for line in lines:
            pdf.drawString(48, y, line)
            y -= 24
            if y < 72:
                pdf.showPage()
                pdf.setFont("STSong-Light", 14)
                y = 800

        pdf.save()
        return file_path

    def _generate_excel(self, matched: List[Dict[str, Any]]) -> Path:
        file_path = self.output_dir / f"matched_candidates_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        rows: List[Dict[str, Any]] = []
        for item in matched:
            rows.append(
                {
                    "name": item.get("name", ""),
                    "match_score": item.get("match_score", 0),
                    "skills": ", ".join(item.get("skills", [])),
                    "experience": item.get("experience", 0),
                    "city": item.get("city", ""),
                    "education": item.get("education", ""),
                    "projects": ", ".join(item.get("projects", [])),
                    "match_reasons": "; ".join(item.get("match_reasons", [])),
                }
            )

        if pd is not None:
            pd.DataFrame(rows).to_excel(file_path, index=False)
            return file_path

        if Workbook is not None:
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "matched_candidates"

            headers = [
                "name",
                "match_score",
                "skills",
                "experience",
                "city",
                "education",
                "projects",
                "match_reasons",
            ]
            worksheet.append(headers)
            for row in rows:
                worksheet.append([row[header] for header in headers])
            workbook.save(file_path)
            return file_path

        raise RuntimeError(
            "Excel generation requires pandas or openpyxl. Install dependencies from requirements.txt."
        )

        return file_path

    def _extract_first(self, text: str, values: List[str]) -> str:
        for value in values:
            if value in text:
                return value
        return ""

    def _extract_skills(self, text: str) -> List[str]:
        known_skills = [
            "Python",
            "Django",
            "Flask",
            "FastAPI",
            "REST API",
            "Redis",
            "MySQL",
            "PostgreSQL",
            "Docker",
            "Kubernetes",
            "Java",
            "Spring Boot",
        ]
        return [skill for skill in known_skills if skill.lower() in text.lower()]

    def _guess_title(self, text: str) -> str:
        known_titles = [
            "Python 后端开发",
            "Python开发",
            "后端开发",
            "Java 后端开发",
            "算法工程师",
            "数据分析师",
            "产品经理",
        ]
        for title in known_titles:
            if title.lower() in text.lower():
                return title

        match = re.search(r"找(.+?)(并生成|生成|，|,|。|$)", text)
        if match:
            return match.group(1).strip()
        return ""

    def _data_source_label(self) -> str:
        if self.resume_data_path and self.resume_data_path.exists():
            return f"local_json:{self.resume_data_path}"
        return "built_in_sample_data"


if __name__ == "__main__":
    skill = BossRecruitSkill()
    demo = skill.search_and_generate_from_text("帮我找上海 Python 后端开发，要求 3 年经验，本科，生成 PDF 和 Excel")
    print(json.dumps(demo, ensure_ascii=False, indent=2))
